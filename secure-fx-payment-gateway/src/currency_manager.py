import requests
import redis
import json
import time
import hmac
import hashlib
import os


# Connect to the same Redis instance
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(redis_url, decode_responses=True)

# 2% Profit Margin (Standard in Fintech is 1-3%)
SPREAD_PERCENTAGE = 0.02 

def get_forex_rate(base_currency, target_currency):
    """
    Fetches real rate, adds spread, and returns 'customer_rate'.
    Caches data in Redis for 60 seconds to optimize performance.
    """
    cache_key = f"fx_rate:{base_currency}:{target_currency}"
    
    # 1. Check Redis Cache first
    cached_rate = r.get(cache_key)
    if cached_rate:
        return float(cached_rate)

    # 2. Fetch from External API (Free Source)
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
        response = requests.get(url)
        data = response.json()
        
        real_rate = data["rates"][target_currency]
        
        # 3. Apply the Spread (The "Business Logic")
        # If user pays in EUR to settle in USD, we charge them MORE EUR.
        # Logic: We give them a slightly worse rate than market.
        customer_rate = real_rate * (1 + SPREAD_PERCENTAGE)
        
        # 4. Save to Redis (Expire in 60s)
        r.setex(cache_key, 60, customer_rate)
        
        return customer_rate

    except Exception as e:
        print(f"FX Error: {e}")
        return None
    
def sign_rate(rate, expires_at):
    secret_key = os.getenv("RATE_SIGNING_KEY", "default-secret-key")
    message = f"{rate}|{expires_at}"
    signature = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature

def build_signed_quote(base_rate, amount, target_currency):
    expires_at = time.time() + 60  # quote valid for 60 seconds
    rate_signature = sign_rate(base_rate, expires_at)

    converted_amount = round(amount * base_rate, 2)

    return {
        "rate": base_rate,
        "converted_amount": converted_amount,
        "expires_at": expires_at,
        "signature": rate_signature,
        "target_currency": target_currency
    }
