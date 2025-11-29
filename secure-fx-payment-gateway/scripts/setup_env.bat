@echo off
echo Setting up environment...

python -m venv venv
call venv\Scripts\activate

pip install -r requirements.txt

echo Creating .env from template...
copy .env.example .env

echo Setup complete.
pause
