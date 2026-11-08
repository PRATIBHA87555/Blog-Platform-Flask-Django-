@echo off
cd /d "%~dp0"
echo Installing requirements (first time only)...
python -m pip install -r requirements.txt
echo.
echo Starting Inkwell...
python app.py
pause
