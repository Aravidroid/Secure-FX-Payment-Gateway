import requests
import time

BASE_URL = "http://localhost:5000"
API_KEY = "sif1JDZ1ssHR0IxnxzWW7pCsiamdH42NIbNZe2aQ_3g"

def make_charge(fake_ip):
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY,
        # spoof header
        "X-Forwarded-For": fake_ip
    }
    payload = {
        "amount": 50,
        "currency": "KRW",
        "card_number": "4242424242424242",
        "exp_month": 12,
        "exp_year": 2028,
        "cvc": "123"
    }
    r = requests.post(f"{BASE_URL}/v1/charges", json=payload, headers=headers)
    return r.status_code, r.text

# rotate fake IPs
for i in range(12):
    fake_ip = f"203.0.113.{i}"   # test IPs
    status, body = make_charge(fake_ip)
    print(i, fake_ip, status, body[:120])
    time.sleep(0.2)
