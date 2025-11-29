
# 🔐 Secure AI Payment Gateway (FX + Fraud + Rate-Limit + Signed Quotes)

A fully-asynchronous, production-grade payment gateway backend built with **Flask**, **Redis**, and **Python**, designed to simulate real-world fintech infrastructure.

Includes:

- 🔑 Merchant API Key System
- 🚦 Multi-Layer Rate Limiter (IP + Key + Endpoint)
- 🛡 Advanced Fraud Engine (velocity + pattern detection)
- 💱 FX Engine with Spread, Markup & Slippage Protection
- ✍️ HMAC-Signed FX Quotes (Stripe-style security)
- ⏳ Anti-Replay Timestamp Validation
- ❌ Card Testing Bot Protection
- 🚨 Real-Time Logging
- 💳 Simulated Payment Processor

---

## ✨ Features

### 🔐 1. Merchant Authentication
Secure API key system stored in Redis:
- Create merchant keys
- Revoke keys instantly
- Prevent brute-force & impersonation attacks

### 🚦 2. Multi-Layer Rate Limiting
Token-bucket rate limiter using Redis Lua scripts:
- Per-API Key  
- Per-IP  
- Per-Endpoint  
- Global limit fallback  
- Atomic & bypass-proof  

### 🛡 3. Fraud Detection Engine
Blocks:
- High-velocity card testing  
- Suspicious IP activity  
- Invalid card ranges  
- Repeated failed attempts  

### 💱 4. FX Engine (with security)
- Fetches real-time FX  
- Applies spread & markup  
- Optional client quotes  
- **HMAC-signed quotes**  
- Slippage detection  
- Anti-replay timestamp checks  

### 🔒 5. Security Highlights
- Signed FX quotes  
- Anti-replay protection  
- No plaintext card logging  
- Redis-backed rate limiting  
- Instant key revocation  
- Sandbox payment simulation  

---

## 🚀 Running the Server (No Docker Needed)

### 1. Create a virtual environment
```
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

### 2. Install dependencies
```
pip install -r requirements.txt
```

### 3. Create your .env
```
MASTER_ADMIN_KEY=youradminkeyhere
RATE_SIGNING_KEY=yourratesigningkeyhere
REDIS_URL=redis://localhost:6379/0
```

### 4. Start Redis
```
redis-server
```

### 5. Run the server
```
python main.py
```

Gateway runs at:
```
http://localhost:5000
```

---

# 📌 Running the Project Using Scripts (Windows / Linux / Mac)

To make running the gateway easier, this project includes cross-platform startup scripts inside the `scripts/` folder.

---

## 🚀 Windows (One-Click Start)

Run:

```
scripts\run_gateway.bat
```

This will:

- Activate virtual environment (if present)
- Start the Flask server
- Open: http://127.0.0.1:5000

---

## 🐧 Linux

Make executable:

```
chmod +x scripts/run_linux.sh
```

Run:

```
./scripts/run_linux.sh
```

---

## 🍎 MacOS

Make executable:

```
chmod +x scripts/run_mac.sh
```

Run:

```
./scripts/run_mac.sh
```

---

## ⚙️ Automatic Environment Setup

### Windows
```
scripts\setup_env.bat
```

### Linux / Mac
```
chmod +x scripts/setup_env.sh
./scripts/setup_env.sh
```

---

## 📂 Project Structure

```
src/
 ├── auth.py
 ├── currency_manager.py
 ├── fraud_engine.py
 ├── logger.py
 ├── main.py
 ├── payment_router.py
 ├── rate_limiter.py
 └── templates/
       └── checkout.html

scripts/
 ├── run_gateway.bat
 ├── run_linux.sh
 ├── run_mac.sh
 ├── setup_env.bat
 └── setup_env.sh

test/
 ├── fx_poison_slippage_replay_test.py
 ├── ip_spoof_test.py
 ├── key_revoke_race.py
 ├── merchant_bruteforce_test.py
 └── stress_rate_limiter.py
```

---

## 🧪 Testing (Security Scripts Included)

This project includes advanced test scripts for:

- Rate limiter stress  
- API key brute-force  
- Merchant impersonation  
- Replay attack  
- FX poisoning  
- Slippage brute-force  
- Redis cache poisoning  
- Multi-IP botnet simulation  

---

## 🛡 Recommended Production Enhancements

- Redis ACL protection  
- Private subnet deployment  
- HTTPS termination  
- Single-use quote IDs  
- Gunicorn/Uvicorn + Nginx  
- Horizontal rate-limiter scaling  

---

## ⭐ Author
**Aravind A.**  
19-year-old fintech backend developer passionate about security, fraud detection, and real-time payment systems.

---
