import os
import asyncio
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Auth + Rate Limit
from auth import generate_key, revoke_key, is_key_valid
from rate_limiter import allow_request

# Fraud & Logging
from fraud_engine import detect_fraud, sanitize_card_data, validate_card_format
from logger import logger

# Payments
from payment_router import process_payment

# FX & Signed Quote
from currency_manager import get_forex_rate, build_signed_quote

load_dotenv()
app = Flask(__name__)


# ============================================================
# HOME / CHECKOUT
# ============================================================

@app.get("/")
def home():
    return render_template("checkout.html")


# ============================================================
# ADMIN ROUTES
# ============================================================

@app.post("/admin/generate-key")
def admin_generate_key():
    master_key = request.args.get("master_key")
    merchant_name = request.args.get("merchant_name")

    if master_key != os.getenv("MASTER_ADMIN_KEY"):
        return jsonify({"error": "admin key invalid"}), 401

    if not merchant_name:
        return jsonify({"error": "merchant_name required"}), 400

    key = generate_key(merchant_name)
    return jsonify({"api_key": key})


# ============================================================
# PAYMENT ROUTE
# ============================================================

@app.post("/v1/charges")
async def create_charge():
    # 1. Merchant Authentication
    api_key = request.headers.get("X-API-KEY")
    if not is_key_valid(api_key):
        return jsonify({"error": "Invalid Merchant Key"}), 401

    client_ip = request.remote_addr
    endpoint = "/v1/charges"

    # 2. Rate-Limit Protection
    if not allow_request(api_key, client_ip, endpoint):
        return jsonify({"error": "Rate limit exceeded"}), 429

    # 3. Body Validation
    data = request.get_json()
    required_fields = ["amount", "currency", "card_number", "exp_month", "exp_year", "cvc"]
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Missing payment details"}), 400

    # 4. Card Format Check
    if not validate_card_format(data["card_number"]):
        return jsonify({"error": "Invalid card number format"}), 400

    # 5. Fraud Detection
    is_fraud, reason = detect_fraud(data, client_ip)
    if is_fraud:
        logger.warning(f"Fraud blocked: {reason} | IP: {client_ip}")
        return jsonify({"error": "Transaction declined by fraud filters", "code": "fraud_detect"}), 403

    # 6. Safe Logging (PCI-DSS compliant)
    safe_log_data = sanitize_card_data(data)
    logger.info({
        "event": "charge_attempt",
        "merchant": api_key[:6] + "...",
        "amount": data["amount"],
        "currency": data["currency"]
    })

    # 7. Route to Payment Processor
    try:
        result = await process_payment(data)

        if result["status"] == "failed":
            return jsonify(result), 402  # Payment failed
        return jsonify(result), 200

    except Exception as e:
        logger.exception("Payment backend failure")
        return jsonify({"error": "Payment processor error"}), 500


# ============================================================
# FX QUOTE ROUTE (SIGNED QUOTE SYSTEM)
# ============================================================

@app.get("/v1/quote")
def get_fx_quote():
    """
    Returns a signed FX quote with:
    - base rate (includes spread)
    - converted amount
    - expires_at
    - signature (HMAC-SHA256)
    """

    base_currency = request.args.get("from", "USD")
    target_currency = request.args.get("to", "MYR")
    amount = float(request.args.get("amount", 0))

    # Fetch FX rate (includes internal 2% spread)
    rate = get_forex_rate(base_currency, target_currency)
    if not rate:
        return jsonify({"error": "Could not fetch rate"}), 503

    # Build signed FX quote
    signed_quote = build_signed_quote(rate, amount, target_currency)

    return jsonify(signed_quote), 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)