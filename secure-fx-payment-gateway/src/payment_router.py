# src/payment_router.py
import os
import time
import hmac
import hashlib
import asyncio
import uuid
import random
from decimal import Decimal, ROUND_HALF_UP
from currency_manager import get_forex_rate

FX_RATE_VALIDITY_SEC = 60           # Rate must be used within 1 minute
FX_MARKUP_PERCENT = 0.35            # 0.35% markup for cross-border FX
SYSTEM_FEE_PERCENT = 0.20           # Internal gateway fee on settlement
MAX_SLIPPAGE_TOLERANCE = 0.50       # Allow 0.50% FX slippage
ALLOWED_TIMESTAMP_SKEW = 5          # seconds allowed in the future for client timestamps



def precise(value, places=2):
    """ 2-decimal precise rounding using banking rules. """
    return float(Decimal(str(value)).quantize(Decimal(f"1.{'0'*places}"), rounding=ROUND_HALF_UP))


def _verify_rate_signature(rate_str, expires_str, rate_signature):
    """
    Verify HMAC-SHA256 signature of the FX rate quote.
    
    The signature is computed over the concatenation of rate|expires_at.
    Uses a secret key from environment variable RATE_SIGNING_KEY.
    Also checks that the expiry timestamp is not in the past.
    """
    secret_key = os.getenv("RATE_SIGNING_KEY", "default-secret-key")
    message = f"{rate_str}|{expires_str}"
    
    # Compute expected signature
    expected_signature = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures using constant-time comparison
    if not hmac.compare_digest(expected_signature, rate_signature):
        return False
    
    # Check expiry
    try:
        now = time.time()
        expires_at = float(expires_str)
        if expires_at < now:
            return False
    except (ValueError, TypeError):
        return False
    
    return True

async def process_payment(data):
    """
    GLOBAL CROSS-BORDER PAYMENT FLOW

    Supports OPTIONAL client-supplied signed quote:
      - client_rate (string or numeric)
      - rate_expires_at (epoch seconds)
      - rate_signature (HMAC-SHA256 hex)
    If client sends a signed quote we validate signature+expiry and use that rate.
    Otherwise the server fetches the authoritative base rate via get_forex_rate().

    Also defends against timestamp replay:
      - Rejects timestamps older than FX_RATE_VALIDITY_SEC
      - Rejects timestamps more than ALLOWED_TIMESTAMP_SKEW seconds in the future
    """

    merchant_currency = "MYR"
    customer_currency = data["currency"]
    amount = Decimal(str(data["amount"]))
    client_rate_timestamp = data.get("rate_timestamp", None)

    # --------------------------
    # Timestamp / replay protection
    # --------------------------
    if client_rate_timestamp is not None:
        try:
            now = time.time()
            client_rate_timestamp = float(client_rate_timestamp)
            age = now - client_rate_timestamp

            # Reject if older than allowed validity or too far in future
            if age > FX_RATE_VALIDITY_SEC or client_rate_timestamp > now + ALLOWED_TIMESTAMP_SKEW:
                return {
                    "status": "failed",
                    "error": "fx_rate_expired",
                    "message": "FX rate expired or invalid timestamp."
                }
        except Exception:
            return {
                "status": "failed",
                "error": "invalid_rate_timestamp",
                "message": "rate_timestamp must be a numeric epoch timestamp."
            }

    # --------------------------
    # Single-currency optimization
    # --------------------------
    if customer_currency == merchant_currency:
        settlement_amount = precise(amount)
        return _finalize_success(
            original_amount=amount,
            original_currency=customer_currency,
            converted_amount=settlement_amount,
            exchange_rate=1.0,
            settlement_currency=merchant_currency
        )

    # --------------------------
    # Option A: Use client-supplied signed quote (if present)
    # --------------------------
    client_rate = data.get("client_rate", None)           # numeric or string
    rate_expires_at = data.get("rate_expires_at", None)   # epoch seconds as string/number
    rate_signature = data.get("rate_signature", None)     # hex string

    base_rate = None

    if client_rate and rate_expires_at and rate_signature:
        # Perform signature verification
        try:
            rate_str = str(client_rate)
            expires_str = str(rate_expires_at)
            if _verify_rate_signature(rate_str, expires_str, rate_signature):
                # signature is valid and expires_at is sensible; use client_rate
                base_rate = Decimal(str(client_rate))
            else:
                return {
                    "status": "failed",
                    "error": "invalid_rate_signature",
                    "message": "Supplied FX quote signature is invalid or expired."
                }
        except Exception:
            return {
                "status": "failed",
                "error": "invalid_rate_format",
                "message": "client_rate or rate_expires_at malformed."
            }

    # --------------------------
    # Option B: Fetch server-side authoritative FX rate
    # --------------------------
    if base_rate is None:
        fetched_rate = get_forex_rate(customer_currency, merchant_currency)
        if not fetched_rate:
            return {
                "status": "failed",
                "error": "forex_rate_unavailable"
            }
        base_rate = Decimal(str(fetched_rate))

    # sanity checks on base_rate
    try:
        if base_rate <= 0:
            return {
                "status": "failed",
                "error": "invalid_forex_rate",
                "message": "Exchange rate invalid."
            }
    except Exception:
        return {
            "status": "failed",
            "error": "invalid_forex_rate",
            "message": "Exchange rate invalid."
        }

    # --------------------------
    # Apply Markup
    # --------------------------
    markup_factor = Decimal("1") + (Decimal(str(FX_MARKUP_PERCENT)) / Decimal("100"))
    applied_rate = base_rate * markup_factor

    # --------------------------
    # Slippage Protection
    # --------------------------
    slippage_limit = base_rate * (Decimal("1") + Decimal(str(MAX_SLIPPAGE_TOLERANCE)) / Decimal("100"))
    if applied_rate > slippage_limit:
        return {
            "status": "failed",
            "error": "slippage_exceeded",
            "message": "Exchange rate changed too much. Please retry."
        }

    # --------------------------
    # Perform Conversion
    # --------------------------
    converted = amount * applied_rate
    converted_amount = precise(converted)

    # --------------------------
    # Apply PSP Settlement Fee
    # --------------------------
    system_fee = precise((Decimal(str(SYSTEM_FEE_PERCENT)) / Decimal("100")) * Decimal(str(converted_amount)))
    final_settlement = precise(Decimal(str(converted_amount)) - Decimal(str(system_fee)))

    # Simulate network latency
    await asyncio.sleep(0.8)

    # Actual success/failure simulation
    success = random.random() > 0.1  # 90% approval rate
    if not success:
        return {
            "status": "failed",
            "error": "issuer_declined"
        }

    # --------------------------
    # Return success
    # --------------------------
    return _finalize_success(
        original_amount=amount,
        original_currency=customer_currency,
        converted_amount=final_settlement,
        exchange_rate=float(applied_rate),
        settlement_currency=merchant_currency,
        fee=float(system_fee),
        markup_percent=FX_MARKUP_PERCENT
    )

def _finalize_success(
    original_amount,
    original_currency,
    converted_amount,
    exchange_rate,
    settlement_currency,
    fee=0.0,
    markup_percent=0.0
):
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

    return {
        "status": "success",
        "transaction_id": transaction_id,
        "original_amount": float(original_amount),
        "original_currency": original_currency,
        "settlement_currency": settlement_currency,
        "settlement_amount": float(converted_amount),
        "applied_rate": exchange_rate,
        "fx_markup_percent": markup_percent,
        "system_fee": fee,
        "message": "Approved"
    }
