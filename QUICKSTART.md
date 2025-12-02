# MediaScope - Quick Start Guide

## 🚀 Get Up and Running in 30 Minutes

This guide will get MediaScope running on your local machine quickly.

## Prerequisites Checklist

- [ ] macOS, Linux, or Windows with WSL2
- [ ] Python 3.10+ installed
- [ ] Node.js 18+ installed
- [ ] 8GB+ RAM
- [ ] 10GB+ free disk space

## Step 1: Install System Dependencies (5 minutes)

### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install PostgreSQL
brew install postgresql@14
brew services start postgresql@14

# Install Elasticsearch
brew tap elastic/tap
brew install elastic/tap/elasticsearch-full
brew services start elastic/tap/elasticsearch-full

# Verify installations
psql --version        # Should show PostgreSQL 14.x
curl http://localhost:9200  # Should return Elasticsearch info
```

### Ubuntu/Debian Linux

```bash
# PostgreSQL
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Elasticsearch
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
sudo apt update
sudo apt install elasticsearch
sudo systemctl start elasticsearch
sudo systemctl enable elasticsearch
```

## Step 2: Setup Database (5 minutes)

```bash
# Create PostgreSQL database
createdb mediascope

# Create database user (optional but recommended)
psql postgres -c "CREATE USER mediascope_user WITH PASSWORD 'your_secure_password';"
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE mediascope TO mediascope_user;"

# Load schema
psql mediascope < database_schema.sql

# Verify
psql mediascope -c "\dt"  # Should show all tables
```

## Step 3: Setup Backend (10 minutes)

```bash
# Create project directory
mkdir mediascope-project
cd mediascope-project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Download spaCy model (this may take a few minutes)
python -m spacy download en_core_web_lg

# Create .env file
cat > .env << EOL
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mediascope
DB_USER=postgres
DB_PASSWORD=your_password

# Elasticsearch
ES_HOST=localhost
ES_PORT=9200
ES_INDEX=mediascope_articles

# Gemini API (get your key from https://makersuite.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key

# JWT Secret (generate with: openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Paths
INPUT_FOLDER=./input_newspapers
OUTPUT_FOLDER=./processed_newspapers
EOL

# Create folders
mkdir -p input_newspapers processed_newspapers

# Test installation
python -c "import fastapi, spacy, transformers; print('✅ All imports successful')"
```

## Step 4: Start Backend Server (2 minutes)

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Start FastAPI server
uvicorn mediascope_api:app --reload --port 8000

# In a new terminal, test the API
curl http://localhost:8000/api/health
# Should return: {"status":"healthy","timestamp":"..."}

# View API documentation
# Open browser to: http://localhost:8000/docs
```

## Step 5: Setup Frontend (5 minutes)

```bash
# In a new terminal, create frontend directory
mkdir frontend
cd frontend

# Initialize React TypeScript project
npx create-react-app . --template typescript

# Install dependencies
npm install recharts axios

# Copy MediaScope components
cp ../MediaScopeDashboard.tsx src/
cp ../mediascope-dashboard.css src/

# Update src/App.tsx
cat > src/App.tsx << EOL
import React from 'react';
import MediaScopeDashboard from './MediaScopeDashboard';
import './mediascope-dashboard.css';

function App() {
  return <MediaScopeDashboard />;
}

export default App;
EOL

# Start development server
npm start

# Frontend will open at: http://localhost:3000
```

## Step 6: Process Your First Newspaper (5 minutes)

```bash
# Place newspaper scans in input_newspapers folder
cp /path/to/your/newspapers/*.jpg input_newspapers/

# Run the processing pipeline
python mediascope_complete_pipeline.py

# The pipeline will:
# ✅ Extract metadata (date, page number)
# ✅ Perform OCR
# ✅ Extract entities
# ✅ Analyze sentiment
# ✅ Store in database

# Check results in database
psql mediascope -c "SELECT COUNT(*) FROM articles;"
```

## Verification Checklist

After completing all steps, verify:

