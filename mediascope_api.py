#!/usr/bin/env python3
"""
MediaScope FastAPI Backend
Endpoints for search, analytics, and trend visualization
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
from elasticsearch import Elasticsearch
import jwt
from passlib.context import CryptContext
from functools import lru_cache

# ============================================
# CONFIGURATION
# ============================================

class Settings:
    """Application settings"""
    # Database
    DB_HOST = "localhost"
    DB_PORT = 5432
    DB_NAME = "mediascope"
    DB_USER = "mediascope_user"
    DB_PASSWORD = "your_secure_password"
    
    # Elasticsearch
    ES_HOST = "localhost"
    ES_PORT = 9200
    ES_INDEX = "mediascope_articles"
    
    # JWT
    SECRET_KEY = "your-secret-key-change-in-production"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30


settings = Settings()

# ============================================
# PYDANTIC MODELS
# ============================================

class ArticleResponse(BaseModel):
    """Article response model"""
    id: str
    headline: str
    content: str
    publication_date: date
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    topic_label: Optional[str]
    page_number: int
    section: Optional[str]
    entities: List[Dict[str, str]] = []


class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., min_length=1, max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    sentiment: Optional[str] = None  # 'positive', 'neutral', 'negative'
    topic: Optional[str] = None
    limit: int = Field(100, ge=1, le=100)
    offset: int = Field(0, ge=0)


class EntitySearchRequest(BaseModel):
    """Entity search request"""
    entity_name: str = Field(..., min_length=1)
    entity_type: Optional[str] = None  # PERSON, ORG, GPE, etc.
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    limit: int = Field(100, ge=1, le=100)


class TrendRequest(BaseModel):
    """Trend analysis request"""
    keywords: List[str] = Field(..., min_items=1, max_items=5)
    start_date: date
    end_date: date
    granularity: str = Field("day", pattern="^(day|week|month)$")


class TopicDistributionRequest(BaseModel):
    """Topic distribution request"""
    start_date: date
    end_date: date


class UserCreate(BaseModel):
    """User registration model"""
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    """User login model"""
    email: str
    password: str


# ============================================
# DATABASE CONNECTION
# ============================================

def get_db_connection():
    """Get PostgreSQL database connection"""
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        cursor_factory=RealDictCursor
    )
    return conn


def get_es_client():
    """Get Elasticsearch client"""
    return Elasticsearch([f"http://{settings.ES_HOST}:{settings.ES_PORT}"])


# ============================================
# FASTAPI APP
# ============================================

app = FastAPI(
    title="MediaScope API",
    description="API for Dawn Newspaper Archive Analysis (1990-1992)",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# AUTHENTICATION
# ============================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@app.post("/api/auth/register")
async def register(user: UserCreate):
    """Register a new user"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Hash password
        hashed_password = pwd_context.hash(user.password)
        
        # Insert user
        cur.execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s)
            RETURNING id, username, email
        """, (user.username, user.email, hashed_password))
        
        user_data = cur.fetchone()
        conn.commit()
        
        return {"message": "User registered successfully", "user": user_data}
    
    except psycopg2.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists")
    finally:
        cur.close()
        conn.close()


@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    """Login user"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id, username, email, password_hash 
            FROM users 
            WHERE email = %s AND is_active = TRUE
        """, (credentials.email,))
        
        user = cur.fetchone()
        
        if not user or not pwd_context.verify(credentials.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create JWT token
        token_data = {"sub": str(user['id']), "email": user['email']}
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Update last login
        cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user['id'],))
        conn.commit()
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user['id']),
                "username": user['username'],
                "email": user['email']
            }
        }
    
    finally:
        cur.close()
        conn.close()


# ============================================
# SEARCH ENDPOINTS
# ============================================

@app.post("/api/search/keyword", response_model=Dict[str, Any])
async def search_keyword(request: SearchRequest):
    """
    Search articles by keyword using Elasticsearch
    
    Searches in both headlines and content
    Returns matching articles with highlighting
    """
    es = get_es_client()
    
    # Build query
    query = {
        "bool": {
            "must": [
                {
                    "multi_match": {
                        "query": request.query,
                        "fields": ["headline^2", "content"],
                        "type": "best_fields"
                    }
                }
            ],
            "filter": []
        }
    }
    
    # Date range filter
    if request.start_date or request.end_date:
        date_range = {}
        if request.start_date:
            date_range["gte"] = request.start_date.isoformat()
        if request.end_date:
            date_range["lte"] = request.end_date.isoformat()
        
        query["bool"]["filter"].append({
            "range": {"publication_date": date_range}
        })
    
    # Sentiment filter
    if request.sentiment:
        query["bool"]["filter"].append({
            "term": {"sentiment_label": request.sentiment}
        })
    
    # Topic filter
    if request.topic:
        query["bool"]["filter"].append({
            "term": {"topic_label": request.topic}
        })
    
    # Execute search
    result = es.search(
        index=settings.ES_INDEX,
        body={
            "query": query,
            "from": request.offset,
            "size": request.limit,
            "highlight": {
                "fields": {
                    "headline": {},
                    "content": {"fragment_size": 150, "number_of_fragments": 3}
                }
            }
        }
    )
    
    # Format results
    articles = []
    for hit in result['hits']['hits']:
        article = hit['_source']
        article['id'] = hit['_id']
        article['highlights'] = hit.get('highlight', {})
        articles.append(article)
    
    return {
        "total": result['hits']['total']['value'],
        "articles": articles,
        "query": request.query
    }


@app.post("/api/search/entity")
async def search_entity(request: EntitySearchRequest):
    """
    Search articles by entity name
    
    Finds all articles mentioning a specific entity (person, organization, location)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = """
            SELECT DISTINCT
                a.id,
                a.headline,
                a.content,
                a.sentiment_score,
                a.sentiment_label,
                a.topic_label,
                n.publication_date,
                n.page_number,
                n.section,
                array_agg(DISTINCT jsonb_build_object(
                    'text', e.entity_text,
                    'type', e.entity_type
                )) as entities
            FROM articles a
            JOIN newspapers n ON a.newspaper_id = n.id
            JOIN entities e ON e.article_id = a.id
            WHERE e.entity_text ILIKE %s
        """
        params = [f"%{request.entity_name}%"]
        
        if request.entity_type:
            query += " AND e.entity_type = %s"
            params.append(request.entity_type)
        
        if request.start_date:
            query += " AND n.publication_date >= %s"
            params.append(request.start_date)
        
        if request.end_date:
            query += " AND n.publication_date <= %s"
            params.append(request.end_date)
        
        query += """
            GROUP BY a.id, a.headline, a.content, a.sentiment_score, 
                     a.sentiment_label, a.topic_label, n.publication_date, 
                     n.page_number, n.section
            ORDER BY n.publication_date DESC
            LIMIT %s
        """
        params.append(request.limit)
        
        cur.execute(query, params)
        articles = cur.fetchall()
        
        return {
            "total": len(articles),
            "entity": request.entity_name,
            "articles": articles
        }
    
    finally:
        cur.close()
        conn.close()


