import asyncio
import aiohttp
import time
import json

BASE_URL = "http://localhost:5000"
API_KEY = "sif1JDZ1ssHR0IxnxzWW7pCsiamdH42NIbNZe2aQ_3g"  # generate via /admin/generate-key or use your test key
CONCURRENT = 200   # number of concurrent requests
PAYLOAD = {
    "amount": 10,
    "currency": "KRW",
    "card_number": "4242424242424242",
    "exp_month": 12,
    "exp_year": 2028,
    "cvc": "123"
}

async def send(session, idx):
    headers = {"Content-Type": "application/json", "X-API-KEY": API_KEY}
    try:
        async with session.post(f"{BASE_URL}/v1/charges", json=PAYLOAD, headers=headers, timeout=10) as r:
            text = await r.text()
            return r.status, text
    except Exception as e:
        return "ERR", str(e)

async def main():
    t0 = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [send(session, i) for i in range(CONCURRENT)]
        results = await asyncio.gather(*tasks)
    dur = time.time() - t0
    counts = {}
    for status, _ in results:
        counts[status] = counts.get(status, 0) + 1
    print(f"Duration: {dur:.2f}s")
    print("Result counts:", counts)
    for i,(s,body) in enumerate(results[:10]):
        print(i, s, (body[:200] + '...') if isinstance(body, str) else body)

if __name__ == "__main__":
    asyncio.run(main())
