#!/bin/bash
echo "Setting up environment..."

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

echo "Creating .env from template..."
cp .env.example .env

echo "Done!"
