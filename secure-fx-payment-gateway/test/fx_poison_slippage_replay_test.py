import requests
import redis
import time
import os
import json

# ---------- CONFIG ----------
BASE_URL = "http://localhost:5000"
MASTER_KEY = "admin_secret_123"   # change if different
MERCHANT_NAME = "FXPoisonTest"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

# currencies used in your project (customer -> merchant MYR)
CUST_CUR = "USD"
MERCHANT_CUR = "MYR"
FX_CACHE_KEY = f"fx_rate:{CUST_CUR}:{MERCHANT_CUR}"

# Test amounts
AMOUNT = 100.0

# ----------------- Helpers -----------------
def create_api_key():
    url = f"{BASE_URL}/admin/generate-key?master_key={MASTER_KEY}&merchant_name={MERCHANT_NAME}"
    resp = requests.post(url)
    resp.raise_for_status()
    data = resp.json()
    return data["api_key"]

def charge_with_key(api_key, payload):
    headers = {"Content-Type": "application/json", "X-API-KEY": api_key}
    r = requests.post(f"{BASE_URL}/v1/charges", json=payload, headers=headers, timeout=10)
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body

def get_quote(from_cur, to_cur, amount):
    r = requests.get(f"{BASE_URL}/v1/quote?from={from_cur}&to={to_cur}&amount={amount}")
    return r.status_code, r.json()

def set_fx_cache(value):
    """Poison the FX cache with a chosen numeric value (float string)."""
    r_conn = r
    # Use the same key name as currency_manager: 'fx_rate:{base}:{target}'
    r_conn.setex(FX_CACHE_KEY, 60, str(value))
    print(f"[redis] set {FX_CACHE_KEY} = {value} (TTL 60s)")

def del_fx_cache():
    r.delete(FX_CACHE_KEY)
    print(f"[redis] deleted {FX_CACHE_KEY}")

# ----------------- Test Steps -----------------
def step_header(title):
    print("\n" + "="*60)
    print(title)
    print("="*60 + "\n")

def main():
    print("Starting FX Poison / Replay / Slippage test against", BASE_URL)

    # 1) create test merchant key
    step_header("STEP 1 — Create test API key")
    api_key = create_api_key()
    print("Created API Key:", api_key)

    # 2) baseline quote & charge (no poisoning)
    step_header("STEP 2 — Baseline quote & payment (no poisoning)")
    status, quote = get_quote(CUST_CUR, MERCHANT_CUR, AMOUNT)
    print("Quote status:", status, "body:", json.dumps(quote, indent=2))
    payload = {
        "amount": AMOUNT,
        "currency": CUST_CUR,
        "card_number": "4242424242424242",
        "exp_month": 12,
        "exp_year": 2028,
        "cvc": "123"
    }
    s, b = charge_with_key(api_key, payload)
    print("Baseline charge ->", s, b)

    # 3) FX Cache Poisoning: set very favorable low rate for customer (attacker pays less)
    step_header("STEP 3 — FX CACHE POISONING (low base rate)")
    poisoned_rate = 0.0001   # extremely low base rate (customer->MYR)
    set_fx_cache(poisoned_rate)
    # fetch quote (should now reflect poisoned_rate if currency_manager reads cache)
    status, quote2 = get_quote(CUST_CUR, MERCHANT_CUR, AMOUNT)
    print("Quote after poisoning:", status, quote2)
    # attempt a charge with fresh timestamp
    payload_ts = payload.copy()
    payload_ts["rate_timestamp"] = time.time()   # current timestamp to pass expiry check
    s2, b2 = charge_with_key(api_key, payload_ts)
    print("Charge after poisoning ->", s2, b2)

    # Clean up poison quickly
    del_fx_cache()

    # 4) REPLAY ATTACK ON rate_timestamp (expiry bypass)
    step_header("STEP 4 — REPLAY / TIMESTAMP BYPASS TEST")
    # 4.a expired timestamp (should be rejected)
    old_ts = time.time() - 120  # 2 minutes old (FX_RATE_VALIDITY_SEC is 60)
    payload_old = payload.copy()
    payload_old["rate_timestamp"] = old_ts
    s_old, b_old = charge_with_key(api_key, payload_old)
    print("Charge with EXPIRED timestamp ->", s_old, b_old)

    # 4.b future timestamp (attacker sets timestamp in future — server currently checks only age > 60)
    future_ts = time.time() + 3600  # 1 hour in future
    payload_future = payload.copy()
    payload_future["rate_timestamp"] = future_ts
    s_future, b_future = charge_with_key(api_key, payload_future)
    print("Charge with FUTURE timestamp ->", s_future, b_future)
    print("If FUTURE timestamp is accepted, that's a replay/expiry-bypass vulnerability.")

    # 5) FX SLIPPAGE BRUTE-ATTEMPTS
    step_header("STEP 5 — FX SLIPPAGE BRUTE-ATTEMPTS (try many base rates)")
    # We'll set a variety of base rates (very low, near-zero, huge, and normal-ish)
    test_rates = [0.00001, 0.0001, 0.001, 0.01, 0.1, 0.5, 1.0, 5.0, 50.0, 100.0, 1000.0]
    slippage_found = []
    for rtest in test_rates:
        set_fx_cache(rtest)
        # Use fresh timestamp
        payload_run = payload.copy()
        payload_run["rate_timestamp"] = time.time()
        s_run, b_run = charge_with_key(api_key, payload_run)
        print(f"base_rate={rtest} -> status {s_run} body {b_run}")
        # look for explicit slippage error
        if isinstance(b_run, dict) and b_run.get("error") == "slippage_exceeded":
            slippage_found.append((rtest, b_run))
        time.sleep(0.15)
        del_fx_cache()
        time.sleep(0.05)

    if slippage_found:
        print("\n[!] Slippage errors observed for these base rates:")
        for ritem in slippage_found:
            print(ritem)
    else:
        print("\n[+] No slippage_exceeded responses observed for tested rates.")
        print("Note: with your current constants (FX_MARKUP_PERCENT=0.35 and MAX_SLIPPAGE_TOLERANCE=0.50)")
        print("applied markup < slippage tolerance, so slippage_exceeded is unlikely unless constants change.")

    # Final cleanup
    del_fx_cache()
    step_header("TEST SUMMARY / SUGGESTED FIXES")
    print("""
Observations & suggested hardening:
1) If the 'future timestamp' attempt was accepted, fix server-side rate_timestamp validation:
   - Reject timestamps > current_time + small_skew (e.g., 5s)
   - Only accept timestamps within [now - FX_VALIDITY, now + ALLOWED_SKEW]

2) Protect the FX cache in Redis:
   - Only allow trusted backend processes to write fx_rate:* keys.
   - Use Redis ACLs, separate Redis DB/username for cache writes, or signed rate quotes.

3) Consider tying a signed quote (server-signed) into the charge flow:
   - When frontend requests /v1/quote, server returns (rate, expires_at, signature).
   - client must send rate + expires_at + signature; server validates signature and timestamp.

4) Enforce stricter slippage checks or reduce MAX_SLIPPAGE_TOLERANCE if you expect large volatility.

5) Log and alert when fx_rate keys are written externally.

""")

if __name__ == "__main__":
    main()