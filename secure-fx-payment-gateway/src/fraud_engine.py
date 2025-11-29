import re
import time
import ipaddress

# ---------------------------
# Configurable Rules
# ---------------------------
BLACKLISTED_IPS = [
    "192.168.1.66",
    "10.0.0.5",
    "192.168.0.0/24"   # Support for subnet blocks
]

HIGH_VALUE_THRESHOLD = 10000

ALLOWED_CURRENCIES = {
    "USD", "EUR", "GBP", "INR", "MYR", "KRW", "JPY", "AUD", "CAD", "AED"
}

# IP velocity store (mock Redis)
IP_ACTIVITY = {}   # { ip: [timestamps] }


# ---------------------------
# Utility Functions
# ---------------------------

def ip_is_blacklisted(ip):
    for entry in BLACKLISTED_IPS:
        # CIDR support
        if "/" in entry:
            if ipaddress.ip_address(ip) in ipaddress.ip_network(entry, strict=False):
                return True
        else:
            if ip == entry:
                return True
    return False


def luhn_check(card_number):
    card_number = re.sub(r'\D', '', str(card_number))
    digits = [int(d) for d in card_number][::-1]
    checksum = 0
    
    for i, digit in enumerate(digits):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
        
    return checksum % 10 == 0


def validate_card_format(card_number):
    clean_num = re.sub(r'\D', '', str(card_number))
    if not (13 <= len(clean_num) <= 19):
        return False
    return luhn_check(clean_num)


def register_transaction(ip):
    """Tracks velocity of transactions from the same IP."""
    now = time.time()
    IP_ACTIVITY.setdefault(ip, [])
    IP_ACTIVITY[ip].append(now)

    # keep only last 60 seconds
    IP_ACTIVITY[ip] = [t for t in IP_ACTIVITY[ip] if now - t < 60]

    return len(IP_ACTIVITY[ip])


# ---------------------------
# Fraud Detection Logic
# ---------------------------

def detect_fraud(data, client_ip):
    """
    Returns (is_fraud: bool, reason: str)
    """

    amount = data.get("amount", 0)
    currency = data.get("currency", "MYR")

    # 1. IP Blacklist
    if ip_is_blacklisted(client_ip):
        return True, "IP_BLACKLISTED"

    # 2. High-value Check
    if amount > HIGH_VALUE_THRESHOLD:
        return True, "AMOUNT_LIMIT_EXCEEDED"

    # 3. Unsupported Currency
    if currency not in ALLOWED_CURRENCIES:
        return True, "UNSUPPORTED_CURRENCY"

    # 4. Velocity Check (too many attempts)
    count = register_transaction(client_ip)
    if count > 5:   # >5 attempts in 60 seconds
        return True, "HIGH_VELOCITY"

    return False, None


# ---------------------------
# PCI: Mask Sensitive Data
# ---------------------------

def sanitize_card_data(data):
    safe = {**data}   # safe copy

    if "card_number" in safe:
        card = re.sub(r'\D', '', str(safe["card_number"]))
        safe["card_number"] = f"**** **** **** {card[-4:]}" if len(card) >= 4 else "****"

    if "cvc" in safe:
        safe["cvc"] = "***"

    if "expiry" in safe:
        safe["expiry"] = "**/**"

    if "cardholder" in safe:
        safe["cardholder"] = safe["cardholder"][0] + "***"

    return safe
