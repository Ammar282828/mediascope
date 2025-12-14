# MediaScope - Dawn Newspaper Archive System (1990-1992)

Historical newspaper archive with AI-powered search, sentiment analysis, and interactive visualizations.

## Quick Start

### 1. Install Prerequisites

Download and install these (in order):

1. **Python 3.8+** → [python.org/downloads](https://www.python.org/downloads/)
2. **Node.js 16+** → [nodejs.org](https://nodejs.org/)
3. **PostgreSQL** → [postgresql.org/download](https://www.postgresql.org/download/)
4. **Git** → [git-scm.com/downloads](https://git-scm.com/downloads)

### 2. Clone & Setup

```bash
# Clone the repository
git clone https://github.com/Ammar282828/mediascope.git
cd mediascope

# Run automatic setup
# Mac/Linux:
chmod +x setup.sh && ./setup.sh

# Windows:
setup.bat
```

That's it! The setup script does everything automatically.

### 3. Start the App

**Terminal 1 - Backend:**
```bash
# Mac/Linux:
source venv/bin/activate
python mediascope_api.py

# Windows:
venv\Scripts\activate
python mediascope_api.py
```

**Terminal 2 - Frontend:**
```bash
cd mediascope-frontend
npm start
```

**Open:** http://localhost:3000

### 4. Upload Sample Newspapers (Optional)

The database starts empty. To add sample newspapers:

1. Open http://localhost:3000
2. Look for the upload/OCR section in the UI
3. Upload newspapers from the `input_newspapers/` folder
4. The system will process them automatically with OCR and sentiment analysis

Or use the API directly:
```bash
curl -X POST "http://localhost:8000/api/ocr/upload-bulk" \
  -F "files=@input_newspapers/Mar_25_90_p1.jpg"
```

---

## What It Does

- **Search** - Find articles by keywords, entities, dates
- **Analytics** - View trends, sentiment analysis, statistics
- **AI Summaries** - Get article summaries powered by Google Gemini
- **Visualizations** - Interactive charts and graphs

## Tech Stack

**Backend:** Python, FastAPI, PostgreSQL
**Frontend:** React, TypeScript, Recharts
**AI:** Google Gemini, spaCy NLP

## Project Structure

```
mediascope/
├── mediascope_api.py          # Backend API server
├── mediascope-frontend/       # React frontend app
├── requirements.txt           # Python packages
├── .env                       # Your config (don't commit!)
├── setup.sh / setup.bat       # Automatic setup scripts
└── README.md                  # This file
```

## Troubleshooting

### "Can't connect to database"
```bash
# Make sure PostgreSQL is running
# Mac:
brew services start postgresql

# Windows:
# Open Services app and start PostgreSQL

# Linux:
sudo systemctl start postgresql
```

### "Port already in use"
```bash
# Kill the process on port 8000 or 3000
# Mac/Linux:
lsof -ti:8000 | xargs kill

# Windows:
netstat -ano | findstr :8000
# Then: taskkill /PID <number> /F
```

### "Module not found"
```bash
# Activate virtual environment first!
# Mac/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Then install:
pip install -r requirements.txt
```

## Features

### Search
- Full-text keyword search
- Entity search (people, places, organizations)
- Date range filtering
- Sentiment filtering

### Analytics
- Keyword trends over time
- Sentiment analysis timeline
- Top keywords and entities
- Article statistics

### AI Features
- Article summarization
- Named entity recognition
- Sentiment classification
- Topic detection

## API Endpoints

Backend runs on `http://localhost:8000`

- `GET /api/articles` - Search articles
- `GET /api/articles/{id}` - Get article details
- `GET /api/analytics/sentiment-over-time` - Sentiment trends
- `GET /api/analytics/top-keywords` - Popular keywords
- `POST /api/ai/summarize` - Generate summary

**Full API docs:** http://localhost:8000/docs

## Team

**Developers:**
- Ammar Murtaza - Backend & ML
- Izbal Mengal - Frontend & UI
- Mahnoor Aminullah - Data & QA
- Mohammad Arqam Nakhuda - Analytics

**Supervisor:** Dr. Faisal Alvi
**Institution:** Habib University

## License

Educational project for Habib University Kaavish program.

---

**Questions?** Open an issue on GitHub or contact am08721@st.habib.edu.pk
