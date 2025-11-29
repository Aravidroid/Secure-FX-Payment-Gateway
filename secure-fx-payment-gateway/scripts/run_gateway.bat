@echo off
echo ==========================================
echo Starting Secure AI Payment Gateway (Windows)
echo ==========================================
echo.

REM Activate virtual environment if exists
IF EXIST venv\Scripts\activate (
    call venv\Scripts\activate
)

REM Run flask
python -m flask run --host=127.0.0.1 --port=5000

echo.
echo Server stopped.
pause
