import os
import secrets
import time
import redis
from typing import Optional
from logger import logger

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(redis_url, decode_responses=True)

API_KEYS_SET = "api_keys"                 # all ACTIVE keys
API_KEY_META = "api_key_meta:"            # per-key meta prefix


def generate_key(owner: str, ttl_days: int = 365, auto_expire=True):
    key = secrets.token_urlsafe(32)
    now = int(time.time())
    ttl_seconds = ttl_days * 86400

    meta = {
        "owner": owner,
        "created_at": now,
        "ttl_days": ttl_days,
        "revoked": "0",
        "last_used": "0",
        "usage_count": "0"
    }

    pipe = r.pipeline()
    pipe.sadd(API_KEYS_SET, key)
    pipe.hset(API_KEY_META + key, mapping=meta)

    # optional: auto expire from Redis storage
    if auto_expire:
        pipe.expire(API_KEY_META + key, ttl_seconds)

    pipe.execute()

    logger.info(f"Created API key for {owner}")
    return key


def revoke_key(key: str):
    pipe = r.pipeline()
    pipe.hset(API_KEY_META + key, "revoked", "1")
    pipe.srem(API_KEYS_SET, key)
    pipe.execute()
    logger.info(f"Revoked API key {key}")


def is_key_valid(key: Optional[str]) -> bool:
    if not key:
        return False

    meta = r.hgetall(API_KEY_META + key)
    if not meta:
        return False

    # revoked?
    if meta.get("revoked", "1") == "1":
        return False

    # TTL enforcement
    created = int(meta.get("created_at", 0))
    ttl_days = int(meta.get("ttl_days", 0))
    expires_at = created + ttl_days * 86400

    if time.time() > expires_at:
        return False

    # update last_used + usage_count
    r.hset(API_KEY_META + key, mapping={
        "last_used": int(time.time()),
    })
    r.hincrby(API_KEY_META + key, "usage_count", 1)

    return True


def get_key_meta(key: str):
    return r.hgetall(API_KEY_META + key)