@app.get("/api/search/topics")
async def get_topics():
    """Get all available topics"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT topic_id, topic_name, keywords, article_count
            FROM topics
            ORDER BY article_count DESC
        """)
        topics = cur.fetchall()
        return {"topics": topics}
    
    finally:
        cur.close()
        conn.close()


# ============================================
# ANALYTICS ENDPOINTS
# ============================================

@app.post("/api/analytics/keyword-trend")
async def get_keyword_trend(request: TrendRequest):
    """
    Get keyword frequency trends over time
    
    Returns time-series data showing how often keywords appear
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        trends = {}
        
        for keyword in request.keywords:
            # Use database function
            cur.execute("""
                SELECT * FROM get_keyword_frequency(%s, %s, %s)
            """, (keyword, request.start_date, request.end_date))
            
            data = cur.fetchall()
            trends[keyword] = [
                {
                    "date": str(row['publication_date']),
                    "count": row['mention_count']
                }
                for row in data
            ]
        
        return {
            "start_date": str(request.start_date),
            "end_date": str(request.end_date),
            "trends": trends
        }
    
    finally:
        cur.close()
        conn.close()


@app.post("/api/analytics/entity-trend")
async def get_entity_trend(
    entity_name: str,
    entity_type: Optional[str] = None,
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    """
    Get entity mention trends over time with sentiment
    
    Shows how often an entity is mentioned and the average sentiment
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT * FROM get_entity_trends(%s, %s, %s, %s)
        """, (entity_name, entity_type, start_date, end_date))
        
        data = cur.fetchall()
        
        trend = [
            {
                "date": str(row['publication_date']),
                "mentions": row['mention_count'],
                "avg_sentiment": float(row['avg_sentiment']) if row['avg_sentiment'] else 0
            }
            for row in data
        ]
        
        return {
            "entity": entity_name,
            "type": entity_type,
            "trend": trend
        }
    
    finally:
        cur.close()
        conn.close()


@app.post("/api/analytics/topic-distribution")
async def get_topic_distribution(request: TopicDistributionRequest):
    """
    Get topic distribution for a time period
    
    Shows what topics were most discussed during a specific period
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT * FROM get_topic_distribution(%s, %s)
        """, (request.start_date, request.end_date))
        
        data = cur.fetchall()
        
        distribution = [
            {
                "topic_id": row['topic_id'],
                "topic_name": row['topic_name'],
                "article_count": row['article_count'],
                "percentage": round(float(row['percentage']), 2)
            }
            for row in data
        ]
        
        return {
            "start_date": str(request.start_date),
            "end_date": str(request.end_date),
            "distribution": distribution
        }
    
    finally:
        cur.close()
        conn.close()


@app.get("/api/analytics/sentiment-overview")
async def get_sentiment_overview(
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    """
    Get sentiment distribution overview
    
    Shows breakdown of positive/neutral/negative articles
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT 
                a.sentiment_label,
                COUNT(*) as count,
                AVG(a.sentiment_score) as avg_score
            FROM articles a
            JOIN newspapers n ON a.newspaper_id = n.id
            WHERE n.publication_date BETWEEN %s AND %s
            GROUP BY a.sentiment_label
        """, (start_date, end_date))
        
        data = cur.fetchall()
        
        total = sum(row['count'] for row in data)
        
        sentiment_breakdown = [
            {
                "label": row['sentiment_label'],
                "count": row['count'],
                "percentage": round((row['count'] / total * 100), 2) if total > 0 else 0,
                "avg_score": round(float(row['avg_score']), 3)
            }
            for row in data
        ]
        
        return {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_articles": total,
            "sentiment_breakdown": sentiment_breakdown
        }
    
    finally:
        cur.close()
        conn.close()


@app.get("/api/analytics/top-entities")
async def get_top_entities(
    entity_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get most mentioned entities
    
    Returns top entities by mention count
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = """
            SELECT 
                e.entity_text,
                e.entity_type,
                COUNT(*) as mention_count,
                COUNT(DISTINCT a.newspaper_id) as newspaper_count,
                AVG(a.sentiment_score) as avg_sentiment
            FROM entities e
            JOIN articles a ON e.article_id = a.id
            JOIN newspapers n ON a.newspaper_id = n.id
            WHERE 1=1
        """
        params = []
        
        if entity_type:
            query += " AND e.entity_type = %s"
            params.append(entity_type)
        
        if start_date:
            query += " AND n.publication_date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND n.publication_date <= %s"
            params.append(end_date)
        
        query += """
            GROUP BY e.entity_text, e.entity_type
            ORDER BY mention_count DESC
            LIMIT %s
        """
        params.append(limit)
        
        cur.execute(query, params)
        entities = cur.fetchall()
        
        return {
            "entities": [
                {
                    "text": row['entity_text'],
                    "type": row['entity_type'],
                    "mentions": row['mention_count'],
                    "newspapers": row['newspaper_count'],
                    "avg_sentiment": round(float(row['avg_sentiment']), 3) if row['avg_sentiment'] else 0
                }
                for row in entities
            ]
        }
    
    finally:
        cur.close()
        conn.close()


# ============================================
# ARTICLE ENDPOINTS
# ============================================

@app.get("/api/articles/{article_id}")
async def get_article(article_id: str):
    """Get single article by ID"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT 
                a.*,
                n.publication_date,
                n.page_number,
                n.section,
                n.image_path,
                t.topic_name,
                t.keywords as topic_keywords,
                array_agg(jsonb_build_object(
                    'text', e.entity_text,
                    'type', e.entity_type
                )) as entities
            FROM articles a
            JOIN newspapers n ON a.newspaper_id = n.id
            LEFT JOIN topics t ON a.topic_id = t.topic_id
            LEFT JOIN entities e ON e.article_id = a.id
            WHERE a.id = %s
            GROUP BY a.id, n.publication_date, n.page_number, n.section, 
                     n.image_path, t.topic_name, t.keywords
        """, (article_id,))
        
        article = cur.fetchone()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return article
    
    finally:
        cur.close()
        conn.close()


@app.get("/api/articles")
async def list_articles(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    topic_id: Optional[int] = None,
    sentiment: Optional[str] = None,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List articles with filters"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = """
            SELECT 
                a.id,
                a.headline,
                LEFT(a.content, 200) as content_preview,
                a.sentiment_score,
                a.sentiment_label,
                a.topic_label,
                n.publication_date,
                n.page_number
            FROM articles a
            JOIN newspapers n ON a.newspaper_id = n.id
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND n.publication_date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND n.publication_date <= %s"
            params.append(end_date)
        
        if topic_id is not None:
            query += " AND a.topic_id = %s"
            params.append(topic_id)
        
        if sentiment:
            query += " AND a.sentiment_label = %s"
            params.append(sentiment)
        
        query += " ORDER BY n.publication_date DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cur.execute(query, params)
        articles = cur.fetchall()
        
        return {"articles": articles}
    
    finally:
        cur.close()
        conn.close()


