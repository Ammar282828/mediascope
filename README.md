# MediaScope - Dawn Newspaper Archive (1990-1992)

## Overview

MediaScope is a comprehensive digital archive and analysis system for Dawn newspaper issues from 1990-1992. It combines OCR, Natural Language Processing, sentiment analysis, and interactive visualization to transform historical newspaper scans into an intelligent, searchable database.

## Features

### 🔍 Intelligent Search
- **Keyword Search**: Full-text search across headlines and article content
- **Entity Search**: Find articles mentioning specific people, organizations, or locations
- **Advanced Filtering**: Filter by date range, sentiment, and topic

### 📊 Analytics & Visualization
- **Keyword Trends**: Track word frequency over time
- **Entity Tracking**: Monitor how often entities are mentioned and sentiment toward them
- **Topic Distribution**: Discover dominant themes during specific periods
- **Sentiment Analysis**: Understand the emotional tone of coverage

### 🤖 AI-Powered Processing
- **OCR**: Gemini 2.5 Flash for accurate text extraction
- **Named Entity Recognition**: spaCy for extracting people, organizations, locations
- **Sentiment Analysis**: RoBERTa for detecting article sentiment (-1 to +1 scale)
- **Topic Modeling**: BERTopic for automatic thematic categorization

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface (React)                    │
│  • Search Panel  • Trend Charts  • Analytics Dashboard      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  FastAPI Backend                             │
│  • REST API  • Authentication  • Search Engine              │
└────────────────────┬────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
┌─────────▼─────────┐  ┌────────▼──────────┐
│    PostgreSQL     │  │  Elasticsearch    │
│  • Structured DB  │  │  • Full-text      │
│  • Metadata       │  │  • Fast queries   │
│  • Relationships  │  │                   │
└───────────────────┘  └───────────────────┘
          ▲
          │
┌─────────┴────────────────────────────────────────────────┐
│              Processing Pipeline                          │
│  1. OCR (Gemini) → 2. NER (spaCy) →                     │
│  3. Sentiment (RoBERTa) → 4. Topics (BERTopic)          │
└──────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **PostgreSQL**: Relational database for structured data
- **Elasticsearch**: Search engine for full-text queries
- **Python 3.10+**

### AI/ML
- **Gemini 2.5 Flash**: OCR and image analysis
- **spaCy (en_core_web_lg)**: Named Entity Recognition
- **RoBERTa**: Sentiment analysis (cardiffnlp/twitter-roberta-base-sentiment-latest)
- **BERTopic**: Topic modeling
- **Sentence Transformers**: Text embeddings

### Frontend
- **React 18**: UI framework
- **TypeScript**: Type-safe JavaScript
- **Recharts**: Data visualization
- **Axios**: HTTP client

## Installation & Setup

### Prerequisites

```bash
# System requirements
- Python 3.10 or higher
- Node.js 18 or higher
- PostgreSQL 14 or higher
- Elasticsearch 8.x
- 8GB+ RAM recommended
```

### 1. Database Setup

#### PostgreSQL

```bash
# Install PostgreSQL (macOS with Homebrew)
brew install postgresql@14
brew services start postgresql@14

# Create database
createdb mediascope

# Run schema
psql mediascope < database_schema.sql
```

#### Elasticsearch

```bash
# Install Elasticsearch (macOS with Homebrew)
brew tap elastic/tap
brew install elastic/tap/elasticsearch-full
brew services start elastic/tap/elasticsearch-full

# Verify it's running
curl http://localhost:9200
```

### 2. Backend Setup

```bash
# Clone repository
git clone https://github.com/your-repo/mediascope.git
cd mediascope

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_lg

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and API keys

# Run database migrations (if using Alembic)
alembic upgrade head

# Start FastAPI server
uvicorn mediascope_api:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure API endpoint
# Edit src/config.ts with your backend URL

# Start development server
npm start
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### 4. Processing Pipeline

```bash
# Configure the pipeline
# Edit mediascope_complete_pipeline.py with your settings

# Process newspaper images
python mediascope_complete_pipeline.py

# The pipeline will:
# 1. Load images from INPUT_FOLDER
# 2. Extract metadata (date, page number)
# 3. Perform OCR to extract article text
# 4. Run NER to identify entities
# 5. Analyze sentiment
# 6. Store in PostgreSQL and Elasticsearch
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
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

# Gemini API
GEMINI_API_KEY=your_gemini_api_key

# JWT Secret (for authentication)
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Paths
INPUT_FOLDER=/path/to/newspaper/scans
OUTPUT_FOLDER=/path/to/processed/output
```

### Pipeline Configuration

Edit `mediascope_complete_pipeline.py`:

```python
@dataclass
class Config:
    # Gemini API
    GEMINI_API_KEY: str = "your_api_key"
    GEMINI_MODEL: str = "gemini-2-5-flash"
    
    # Database
    DB_HOST: str = "localhost"
    DB_NAME: str = "mediascope"
    
    # Paths
    INPUT_FOLDER: str = "/path/to/newspapers"
    OUTPUT_FOLDER: str = "/path/to/processed"
