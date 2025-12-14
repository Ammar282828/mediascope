# MediaScope - Dawn Newspaper Archive System (1990-1992)

Historical newspaper archive with AI-powered search, sentiment analysis, and interactive visualizations.

## Quick Start

### 1. Install Prerequisites

Download and install these (in order):

1. **Python 3.8+** → [python.org/downloads](https://www.python.org/downloads/)
2. **Node.js 16+** → [nodejs.org](https://nodejs.org/)
3. **Git** → [git-scm.com/downloads](https://git-scm.com/downloads)
4. **Firebase Project** → See [Firebase Setup](#firebase-setup) below

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

## Firebase Setup

MediaScope uses Firebase Firestore as its cloud database. **You need to set this up before running the app.**

### Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" or select an existing project
3. Follow the setup wizard (you can disable Google Analytics)

### Step 2: Enable Firestore

1. In your Firebase project, click "Firestore Database" in the left sidebar
2. Click "Create database"
3. Choose "Start in production mode"
4. Select a location (choose closest to your region)

### Step 3: Get Service Account Key

1. In Firebase Console, click the gear icon ⚙️ → "Project settings"
2. Go to "Service accounts" tab
3. Click "Generate new private key"
4. Save the downloaded JSON file as `firebase-service-account.json` in your project root

### Step 4: Configure Environment

Add this to your `.env` file:

```bash
# Firebase Configuration
FIREBASE_SERVICE_ACCOUNT_PATH=firebase-service-account.json
```

**Important:** Never commit `firebase-service-account.json` to Git! It's already in `.gitignore`.

For detailed instructions, see [FIREBASE_SETUP.md](FIREBASE_SETUP.md)

---

## What It Does

- **Search** - Find articles by keywords, entities, dates
- **Analytics** - View trends, sentiment analysis, statistics
- **AI Summaries** - Get article summaries powered by Google Gemini
- **Visualizations** - Interactive charts and graphs

## Tech Stack

**Backend:** Python, FastAPI, Firebase Firestore
**Frontend:** React, TypeScript, Recharts
**AI:** Google Gemini, spaCy NLP
**Database:** Firebase Firestore (Cloud NoSQL)

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

### "Firestore connection error"
```bash
# Check that you have the Firebase service account key file
ls firebase-service-account.json

# Make sure .env points to the correct file
cat .env | grep FIREBASE

# Verify the JSON file is valid
python -c "import json; json.load(open('firebase-service-account.json'))"
```

### "No module named 'firestore_db'"
```bash
# Make sure you're in the project directory and virtual environment is activated
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate     # Windows

# Then verify the file exists
ls firestore_db.py
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