# ============================================
# HEALTH CHECK
# ============================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MediaScope API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
@app.get("/api/articles/{article_id}")
def get_article_detail(article_id: str):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                a.id,
                a.headline,
                a.content,
                a.word_count,
                a.sentiment_score,
                a.sentiment_label,
                a.topic_label,
                a.created_at as publication_date,
                1 as page_number,
                COALESCE(
                    json_agg(
                        json_build_object('text', e.text, 'type', e.entity_type)
                    ) FILTER (WHERE e.id IS NOT NULL),
                    '[]'
                ) as entities
            FROM articles a
            LEFT JOIN entities e ON a.id = e.article_id
            WHERE a.id = %s
            GROUP BY a.id, a.headline, a.content, a.word_count, 
                     a.sentiment_score, a.sentiment_label, a.topic_label, a.created_at
        """, (article_id,))
        
        article = cur.fetchone()
        cur.close()
        conn.close()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return {"article": dict(article)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/suggestions/keywords")
def get_keyword_suggestions(limit: int = 100):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                entity_text as keyword,
                entity_type as type,
                COUNT(*) as frequency
            FROM entities
            GROUP BY entity_text, entity_type
            ORDER BY frequency DESC
            LIMIT %s
        """, (limit,))
        
        suggestions = cur.fetchall()
        cur.close()
        conn.close()
        
        return {"suggestions": [dict(s) for s in suggestions]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analytics/ai-summary")
def generate_ai_summary(request: dict):
    try:
        start_date = request.get('start_date', '1990-01-01')
        end_date = request.get('end_date', '1992-12-31')
        topic = request.get('topic', None)
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT headline, LEFT(content, 500) as excerpt, 
                   sentiment_label, topic_label
            FROM articles 
            WHERE created_at::date BETWEEN %s AND %s
        """
        params = [start_date, end_date]
        
        if topic:
            query += " AND topic_label = %s"
            params.append(topic)
        
        query += " ORDER BY created_at LIMIT 50"
        
        cur.execute(query, params)
        articles = cur.fetchall()
        cur.close()
        conn.close()
        
        articles_text = "\n\n".join([
            f"Headline: {a['headline']}\nExcerpt: {a['excerpt']}\nSentiment: {a['sentiment_label']}"
            for a in articles
        ])
        
        prompt = f"""Analyze these news articles from Dawn newspaper ({start_date} to {end_date}) and provide:
1. Main themes and topics covered
2. Overall sentiment and tone
3. Key events or trends
4. Notable patterns or insights

Articles:
{articles_text}

Provide a concise 200-word summary."""
        
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-3-pro-preview')
        response = model.generate_content(prompt)
        
        return {
            "summary": response.text,
            "article_count": len(articles),
            "date_range": f"{start_date} to {end_date}",
            "topic": topic
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/articles/{article_id}")
def get_article_detail(article_id: str):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                a.id,
                a.headline,
                a.content,
                a.word_count,
                a.sentiment_score,
                a.sentiment_label,
                a.topic_label,
                a.created_at as publication_date,
                1 as page_number,
                COALESCE(
                    json_agg(
                        json_build_object('text', e.text, 'type', e.entity_type)
                    ) FILTER (WHERE e.id IS NOT NULL),
                    '[]'
                ) as entities
            FROM articles a
            LEFT JOIN entities e ON a.id = e.article_id
            WHERE a.id = %s
            GROUP BY a.id, a.headline, a.content, a.word_count, 
                     a.sentiment_score, a.sentiment_label, a.topic_label, a.created_at
        """, (article_id,))
        
        article = cur.fetchone()
        cur.close()
        conn.close()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return {"article": dict(article)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/suggestions/keywords")
def get_keyword_suggestions(limit: int = 100):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                entity_text as keyword,
                entity_type as type,
                COUNT(*) as frequency
            FROM entities
            GROUP BY entity_text, entity_type
            ORDER BY frequency DESC
            LIMIT %s
        """, (limit,))
        
        suggestions = cur.fetchall()
        cur.close()
        conn.close()
        
        return {"suggestions": [dict(s) for s in suggestions]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analytics/ai-summary")
def generate_ai_summary(request: dict):
    try:
        start_date = request.get('start_date', '1990-01-01')
        end_date = request.get('end_date', '1992-12-31')
        topic = request.get('topic', None)
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT headline, LEFT(content, 500) as excerpt, 
                   sentiment_label, topic_label
            FROM articles 
            WHERE created_at::date BETWEEN %s AND %s
        """
        params = [start_date, end_date]
        
        if topic:
            query += " AND topic_label = %s"
            params.append(topic)
        
        query += " ORDER BY created_at LIMIT 50"
        
        cur.execute(query, params)
        articles = cur.fetchall()
        cur.close()
        conn.close()
        
        articles_text = "\n\n".join([
            f"Headline: {a['headline']}\nExcerpt: {a['excerpt']}\nSentiment: {a['sentiment_label']}"
            for a in articles
        ])
        
        prompt = f"""Analyze these news articles from Dawn newspaper ({start_date} to {end_date}) and provide:
1. Main themes and topics covered
2. Overall sentiment and tone
3. Key events or trends
4. Notable patterns or insights

Articles:
{articles_text}

Provide a concise 200-word summary."""
        
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-3-pro-preview')
        response = model.generate_content(prompt)
        
        return {
            "summary": response.text,
            "article_count": len(articles),
            "date_range": f"{start_date} to {end_date}",
            "topic": topic
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/keyword-trend-fixed")
def get_keyword_trend_fixed():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count
            FROM articles
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        return {"trends": {"articles": [{"date": str(r['date']), "count": r['count']} for r in results]}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/sentiment-fixed")
def get_sentiment_fixed():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                sentiment_label,
                COUNT(*) as count
            FROM articles
            WHERE sentiment_label IS NOT NULL
            GROUP BY sentiment_label
        """)
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        sentiment_data = {"positive": 0, "neutral": 0, "negative": 0, "total": 0}
        for r in results:
            sentiment_data[r['sentiment_label']] = r['count']
            sentiment_data['total'] += r['count']
        
        return sentiment_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/top-entities-fixed")
def get_top_entities_fixed(entity_type: str = None, limit: int = 10):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                entity_text as text,
                entity_type as type,
                COUNT(*) as count
            FROM entities
        """
        
        params = []
        if entity_type:
            query += " WHERE entity_type = %s"
            params.append(entity_type)
        
        query += " GROUP BY entity_text, entity_type ORDER BY count DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        return {"entities": [dict(r) for r in results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-3-pro-preview')
        response = model.generate_content(prompt)
        
        return {
            "summary": response.text,
            "article_count": len(articles),
            "date_range": f"{start_date} to {end_date}",
            "topic": topic
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/sentiment-fixed")
def get_sentiment_fixed():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                sentiment_label,
                COUNT(*) as count
            FROM articles
            WHERE sentiment_label IS NOT NULL
            GROUP BY sentiment_label
        """)
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        sentiment_data = {"positive": 0, "neutral": 0, "negative": 0, "total": 0}
        for r in results:
            sentiment_data[r['sentiment_label']] = r['count']
            sentiment_data['total'] += r['count']
        
        return sentiment_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/top-entities-fixed")
def get_top_entities_fixed(entity_type: str = None, limit: int = 10):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                entity_text as text,
                entity_type as type,
                COUNT(*) as count
            FROM entities
        """
        
        params = []
        if entity_type:
            query += " WHERE entity_type = %s"
            params.append(entity_type)
        
        query += " GROUP BY entity_text, entity_type ORDER BY count DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        return {"entities": [dict(r) for r in results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
