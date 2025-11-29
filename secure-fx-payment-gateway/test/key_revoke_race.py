import requests
import threading
import time

BASE_URL = "http://localhost:5000"
MASTER_KEY = "admin_secret_123"   # matches checkout.html for dev; or set env MASTER_ADMIN_KEY
MERCHANT_NAME = "test_revoke_merchant"

def create_key():
    r = requests.post(f"{BASE_URL}/admin/generate-key?master_key={MASTER_KEY}&merchant_name={MERCHANT_NAME}")
    return r.status_code, r.json()

def revoke_key(key):
    r = requests.post(f"{BASE_URL}/admin/revoke-key?key={key}&master_key={MASTER_KEY}") if False else None
    # if you don't have a revoke endpoint, use auth.revoke_key via admin console or Redis CLI.
    # For demo, we'll call a small endpoint — replace with your revoke mechanism.

# Step 1: create key
code, data = create_key()
print("create key:", code, data)
API_KEY = data.get("api_key") or data.get("api_key") or data.get("api_key", "")
print("API_KEY:", API_KEY)

# Step 2: spawn worker threads that continuously send charges
stop = False
def worker():
    headers = {"Content-Type": "application/json", "X-API-KEY": API_KEY}
    payload = {"amount": 1, "currency": "MYR", "card_number": "4242424242424242", "exp_month":12, "exp_year":2028, "cvc":"123"}
    while not stop:
        try:
            r = requests.post(f"{BASE_URL}/v1/charges", json=payload, headers=headers, timeout=5)
            print("worker:", r.status_code, r.text[:120])
        except Exception as e:
            print("worker err", e)
        time.sleep(0.05)

threads = [threading.Thread(target=worker) for _ in range(4)]
for t in threads: t.start()

# Step 3: wait, then revoke key
time.sleep(1.5)
print("Now revoking key (simulate)")
# direct Redis revoke via HTTP not implemented in default main.py; you can revoke using redis CLI:
# For demo, we'll call the revoke helper via a small admin endpoint if present.
# Alternatively, run a small script that uses the same auth.generate_key/revoke_key functions to revoke.
import redis, os
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(redis_url, decode_responses=True)
r.hset("api_key_meta:" + API_KEY, "revoked", "1")
r.srem("api_keys", API_KEY)
print("Revoked in Redis.")

# keep running for a bit to observe
time.sleep(3)
stop = True
for t in threads: t.join()
print("Done")
