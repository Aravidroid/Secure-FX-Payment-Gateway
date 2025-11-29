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
```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create your `.env`
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
```bash
python main.py
```

Server runs at:
```
http://localhost:5000
```

---

## 📂 Project Structure

```
src/
 ├── main.py
 ├── auth.py
 ├── rate_limiter.py
 ├── payment_router.py
 ├── currency_manager.py
 ├── fraud_engine.py
 ├── logger.py
 └── templates/
       └── checkout.html
test/
 ├── stress_rate_limiter.py
 ├── ip_spoof_test.py
 ├── fx_poison_slippage_replay_test.py
 └── botnet_simulator.py  (optional)
```

---

## 🧪 Testing (Security Scripts Included)

This project includes advanced test scripts for:

- Rate limiter stress  
- Fraud engine hardening  
- API key brute-force  
- Merchant impersonation  
- FX replay attack  
- FX slippage brute attack  
- Redis cache poisoning  
- Multi-IP botnet simulation  

---

## 🛡 Recommended Production Enhancements

- Redis ACLs  
- Quote IDs for single-use quotes  
- Gunicorn/Uvicorn  
- HTTPS termination  
- Private network for Redis  

---

## ⭐ Author
**Aravind A.**  
19-year-old fintech backend developer passionate about security, fraud detection, and real-time payment systems.

---
