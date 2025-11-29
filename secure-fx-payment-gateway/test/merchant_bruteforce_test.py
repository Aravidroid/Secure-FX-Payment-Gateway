import asyncio
import aiohttp
import secrets
import random
import string
import time
import redis
import os
import json

BASE_URL = "http://localhost:5000"
MASTER_KEY = "admin_secret_123"  # same as your test UI
MERCHANT_NAME = "ImpersonationTest"
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(redis_url, decode_responses=True)

CONCURRENCY = 150   # high parallel brute pressure


# ------------------------------
# Helper: create a valid API Key
# ------------------------------
async def create_valid_key(session):
    url = f"{BASE_URL}/admin/generate-key?master_key={MASTER_KEY}&merchant_name={MERCHANT_NAME}"
    async with session.post(url) as res:
        data = await res.json()
        print("[+] Created Valid Merchant Key:", data)
        return data.get("api_key")


# ------------------------------
# Helper: revoke via Redis only
# ------------------------------
def revoke_direct_in_redis(key):
    r.hset("api_key_meta:" + key, "revoked", "1")
    r.srem("api_keys", key)
    print("[!] Revoked key via Redis:", key)


# -----------------------------------------------
# Attack 1 — Merchant Impersonation (Key Forgery)
# -----------------------------------------------
def generate_forged_keys(real_key):
    fake_keys = []

    # 1. Mutate characters in real key
    for i in range(10):
        k = list(real_key)
        idx = random.randint(0, len(k)-1)
        k[idx] = random.choice(string.ascii_letters + string.digits + "-_")
        fake_keys.append("".join(k))

    # 2. Prefix collision attempts
    fake_keys.append(real_key[:10] + secrets.token_urlsafe(22))

    # 3. Suffix collision attempts
    fake_keys.append(secrets.token_urlsafe(22) + real_key[-10:])

    # 4. Same-length random keys
    for _ in range(20):
        fake_keys.append(secrets.token_urlsafe(32))

    # 5. Very short and very long keys
    fake_keys.append(secrets.token_urlsafe(4))
    fake_keys.append(secrets.token_urlsafe(64))

    return fake_keys


# ----------------------------------------------------
# Attack 2 — Brute-Force Random API Keys in Parallel
# ----------------------------------------------------
async def brute_force_key(key, session):
    payload = {
        "amount": 5,
        "currency": "MYR",
        "card_number": "4242424242424242",
        "exp_month": 12,
        "exp_year": 2028,
        "cvc": "123"
    }

    headers = {"Content-Type": "application/json", "X-API-KEY": key}

    try:
        async with session.post(f"{BASE_URL}/v1/charges",
                                json=payload, headers=headers, timeout=4) as res:
            text = await res.text()

            # Track key behavior
            return {
                "key": key,
                "status": res.status,
                "body": text[:200]
            }

    except Exception as e:
        return {"key": key, "status": "ERR", "body": str(e)}


async def run_attack():
    async with aiohttp.ClientSession() as session:
        print("\n==============================")
        print("Step 1: Generate REAL key")
        print("==============================\n")

        real_key = await create_valid_key(session)

        print("\n==============================")
        print("Step 2: Revoke REAL key")
        print("==============================\n")
        revoke_direct_in_redis(real_key)

        print("\n==============================")
        print("Step 3: Generate forged keys")
        print("==============================\n")

        forged_keys = generate_forged_keys(real_key)
        print("[+] Total forged keys:", len(forged_keys))

        print("\n==============================")
        print("Step 4: Test forged keys + brute force")
        print("==============================\n")

        # Mix forged keys with brute-force random keys
        attack_keys = forged_keys + [secrets.token_urlsafe(32) for _ in range(CONCURRENCY)]

        tasks = [brute_force_key(k, session) for k in attack_keys]
        results = await asyncio.gather(*tasks)

        # Print relevant results
        categories = {}

        for res in results:
            s = res["status"]
            categories.setdefault(s, 0)
            categories[s] += 1

        print("\n==============================")
        print("ATTACK RESULTS SUMMARY")
        print("==============================")
        for s, count in categories.items():
            print(f"{s} : {count}")

        print("\n==============================")
        print("Sample Results")
        print("==============================")
        for res in results[:10]:
            print(res)


if __name__ == "__main__":
    asyncio.run(run_attack())