```

## Usage

### 1. Search Articles

**Keyword Search:**
```bash
curl -X POST http://localhost:8000/api/search/keyword \
  -H "Content-Type: application/json" \
  -d '{
    "query": "election",
    "start_date": "1990-01-01",
    "end_date": "1992-12-31",
    "limit": 20
  }'
```

**Entity Search:**
```bash
curl -X POST http://localhost:8000/api/search/entity \
  -H "Content-Type: application/json" \
  -d '{
    "entity_name": "Benazir Bhutto",
    "entity_type": "PERSON",
    "limit": 20
  }'
```

### 2. Get Trends

**Keyword Frequency:**
```bash
curl -X POST http://localhost:8000/api/analytics/keyword-trend \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["politics", "economy"],
    "start_date": "1990-01-01",
    "end_date": "1992-12-31",
    "granularity": "month"
  }'
```

**Entity Trends:**
```bash
curl http://localhost:8000/api/analytics/entity-trend?entity_name=Pakistan&start_date=1990-01-01&end_date=1992-12-31
```

### 3. Analytics

**Topic Distribution:**
```bash
curl -X POST http://localhost:8000/api/analytics/topic-distribution \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "1990-01-01",
    "end_date": "1990-12-31"
  }'
```

**Top Entities:**
```bash
curl http://localhost:8000/api/analytics/top-entities?entity_type=PERSON&limit=10
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database Schema

### Key Tables

**newspapers**: Metadata about newspaper issues
- `id`, `publication_date`, `page_number`, `section`, `image_path`

**articles**: Extracted articles
- `id`, `newspaper_id`, `headline`, `content`, `sentiment_score`, `topic_id`

**entities**: Named entities extracted from articles
- `id`, `article_id`, `entity_text`, `entity_type`

**topics**: Topic modeling results
- `id`, `topic_id`, `topic_name`, `keywords`

**advertisements**: Advertisement data
- `id`, `newspaper_id`, `industry_category`, `brand_name`

### Views & Functions

- `article_details`: Articles with full metadata
- `entity_mentions`: Aggregated entity statistics
- `topic_timeline`: Topic evolution over time
- `get_keyword_frequency()`: Keyword trends function
- `get_entity_trends()`: Entity mention trends function

## Development

### Running Tests

```bash
# Backend tests
pytest tests/

# Frontend tests
cd frontend
npm test
```

### Code Structure

```
mediascope/
├── backend/
│   ├── mediascope_api.py           # FastAPI application
│   ├── mediascope_complete_pipeline.py  # Processing pipeline
│   ├── models.py                    # Database models
│   └── utils.py                     # Utility functions
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── MediaScopeDashboard.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── styles/
│   │       └── mediascope-dashboard.css
│   └── package.json
├── database_schema.sql              # PostgreSQL schema
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template
└── README.md
```

## Troubleshooting

### Common Issues

**1. PostgreSQL Connection Error**
```bash
# Check if PostgreSQL is running
pg_isready

# Start PostgreSQL
brew services start postgresql@14
```

**2. Elasticsearch Not Running**
```bash
# Check status
brew services info elastic/tap/elasticsearch-full

# Start service
brew services start elastic/tap/elasticsearch-full
```

**3. Gemini API Rate Limits**
```
# Gemini Flash: 1,500 requests/day (free tier)
# Gemini Pro: 50 requests/day (free tier)

# Solution: Implement rate limiting in code or upgrade to paid tier
```

**4. spaCy Model Not Found**
```bash
# Download the model
python -m spacy download en_core_web_lg
```

**5. Out of Memory Errors**
```python
# Process newspapers in smaller batches
# Reduce batch size in BERTopic
# Use GPU acceleration if available
```

## Performance Optimization

### Database
- Create indexes on frequently queried columns
- Use connection pooling
- Regularly VACUUM and ANALYZE tables

### Elasticsearch
- Allocate sufficient heap memory (50% of RAM, max 32GB)
- Use bulk indexing for faster imports
- Configure appropriate refresh intervals

### Pipeline
- Process images in batches
- Use multiprocessing for parallel processing
- Cache OCR results to avoid reprocessing

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Team

- **Ammar Murtaza** - Backend & ML Integration
- **Izbal Mengal** - Frontend Development & UI Design
- **Mahnoor Aminullah** - Data Curation & QA
- **Mohammad Arqam Nakhuda** - Advertisement Analysis

**Supervisor**: Dr. Faisal Alvi

## License

This project is part of the Habib University Computer Science Capstone (Kaavish) program.

Copyright © 2025 Habib University

## Acknowledgments

- Dawn Newspaper for archive access
- Frere Hall Library for facilitating data collection
- Habib University DSSE for project support
- Google for Gemini API access
- Anthropic for Claude AI assistance

## Contact

For questions or collaboration:
- Email: am08721@st.habib.edu.pk
- Project Repository: [GitHub Link]

---

**MediaScope** - Illuminating Pakistan's Media History through AI
