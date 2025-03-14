@echo off
echo Installing API Contract Testing CLI...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed. Please install Python 3.7 or higher from https://www.python.org/
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed. Please install Node.js from https://nodejs.org/
    exit /b 1
)

REM Check if npm is installed
npm --version >nul 2>&1
if errorlevel 1 (
    echo Error: npm is not installed. Please install npm from https://nodejs.org/
    exit /b 1
)

REM Install Python dependencies
echo Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Install Dredd globally
echo Installing Dredd...
call npm install -g dredd

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo.
    echo Please edit .env with your actual credentials:
    echo - API_USERNAME
    echo - API_PASSWORD
    echo - API_TOKEN
    echo.
)

echo.
echo Installation completed successfully!
echo.
echo You can now run the API tester using:
echo python api_tester.py --oas ^<path-to-oas-file^> --url ^<api-base-url^> --tool ^<tool-name^>
echo.
echo Example:
echo python api_tester.py --oas api/openapi.yaml --url http://localhost:3000 --tool schemathesis 