- [ ] PostgreSQL is running: `pg_isready`
- [ ] Elasticsearch is running: `curl http://localhost:9200`
- [ ] Backend API is running: `curl http://localhost:8000/api/health`
- [ ] Frontend is accessible: Open http://localhost:3000
- [ ] Database has tables: `psql mediascope -c "\dt"`
- [ ] At least one newspaper processed: Check database

## Quick Test

```bash
# 1. Search for articles (using curl or API docs)
curl -X POST http://localhost:8000/api/search/keyword \
  -H "Content-Type: application/json" \
  -d '{"query": "politics", "limit": 5}'

# 2. Get top entities
curl http://localhost:8000/api/analytics/top-entities?limit=10

# 3. Use the web interface
# Open http://localhost:3000
# Try searching for keywords like "election", "economy", etc.
```

## Common Issues & Solutions

### Issue 1: PostgreSQL connection refused
```bash
# Solution: Start PostgreSQL
brew services start postgresql@14  # macOS
sudo systemctl start postgresql    # Linux
```

### Issue 2: Elasticsearch not responding
```bash
# Solution: Start Elasticsearch
brew services start elastic/tap/elasticsearch-full  # macOS
sudo systemctl start elasticsearch                  # Linux

# Check logs
tail -f /usr/local/var/log/elasticsearch.log  # macOS
sudo journalctl -u elasticsearch              # Linux
```

### Issue 3: spaCy model not found
```bash
# Solution: Download model
python -m spacy download en_core_web_lg
```

### Issue 4: Gemini API rate limit
```
Error: Resource exhausted

# Solution: 
# 1. Wait for rate limit to reset (daily)
# 2. Or upgrade to paid tier
# 3. Or process newspapers in smaller batches
```

### Issue 5: Frontend can't connect to backend
```javascript
// Solution: Check CORS settings in mediascope_api.py
// Ensure backend URL is correct in frontend

// In MediaScopeDashboard.tsx, update:
const API_BASE = 'http://localhost:8000/api';
```

## Next Steps

Once everything is working:

1. **Process More Newspapers**: Add more scanned images to `input_newspapers/`

2. **Explore the Dashboard**:
   - Try different search queries
   - View trending keywords
   - Analyze sentiment patterns

3. **Customize Configuration**:
   - Edit `.env` for your specific setup
   - Modify `mediascope_complete_pipeline.py` for batch processing

4. **Add More Data**:
   - Import additional newspaper archives
   - Train topic models on larger datasets

5. **Deploy to Production**:
   - Use Docker for containerization
   - Deploy to Google Cloud Platform
   - Set up CI/CD pipeline

## Performance Tips

### For Large Datasets

```python
# In mediascope_complete_pipeline.py

# Use batch processing
batch_size = 10  # Process 10 newspapers at a time

# Enable multiprocessing
from multiprocessing import Pool
with Pool(4) as p:  # 4 parallel workers
    p.map(process_newspaper, newspaper_files)
```

### For Faster Search

```sql
-- Create additional indexes
CREATE INDEX CONCURRENTLY idx_articles_date 
ON articles((newspapers.publication_date));

-- Optimize Elasticsearch
PUT /mediascope_articles/_settings
{
  "index.refresh_interval": "30s"
}
```

## Resources

- **API Documentation**: http://localhost:8000/docs
- **Gemini API**: https://makersuite.google.com/app/apikey
- **spaCy Models**: https://spacy.io/models
- **BERTopic Guide**: https://maartengr.github.io/BERTopic/
- **FastAPI Docs**: https://fastapi.tiangolo.com/

## Getting Help

If you encounter issues:

1. Check the troubleshooting section in README.md
2. Look at the logs: `tail -f logs/mediascope.log`
3. Review API documentation at http://localhost:8000/docs
4. Contact the team:
   - Ammar Murtaza: am08721@st.habib.edu.pk

## Summary

You should now have:
- ✅ PostgreSQL database with schema
- ✅ Elasticsearch running and indexed
- ✅ FastAPI backend serving API
- ✅ React frontend with visualizations
- ✅ Processing pipeline ready to ingest newspapers

**Time to completion**: ~30 minutes

**Next milestone**: Process 10 newspapers and explore trends!

---

Happy analyzing! 📰📊🚀
