#!/bin/bash

echo "Installing API Contract Testing CLI..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python is not installed. Please install Python 3.7 or higher from https://www.python.org/"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed. Please install npm from https://nodejs.org/"
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt

# Install Dredd globally
echo "Installing Dredd..."
npm install -g dredd

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo
    echo "Please edit .env with your actual credentials:"
    echo "- API_USERNAME"
    echo "- API_PASSWORD"
    echo "- API_TOKEN"
    echo
fi

echo
echo "Installation completed successfully!"
echo
echo "You can now run the API tester using:"
echo "python api_tester.py --oas <path-to-oas-file> --url <api-base-url> --tool <tool-name>"
echo
echo "Example:"
echo "python api_tester.py --oas api/openapi.yaml --url http://localhost:3000 --tool schemathesis" 