# src/rate_limiter.py

import os
import time
import redis
from logger import logger

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(redis_url, decode_responses=True)

# --- GLOBAL CONFIGS (Forex-grade) ---
DEFAULT_RPM = 60                      # Base requests per minute
BURST_MULTIPLIER = 2.0                # Allow 2x burst
GLOBAL_RPM = 5000                     # Overall system throttle
IP_RPM = 30                           # Per-IP limit (fraud protection)
ENDPOINT_RPM = 40                     # Per-endpoint limit (avoids API misuse)

BUCKET_PREFIX = "fx:bucket:"


# --------------------- LUA SCRIPT (Atomic Token Bucket) ------------------------
LUA_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local burst = tonumber(ARGV[3])

local data = redis.call('HMGET', key, 'tokens', 'last_ts')
local tokens = tonumber(data[1])
local last_ts = tonumber(data[2])

if not tokens then
    tokens = burst
    last_ts = now
end

local elapsed = now - last_ts
local refill = (rate / 60.0) * elapsed
tokens = math.min(burst, tokens + refill)

if tokens >= 1 then
    tokens = tokens - 1
    redis.call('HMSET', key, 'tokens', tokens, 'last_ts', now)
    redis.call('EXPIRE', key, 3600)
    return 1
else
    redis.call('HMSET', key, 'tokens', tokens, 'last_ts', now)
    redis.call('EXPIRE', key, 3600)
    return 0
end
"""

RATE_LIMITER = r.register_script(LUA_SCRIPT)
# ----------------------------------------------------------------------------


def limit_bucket(name: str, rpm: int, burst_factor: float = BURST_MULTIPLIER):
    """
    Runs the Lua script for ONE bucket.
    """
    now = time.time()
    burst_capacity = rpm * burst_factor

    allowed = RATE_LIMITER(
        keys=[BUCKET_PREFIX + name],
        args=[now, rpm, burst_capacity]
    )

    return bool(int(allowed))


def allow_request(api_key: str, ip: str, endpoint: str, user_rpm: int = None):
    """
    Forex-grade multilayer rate limiter.
    Returns True/False + logs the layer that blocked.
    """

    # --- 1️⃣ Per API key ---
    key_rpm = user_rpm or DEFAULT_RPM
    if not limit_bucket(f"key:{api_key}", key_rpm):
        logger.warning(f"[RATELIMIT] API_KEY limit exceeded ({api_key})")
        return False

    # --- 2️⃣ Per IP address (fraud protection layer) ---
    if not limit_bucket(f"ip:{ip}", IP_RPM):
        logger.warning(f"[RATELIMIT] IP limit exceeded ({ip}) - possible botnet")
        return False

    # --- 3️⃣ Per endpoint (prevents targeted abuse) ---
    if not limit_bucket(f"endpoint:{endpoint}", ENDPOINT_RPM):
        logger.warning(f"[RATELIMIT] Endpoint throttle ({endpoint})")
        return False

    # --- 4️⃣ Global throttle (system protection) ---
    if not limit_bucket("GLOBAL", GLOBAL_RPM):
        logger.critical("[RATELIMIT] GLOBAL capacity exceeded! System under load.")
        return False

    return True
