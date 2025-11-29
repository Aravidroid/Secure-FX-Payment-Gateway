#!/bin/bash
echo "=========================================="
echo "Starting Secure AI Payment Gateway (Linux)"
echo "=========================================="
echo ""

# Activate venv if exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

export FLASK_APP=main.py
export FLASK_ENV=production

flask run --host=127.0.0.1 --port=5000
