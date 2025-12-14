#!/bin/bash

# MediaScope Setup Script for Mac/Linux
# This script sets up the entire project automatically

set -e  # Exit on any error

echo "================================"
echo "MediaScope Automatic Setup"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
echo -e "${YELLOW}Checking prerequisites...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install it from https://www.python.org/downloads/"
    exit 1
fi
echo "✅ Python 3 found"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install it from https://nodejs.org/"
    exit 1
fi
echo "✅ Node.js found"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed. Please install it from https://www.postgresql.org/download/"
    exit 1
fi
echo "✅ PostgreSQL found"

echo ""
echo -e "${GREEN}Step 1: Setting up Python virtual environment${NC}"
python3 -m venv venv
source venv/bin/activate
echo "✅ Virtual environment created"

echo ""
echo -e "${GREEN}Step 2: Installing Python dependencies${NC}"
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Python packages installed"

echo ""
echo -e "${GREEN}Step 3: Installing spaCy language model${NC}"
python -m spacy download en_core_web_sm
echo "✅ spaCy model downloaded"

echo ""
echo -e "${GREEN}Step 4: Setting up PostgreSQL database${NC}"

# Check if database exists
if psql -lqt | cut -d \| -f 1 | grep -qw mediascope; then
    echo "⚠️  Database 'mediascope' already exists. Skipping creation."
else
    # Create database and user
    echo "Creating database..."
    createdb mediascope || true

    # Try to create user (may fail if already exists, that's ok)
    psql postgres -c "CREATE USER mediascope_user WITH PASSWORD 'mediascope_pass';" 2>/dev/null || true
    psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE mediascope TO mediascope_user;" 2>/dev/null || true

    echo "✅ Database created"
fi

echo ""
echo -e "${GREEN}Step 5: Creating environment file${NC}"
if [ ! -f .env ]; then
    cat > .env << EOL
# Database Configuration
DB_HOST=localhost
DB_NAME=mediascope
DB_USER=mediascope_user
DB_PASSWORD=mediascope_pass

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# API Configuration
API_PORT=8000

# Legacy settings
DATABASE_URL=postgresql://mediascope_user:mediascope_pass@localhost:5432/mediascope
ELASTICSEARCH_URL=http://elasticsearch:9200

# Gemini API Key - GET THIS FROM: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here
EOL
    echo "✅ .env file created"
else
    echo "⚠️  .env file already exists. Skipping..."
fi

echo ""
echo -e "${GREEN}Step 6: Installing frontend dependencies${NC}"
cd mediascope-frontend
npm install
cd ..
echo "✅ Frontend packages installed"

echo ""
echo -e "${GREEN}Step 7: Updating frontend configuration${NC}"
cat > mediascope-frontend/.env.local << EOL
# Development API URL (localhost)
REACT_APP_API_URL=http://localhost:8000
EOL
echo "✅ Frontend configured for local development"

echo ""
echo "================================"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "================================"
echo ""
echo "📝 NEXT STEPS:"
echo ""
echo "1. Get your Gemini API key:"
echo "   → Visit: https://makersuite.google.com/app/apikey"
echo "   → Copy your API key"
echo "   → Edit .env file and add: GEMINI_API_KEY=your_key_here"
echo ""
echo "2. Make sure PostgreSQL is running:"
echo "   → Mac: brew services start postgresql"
echo "   → Linux: sudo systemctl start postgresql"
echo ""
echo "3. Start the backend (Terminal 1):"
echo "   → source venv/bin/activate"
echo "   → python mediascope_api.py"
echo ""
echo "4. Start the frontend (Terminal 2):"
echo "   → cd mediascope-frontend"
echo "   → npm start"
echo ""
echo "5. Open http://localhost:3000 in your browser"
echo ""
echo "================================"
echo "Happy searching! 🔍"
echo "================================"
