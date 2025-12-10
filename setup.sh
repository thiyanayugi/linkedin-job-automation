#!/bin/bash

# LinkedIn Job Search Automation - Setup Script

echo "=================================="
echo "LinkedIn Job Automation - Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data
mkdir -p logs
mkdir -p config

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your API keys."
else
    echo ""
    echo "⚠️  .env file already exists, skipping..."
fi

# Create placeholder for resume
if [ ! -f data/resume.pdf ]; then
    echo ""
    echo "⚠️  Please add your resume PDF to: data/resume.pdf"
fi

# Check for Google credentials
if [ ! -f config/google_credentials.json ]; then
    echo ""
    echo "⚠️  Please add your Google credentials to: config/google_credentials.json"
fi

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Add your resume PDF to data/resume.pdf"
echo "3. Add Google credentials to config/google_credentials.json"
echo "4. Update config/filters.json with your job search criteria"
echo "5. Run: source venv/bin/activate"
echo "6. Test: python src/main.py"
echo ""
echo "For detailed instructions, see README.md"
echo ""
