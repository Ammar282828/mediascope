#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
from contextlib import contextmanager
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime
import base64
import re
from pathlib import Path
import google.generativeai as genai

# Import Firebase Firestore database layer
from firestore_db import get_db as get_firestore_db

# Pipeline will be imported lazily to avoid dependency issues on startup
PIPELINE_AVAILABLE = False
pipeline = None

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI(title="MediaScope API", version="2.0")

# Secure CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # Allow all headers for file uploads
    allow_credentials=True,
    max_age=3600
)

# Mount static files for newspaper images
app.mount("/input_newspapers", StaticFiles(directory="input_newspapers"), name="newspapers")

# Lazy initialization of OCR pipeline
def _init_pipeline():
    """Initialize pipeline on first use to avoid import errors on startup"""
    global pipeline, PIPELINE_AVAILABLE

    if pipeline is not None:
        return pipeline

    try:
        from mediascope_complete_pipeline import MediaScopePipeline, Config
        config = Config()
        pipeline = MediaScopePipeline(config)
        pipeline.initialize()
        PIPELINE_AVAILABLE = True
        print("[OK] MediaScope OCR Pipeline initialized")
        return pipeline
    except Exception as e:
        print(f"[WARNING] Pipeline initialization failed: {e}")
        print(f"   OCR features will be unavailable. Install missing dependencies with: pip install spacy transformers bertopic")
        PIPELINE_AVAILABLE = False
        return None

def get_db():
    """Get Firestore database instance"""
    return get_firestore_db()

@contextmanager
def get_db_cursor():
    """Context manager for database operations (Firestore compatibility layer)"""
    # For Firestore, we don't need cursors, but keep this for compatibility
    db = get_db()
    try:
        yield db
    except Exception as e:
        raise
    finally:
        pass  # Firestore doesn't need explicit connection closing

def filter_and_normalize_entities(entities):
    """Filter out noise entities and normalize similar ones"""
    if not entities or entities == '[]':
        return []

    # Common words and patterns to filter out
    NOISE_WORDS = {
        'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
        'first', 'second', 'third', 'last', 'next', 'today', 'yesterday', 'tomorrow',
        'this', 'that', 'these', 'those', 'the', 'a', 'an', 'and', 'or', 'but',
        'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
        'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
    }

    filtered = []
    seen_normalized = {}

    for entity in entities:
        text = entity.get('text', '').strip()
        entity_type = entity.get('type', '')

        # Skip empty or very short entities
        if not text or len(text) < 2:
            continue

        # Skip pure numbers
        if text.isdigit():
            continue

        # Skip noise words
        if text.lower() in NOISE_WORDS:
            continue

        # Skip entities that are just punctuation or special chars
        if not any(c.isalnum() for c in text):
            continue

        # Skip noisy entity types
        if entity_type in ['DATE', 'TIME', 'CARDINAL', 'ORDINAL', 'MONEY', 'PERCENT', 'QUANTITY']:
            continue

        # Normalize: lowercase for comparison, handle plurals
        normalized = text.lower().rstrip('s')  # Simple plural handling

        # Deduplicate based on normalized form
        if normalized in seen_normalized:
            # Keep the longer/capitalized version
            existing = seen_normalized[normalized]
            if len(text) > len(existing['text']):
                seen_normalized[normalized] = entity
        else:
            seen_normalized[normalized] = entity

    return list(seen_normalized.values())

def extract_date_from_image(image_path: str) -> Optional[str]:
    """Extract publication date from newspaper image using OCR"""
    try:
        # Try to use pytesseract if available
        try:
            import pytesseract
            from PIL import Image

            # Open image and extract text from top portion (where date usually is)
            img = Image.open(image_path)
            width, height = img.size
            # Crop top 20% of image where masthead/date typically appears
            top_section = img.crop((0, 0, width, int(height * 0.2)))

            # Extract text
            text = pytesseract.image_to_string(top_section)

            # Look for date patterns (e.g., "May 15, 1990", "15-05-1990", etc.)
            date_patterns = [
                r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',  # DD-MM-YYYY or MM-DD-YYYY
                r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',  # YYYY-MM-DD
                r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',  # Month DD, YYYY
                r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',  # DD Month YYYY
            ]

            for pattern in date_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    date_str = match.group(1)
                    # Try to parse and normalize to YYYY-MM-DD
                    try:
                        from dateutil import parser
                        parsed_date = parser.parse(date_str, fuzzy=True)
                        # Ensure date is in valid range (1990-1992)
                        if 1990 <= parsed_date.year <= 1992:
                            return parsed_date.strftime('%Y-%m-%d')
                    except:
                        continue
        except ImportError:
            # pytesseract not available
            pass

        return None
    except Exception as e:
        print(f"Date extraction error: {e}")
        return None

@app.get("/api/articles")
def list_articles(limit: int = 100, offset: int = 0):
    """List articles with proper connection management"""
    try:
        db = get_db()
        # Get articles from Firestore
        articles_ref = db.db.collection('articles').order_by('publication_date', direction='DESCENDING').limit(limit + offset)
        articles_docs = list(articles_ref.stream())

        # Apply offset manually (Firestore doesn't have native offset)
        articles_docs = articles_docs[offset:offset + limit]

        articles = []
        for doc in articles_docs:
            data = doc.to_dict()
            # Add content preview
            data['content_preview'] = data.get('content', '')[:200]
            articles.append(data)

        return {"articles": articles}
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/api/articles/{article_id}")
def get_article(article_id: str):
    """Get single article by ID"""
    try:
        db = get_db()
        article = db.get_article(article_id)
        if not article:
            raise HTTPException(404, "Article not found")
        return article
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/api/analytics/articles-over-time")
def articles_over_time():
    """Get article count over time with proper error handling"""
    try:
        db = get_db()
        timeline = db.get_analytics_articles_over_time()
        return {"timeline": timeline}
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/api/analytics/sentiment-over-time")
def sentiment_over_time():
    """Get sentiment distribution over time with proper error handling"""
    try:
        db = get_db()
        timeline = db.get_analytics_sentiment_over_time()
        return {"timeline": timeline}
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/api/analytics/top-keywords")
def top_keywords(limit: int = 30):
    """Get top keywords with proper error handling"""
    limit = min(limit, 100)  # Cap at 100
    try:
        db = get_db()
        keywords = db.get_top_keywords(limit=limit)
        return {"keywords": keywords}
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/api/suggestions/keywords")
def keyword_suggestions(limit: int = 100):
    """Get keyword suggestions with proper error handling"""
    limit = min(limit, 200)  # Cap at 200
    try:
        db = get_db()
        keywords = db.get_top_keywords(limit=limit)
        return {"suggestions": keywords}
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/api/analytics/top-entities-fixed")
def top_entities(entity_type: Optional[str] = None, limit: int = 15):
    """Get top entities with proper error handling"""
    limit = min(limit, 100)  # Cap at 100
    try:
        with get_db_cursor() as cur:
            if entity_type:
                cur.execute("""
                    SELECT entity_text as text, entity_type as type, COUNT(*) as count FROM entities
                    WHERE entity_type = %s GROUP BY entity_text, entity_type ORDER BY count DESC LIMIT %s
                """, (entity_type, limit))
            else:
                cur.execute("""
                    SELECT entity_text as text, entity_type as type, COUNT(*) as count FROM entities
                    GROUP BY entity_text, entity_type ORDER BY count DESC LIMIT %s
                """, (limit,))
            entities = [dict(r) for r in cur.fetchall()]
            return {"entities": entities}
    except psycopg2.Error as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/api/analytics/sentiment-fixed")
def sentiment_overview():
    """Get sentiment overview with proper error handling"""
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT sentiment_label, COUNT(*) as count FROM articles
                WHERE sentiment_label IS NOT NULL GROUP BY sentiment_label
            """)
            data = {"positive": 0, "neutral": 0, "negative": 0, "total": 0}
            for r in cur.fetchall():
                data[r['sentiment_label']] = r['count']
                data['total'] += r['count']
            return data
    except psycopg2.Error as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.post("/api/analytics/keyword-trend")
def keyword_trend(request: dict):
    """Get keyword trends over time with proper validation and error handling"""
    keywords = request.get('keywords', [])
    start_date = request.get('start_date')
    end_date = request.get('end_date')

    if not keywords or not isinstance(keywords, list):
        raise HTTPException(400, "Keywords must be a non-empty list")

    if not start_date or not end_date:
        raise HTTPException(400, "start_date and end_date are required")

    try:
        with get_db_cursor() as cur:
            trends = {}
            for keyword in keywords[:5]:  # Limit to 5 keywords
                cur.execute("""
                    SELECT n.publication_date as date, COUNT(*) as count
                    FROM articles a
                    JOIN newspapers n ON a.newspaper_id = n.id
                    JOIN entities e ON a.id = e.article_id
                    WHERE e.entity_text ILIKE %s AND n.publication_date BETWEEN %s AND %s
                    GROUP BY n.publication_date ORDER BY date
                """, (f'%{keyword}%', start_date, end_date))
                trends[keyword] = [{"date": str(r['date']), "count": r['count']} for r in cur.fetchall()]
            return {"trends": trends}
    except psycopg2.Error as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.post("/api/search/keyword")
def search_keyword(request: dict):
    """Search articles by keyword with validation, sorting, and error handling"""
    keyword = request.get('keyword') or request.get('query', '')
    limit = min(request.get('limit', 100), 1000)  # Cap at 1000
    offset = max(request.get('offset', 0), 0)  # Must be >= 0
    sort_by = request.get('sort_by', 'date')  # date, sentiment, frequency, relevance

    if not keyword or len(keyword) < 1:
        raise HTTPException(400, "Keyword is required and must be at least 1 character")

    if len(keyword) > 200:
        raise HTTPException(400, "Keyword must be less than 200 characters")

    try:
        db = get_db()
        articles = db.search_articles(keyword, limit=limit)

        # Apply offset manually
        total = len(articles)
        articles = articles[offset:offset + limit]

        # Add content preview and filter entities
        articles_list = []
        for article in articles:
            article['content_preview'] = article.get('content', '')[:200]
            article['entities'] = filter_and_normalize_entities(article.get('entities', []))
            articles_list.append(article)

        # Sort based on sort_by parameter
        if sort_by == 'date':
            articles_list.sort(key=lambda x: x.get('publication_date', ''), reverse=True)
        elif sort_by == 'date_asc':
            articles_list.sort(key=lambda x: x.get('publication_date', ''))
        elif sort_by == 'sentiment':
            articles_list.sort(key=lambda x: x.get('sentiment_score', 0), reverse=True)
        elif sort_by == 'sentiment_asc':
            articles_list.sort(key=lambda x: x.get('sentiment_score', 0))

        return {
            "articles": articles_list,
            "total": total,
            "keyword": keyword,
            "sort_by": sort_by
        }
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.post("/api/search/entity")
def search_entity(request: dict):
    """Search articles by entity name"""
    entity_name = request.get('entity_name', '') or request.get('query', '')
    limit = min(request.get('limit', 100), 1000)
    offset = max(request.get('offset', 0), 0)

    if not entity_name or len(entity_name) < 1:
        raise HTTPException(400, "Entity name is required")

    try:
        db = get_db()
        articles = db.search_by_entity(entity_name, limit=limit)

        # Apply offset
        total = len(articles)
        articles = articles[offset:offset + limit]

        # Add content preview and filter entities
        articles_list = []
        for article in articles:
            article['content_preview'] = article.get('content', '')[:200]
            article['entities'] = filter_and_normalize_entities(article.get('entities', []))
            articles_list.append(article)

        return {
            "articles": articles_list,
            "total": total,
            "entity_name": entity_name
        }
    except psycopg2.Error as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.post("/api/ocr/upload")
async def upload_newspaper_for_ocr(file: UploadFile = File(...)):
    """Upload newspaper image for OCR processing with automatic date extraction"""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")

        # Create uploads directory if it doesn't exist
        upload_dir = "uploads/newspapers"
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        file_path = f"{upload_dir}/{file_id}.{file_ext}"

        # Save file
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        # Attempt to extract date from image
        extracted_date = extract_date_from_image(file_path)

        # Return file info
        return {
            "file_id": file_id,
            "filename": file.filename,
            "path": file_path,
            "size": len(contents),
            "extracted_date": extracted_date,
            "status": "uploaded",
            "message": f"File uploaded successfully. {'Date auto-detected: ' + extracted_date if extracted_date else 'No date detected - you can set it manually.'}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Upload error: {str(e)}")

@app.post("/api/ocr/upload-bulk")
async def upload_bulk_newspapers(files: List[UploadFile] = File(...)):
    """Upload multiple newspaper images for batch OCR processing"""
    try:
        if not files:
            raise HTTPException(400, "No files provided")

        # Create uploads directory
        upload_dir = "uploads/newspapers"
        os.makedirs(upload_dir, exist_ok=True)

        results = []
        for file in files:
            try:
                # Validate file type
                if not file.content_type or not file.content_type.startswith('image/'):
                    results.append({
                        "filename": file.filename,
                        "status": "error",
                        "message": "Not an image file"
                    })
                    continue

                # Generate unique filename
                file_id = str(uuid.uuid4())
                file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
                file_path = f"{upload_dir}/{file_id}.{file_ext}"

                # Save file
                contents = await file.read()
                with open(file_path, "wb") as f:
                    f.write(contents)

                # Attempt to extract date
                extracted_date = extract_date_from_image(file_path)

                results.append({
                    "file_id": file_id,
                    "filename": file.filename,
                    "path": file_path,
                    "size": len(contents),
                    "extracted_date": extracted_date,
                    "status": "uploaded"
                })
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "message": str(e)
                })

        # Count successes
        successful = sum(1 for r in results if r.get("status") == "uploaded")

        return {
            "total_files": len(files),
            "successful": successful,
            "failed": len(files) - successful,
            "results": results,
            "message": f"Uploaded {successful} of {len(files)} files successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Bulk upload error: {str(e)}")

@app.post("/api/ocr/process-folder")
def process_local_folder(request: dict):
    """Process all newspaper images from a local folder without uploading"""
    folder_path = request.get('folder_path')

    if not folder_path:
        raise HTTPException(400, "folder_path is required")

    # Expand user path (~) and convert to absolute path
    folder_path = os.path.expanduser(folder_path)
    folder_path = os.path.abspath(folder_path)

    print(f"[DEBUG] Attempting to access folder: {folder_path}")

    if not os.path.exists(folder_path):
        raise HTTPException(404, f"Folder not found: {folder_path}. Please check the path and try again.")

    if not os.path.isdir(folder_path):
        raise HTTPException(400, f"Path is not a directory: {folder_path}")

    # Initialize pipeline if needed (lazy loading)
    active_pipeline = _init_pipeline()

    if not active_pipeline:
        raise HTTPException(503, "OCR pipeline not available. Missing dependencies (spaCy, transformers, etc.). Check server logs.")

    # Scan folder for image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.HEIC', '.JPG', '.JPEG', '.PNG'}
    image_files = []

    try:
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(filename)
                if ext in image_extensions:
                    image_files.append((filename, file_path))
    except Exception as e:
        raise HTTPException(500, f"Error reading folder: {str(e)}")

    if not image_files:
        raise HTTPException(400, f"No image files found in folder: {folder_path}")

    # Process each image
    results = []
    for idx, (filename, file_path) in enumerate(image_files, 1):
        try:
            print(f"\n[{idx}/{len(image_files)}] Processing: {filename}")

            # Extract date from image
            extracted_date = extract_date_from_image(file_path)

            # Parse the date if extracted
            parsed_date = None
            if extracted_date:
                try:
                    parsed_date = datetime.strptime(extracted_date, '%Y-%m-%d')
                except:
                    pass

            # Process the newspaper using the pipeline
            success = active_pipeline.process_single_newspaper(file_path, publication_date=parsed_date)

            results.append({
                "filename": filename,
                "path": file_path,
                "extracted_date": extracted_date,
                "status": "completed" if success else "failed",
                "message": "OCR processing completed successfully" if success else "OCR processing failed"
            })
            print(f"[OK] {filename}: {'Success' if success else 'Failed'}")
        except Exception as e:
            print(f"[ERROR] {filename}: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                "filename": filename,
                "path": file_path,
                "status": "error",
                "message": str(e)
            })

    # Count successes
    successful = sum(1 for r in results if r.get("status") == "completed")

    return {
        "folder_path": folder_path,
        "total_files": len(image_files),
        "successful": successful,
        "failed": len(image_files) - successful,
        "results": results,
        "message": f"Processed {successful} of {len(image_files)} files successfully"
    }

@app.post("/api/ocr/process")
def trigger_ocr_processing(request: dict):
    """Trigger OCR processing for uploaded newspaper using MediaScope pipeline"""
    file_id = request.get('file_id')
    file_path = request.get('file_path')  # Can be provided directly
    publication_date = request.get('publication_date')

    if not file_id and not file_path:
        raise HTTPException(400, "file_id or file_path is required")

    # Determine file path
    if not file_path:
        # Look for file in uploads directory
        upload_dir = "uploads/newspapers"
        # Try common image extensions
        for ext in ['jpg', 'jpeg', 'png', 'HEIC', 'heic']:
            potential_path = f"{upload_dir}/{file_id}.{ext}"
            if os.path.exists(potential_path):
                file_path = potential_path
                break

        if not file_path:
            raise HTTPException(404, f"File not found for file_id: {file_id}")

    # Initialize pipeline if needed (lazy loading)
    active_pipeline = _init_pipeline()

    if not active_pipeline:
        raise HTTPException(503, "OCR pipeline not available. Missing dependencies (spaCy, transformers, etc.). Check server logs.")

    # Parse publication date if provided
    parsed_date = None
    if publication_date:
        try:
            parsed_date = datetime.strptime(publication_date, '%Y-%m-%d')
        except:
            pass

    # Process the newspaper using the pipeline
    try:
        success = active_pipeline.process_single_newspaper(file_path, publication_date=parsed_date)

        if success:
            return {
                "file_id": file_id,
                "file_path": file_path,
                "status": "completed",
                "message": "OCR processing completed successfully. Articles extracted and stored in database."
            }
        else:
            return {
                "file_id": file_id,
                "file_path": file_path,
                "status": "failed",
                "message": "OCR processing failed. Check server logs for details."
            }
    except Exception as e:
        raise HTTPException(500, f"OCR processing error: {str(e)}")

@app.get("/api/ocr/status/{file_id}")
def get_ocr_status(file_id: str):
    """Get OCR processing status"""
    # This would check the actual processing status
    # For now, return a mock status
    return {
        "file_id": file_id,
        "status": "processing",
        "progress": 45,
        "message": "Extracting text from newspaper image..."
    }

@app.post("/api/ads/upload")
async def upload_ad_image(file: UploadFile = File(...), metadata: Optional[str] = None):
    """Upload advertisement image for analysis"""
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")

        # Create uploads directory
        upload_dir = "uploads/ads"
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        file_path = f"{upload_dir}/{file_id}.{file_ext}"

        # Save file
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        # Store in database
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    INSERT INTO ad_images (id, filename, file_path, upload_date, file_size)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (file_id, file.filename, file_path, datetime.now(), len(contents)))

                return {
                    "file_id": file_id,
                    "filename": file.filename,
                    "path": file_path,
                    "size": len(contents),
                    "status": "uploaded",
                    "message": "Advertisement uploaded successfully"
                }
        except psycopg2.Error:
            # If table doesn't exist, return without DB insert
            return {
                "file_id": file_id,
                "filename": file.filename,
                "path": file_path,
                "size": len(contents),
                "status": "uploaded",
                "message": "Advertisement uploaded (DB table not configured)"
            }
    except Exception as e:
        raise HTTPException(500, f"Upload error: {str(e)}")

@app.post("/api/ads/analyze")
def analyze_ad_image(request: dict):
    """Analyze uploaded advertisement image"""
    file_id = request.get('file_id')

    if not file_id:
        raise HTTPException(400, "file_id is required")

    # Mock analysis result (integrate with your AI analysis later)
    return {
        "file_id": file_id,
        "analysis": {
            "detected_text": "Sample ad text detected",
            "brands": ["Brand A", "Brand B"],
            "sentiment": "positive",
            "sentiment_score": 0.75,
            "categories": ["consumer goods", "lifestyle"],
            "colors": ["#FF5733", "#3498DB"],
            "dominant_emotion": "happy",
            "target_demographic": "adults 25-45"
        },
        "status": "completed"
    }

@app.get("/api/ads/list")
def list_ads(limit: int = 50, offset: int = 0):
    """List uploaded advertisements"""
    limit = min(limit, 200)
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT id, filename, upload_date, file_size, analysis_status
                FROM ad_images
                ORDER BY upload_date DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            ads = cur.fetchall()
            return {"ads": [dict(ad) for ad in ads]}
    except psycopg2.Error:
        # If table doesn't exist, return empty list
        return {"ads": [], "message": "Ad database table not configured"}

@app.get("/api/analytics/sentiment-by-entity")
def sentiment_by_entity(entity_type: Optional[str] = None, limit: int = 20):
    """Get sentiment breakdown for top entities"""
    limit = min(limit, 100)
    try:
        with get_db_cursor() as cur:
            query = """
                SELECT
                    e.entity_text,
                    e.entity_type,
                    COUNT(DISTINCT a.id) as article_count,
                    AVG(a.sentiment_score) as avg_sentiment,
                    SUM(CASE WHEN a.sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
                    SUM(CASE WHEN a.sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
                    SUM(CASE WHEN a.sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count
                FROM entities e
                JOIN articles a ON e.article_id = a.id
            """

            if entity_type:
                query += " WHERE e.entity_type = %s"
                params = (entity_type, limit)
            else:
                params = (limit,)

            query += """
                GROUP BY e.entity_text, e.entity_type
                HAVING COUNT(DISTINCT a.id) >= 5
                ORDER BY article_count DESC
                LIMIT %s
            """

            cur.execute(query, params)
            results = cur.fetchall()

            return {
                "entities": [dict(r) for r in results],
                "entity_type": entity_type
            }
    except psycopg2.Error as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/api/analytics/entity-cooccurrence")
def entity_cooccurrence(entity_type: Optional[str] = None, min_count: int = 3, limit: int = 50):
    """Get entity pairs that frequently appear together in articles"""
    limit = min(limit, 200)
    try:
        with get_db_cursor() as cur:
            query = """
                SELECT
                    e1.entity_text as entity1,
                    e1.entity_type as type1,
                    e2.entity_text as entity2,
                    e2.entity_type as type2,
                    COUNT(DISTINCT e1.article_id) as cooccurrence_count
                FROM entities e1
                JOIN entities e2 ON e1.article_id = e2.article_id AND e1.entity_text < e2.entity_text
            """

            params = []
            if entity_type:
                query += " WHERE e1.entity_type = %s AND e2.entity_type = %s"
                params = [entity_type, entity_type, min_count, limit]
            else:
                params = [min_count, limit]

            query += """
                GROUP BY e1.entity_text, e1.entity_type, e2.entity_text, e2.entity_type
                HAVING COUNT(DISTINCT e1.article_id) >= %s
                ORDER BY cooccurrence_count DESC
                LIMIT %s
            """

            cur.execute(query, params)
            results = cur.fetchall()

            return {
                "pairs": [dict(r) for r in results],
                "entity_type": entity_type,
                "min_count": min_count
            }
    except psycopg2.Error as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/api/newspapers")
def search_newspapers(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page_number: Optional[int] = None,
    limit: int = 50
):
    """Search newspapers by date and page number"""
    limit = min(limit, 200)
    try:
        with get_db_cursor() as cur:
            query = """
                SELECT
                    n.id,
                    n.publication_date,
                    n.page_number,
                    n.section,
                    n.image_path,
                    COUNT(a.id) as article_count,
                    AVG(a.sentiment_score) as avg_sentiment
                FROM newspapers n
                LEFT JOIN articles a ON n.id = a.newspaper_id
                WHERE 1=1
            """
            params = []

            if start_date:
                query += " AND n.publication_date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND n.publication_date <= %s"
                params.append(end_date)
            if page_number is not None:
                query += " AND n.page_number = %s"
                params.append(page_number)

            query += """
                GROUP BY n.id, n.publication_date, n.page_number, n.section, n.image_path
                ORDER BY n.publication_date DESC, n.page_number ASC
                LIMIT %s
            """
            params.append(limit)

            cur.execute(query, params)
            newspapers = cur.fetchall()

            return {
                "newspapers": [dict(n) for n in newspapers],
                "count": len(newspapers)
            }
    except psycopg2.Error as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/api/newspapers/{newspaper_id}")
def get_newspaper_page(newspaper_id: str):
    """Get newspaper page with all its articles"""
    try:
        with get_db_cursor() as cur:
            # Get newspaper info
            cur.execute("""
                SELECT id, publication_date, page_number, section, image_path
                FROM newspapers
                WHERE id = %s
            """, (newspaper_id,))

            newspaper = cur.fetchone()
            if not newspaper:
                raise HTTPException(404, "Newspaper page not found")

            # Get all articles from this page
            cur.execute("""
                SELECT
                    a.id,
                    a.article_number,
                    a.headline,
                    a.content,
                    a.word_count,
                    a.sentiment_score,
                    a.sentiment_label,
                    a.topic_label
                FROM articles a
                WHERE a.newspaper_id = %s
                ORDER BY a.article_number
            """, (newspaper_id,))

            articles = cur.fetchall()

            # Get entities for all articles
            cur.execute("""
                SELECT
                    e.article_id,
                    e.entity_text,
                    e.entity_type
                FROM entities e
                WHERE e.article_id IN (
                    SELECT id FROM articles WHERE newspaper_id = %s
                )
            """, (newspaper_id,))

            entities = cur.fetchall()

            return {
                "newspaper": dict(newspaper),
                "articles": [dict(a) for a in articles],
                "entities": [dict(e) for e in entities],
                "article_count": len(articles)
            }
    except psycopg2.Error as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.post("/api/newspapers/{newspaper_id}/summarize")
def summarize_newspaper_page(newspaper_id: str):
    """Generate AI summary for an entire newspaper page"""
    try:
        with get_db_cursor() as cur:
            # Get newspaper info
            cur.execute("""
                SELECT publication_date, page_number, section
                FROM newspapers
                WHERE id = %s
            """, (newspaper_id,))

            newspaper = cur.fetchone()
            if not newspaper:
                raise HTTPException(404, "Newspaper page not found")

            # Get all articles from this page
            cur.execute("""
                SELECT headline, content
                FROM articles
                WHERE newspaper_id = %s
                ORDER BY article_number
            """, (newspaper_id,))

            articles = cur.fetchall()

            if not articles:
                return {
                    "error": "No articles found for this newspaper page"
                }

            # Prepare content for summarization
            page_content = f"Newspaper: Dawn, Date: {newspaper['publication_date']}, Page: {newspaper['page_number']}\n\n"
            for article in articles:
                page_content += f"Headline: {article['headline']}\n{article['content'][:500]}\n\n"

            # Generate summary using Gemini
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                raise HTTPException(500, "GEMINI_API_KEY not configured")

            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-pro')

            prompt = f"""Provide a comprehensive summary of this newspaper page from {newspaper['publication_date']}.
Include the main topics covered, key events, and important details mentioned across all articles.

{page_content[:5000]}

Summary:"""

            response = model.generate_content(prompt)

            return {
                "newspaper_id": newspaper_id,
                "publication_date": str(newspaper['publication_date']),
                "page_number": newspaper['page_number'],
                "article_count": len(articles),
                "summary": response.text
            }

    except Exception as e:
        print(f"Error generating summary: {e}")
        return {"error": f"Failed to generate summary: {str(e)}"}

@app.get("/api/articles/{article_id}/related")
def get_related_articles(article_id: str, limit: int = 10):
    """Get articles from the same newspaper"""
    limit = min(limit, 50)
    try:
        with get_db_cursor() as cur:
            # First get the newspaper_id of the current article
            cur.execute("""
                SELECT newspaper_id FROM articles WHERE id = %s
            """, (article_id,))

            result = cur.fetchone()
            if not result:
                raise HTTPException(404, "Article not found")

            newspaper_id = result['newspaper_id']

            # Get other articles from same newspaper
            cur.execute("""
                SELECT a.id, a.headline, a.sentiment_label, a.sentiment_score,
                       LEFT(a.content, 150) as content_preview
                FROM articles a
                WHERE a.newspaper_id = %s AND a.id != %s
                ORDER BY a.id
                LIMIT %s
            """, (newspaper_id, article_id, limit))

            articles = cur.fetchall()

            return {
                "related_articles": [dict(a) for a in articles],
                "newspaper_id": newspaper_id,
                "count": len(articles)
            }
    except psycopg2.Error as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/api/articles/{article_id}/full")
def get_article_full(article_id: str):
    """Get complete article details including newspaper image"""
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT
                    a.id, a.headline, a.content, a.sentiment_score, a.sentiment_label,
                    a.topic_label, a.word_count, a.created_at,
                    n.id as newspaper_id, n.publication_date, n.image_path,
                    n.page_number, n.section,
                    COALESCE(json_agg(
                        json_build_object(
                            'text', e.entity_text,
                            'type', e.entity_type,
                            'start_char', e.start_char,
                            'end_char', e.end_char
                        )
                    ) FILTER (WHERE e.id IS NOT NULL), '[]') as entities
                FROM articles a
                LEFT JOIN newspapers n ON a.newspaper_id = n.id
                LEFT JOIN entities e ON a.id = e.article_id
                WHERE a.id = %s
                GROUP BY a.id, a.headline, a.content, a.sentiment_score, a.sentiment_label,
                         a.topic_label, a.word_count, a.created_at,
                         n.id, n.publication_date, n.image_path, n.page_number, n.section
            """, (article_id,))

            article = cur.fetchone()

            if not article:
                raise HTTPException(404, "Article not found")

            # Filter and normalize entities
            article_dict = dict(article)
            article_dict['entities'] = filter_and_normalize_entities(article_dict.get('entities', []))

            return {"article": article_dict}
    except psycopg2.Error as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.post("/api/articles/{article_id}/summary")
def generate_article_summary(article_id: str):
    """Generate AI summary for a specific article using Gemini"""
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT headline, content FROM articles WHERE id = %s
            """, (article_id,))

            article = cur.fetchone()

            if not article:
                raise HTTPException(404, "Article not found")

            # Generate summary using Gemini API
            if not GEMINI_API_KEY:
                raise HTTPException(500, "Gemini API key not configured")

            try:
                # Use Gemini 2.0 Flash (latest preview model)
                model = genai.GenerativeModel('gemini-2.0-flash-exp')

                prompt = f"""You are analyzing a historical newspaper article from 1990-1992.

Article Headline: {article['headline']}

Article Content:
{article['content']}

Please provide a concise, professional summary (3-5 sentences) covering:
1. Main topic and key events
2. Key people, organizations, or locations mentioned
3. Historical significance or context
4. Overall tone and perspective

Summary:"""

                response = model.generate_content(prompt)
                summary = response.text.strip()

            except Exception as e:
                # Fallback if Gemini fails
                summary = f"AI Summary temporarily unavailable. Article discusses: {article['headline']}"
                print(f"Gemini API error: {str(e)}")

            return {
                "article_id": article_id,
                "summary": summary,
                "headline": article['headline']
            }
    except psycopg2.Error as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.post("/api/analytics/ai-summary")
def generate_date_range_summary(request: dict):
    """Generate AI-powered summary for articles in a date range using Gemini"""
    start_date = request.get('start_date', '1990-01-01')
    end_date = request.get('end_date', '1992-12-31')
    topic = request.get('topic')

    try:
        with get_db_cursor() as cur:
            # Get articles from date range
            query = """
                SELECT a.headline, a.content, a.sentiment_label, a.topic_label,
                       n.publication_date,
                       COALESCE(json_agg(DISTINCT e.entity_text) FILTER (WHERE e.entity_type IN ('PERSON', 'ORG', 'GPE')), '[]') as key_entities
                FROM articles a
                LEFT JOIN newspapers n ON a.newspaper_id = n.id
                LEFT JOIN entities e ON a.id = e.article_id
                WHERE n.publication_date BETWEEN %s AND %s
            """

            params = [start_date, end_date]

            if topic:
                query += " AND a.topic_label ILIKE %s"
                params.append(f'%{topic}%')

            query += """
                GROUP BY a.id, a.headline, a.content, a.sentiment_label, a.topic_label, n.publication_date
                ORDER BY n.publication_date DESC
                LIMIT 100
            """

            cur.execute(query, params)
            articles = cur.fetchall()

            if not articles:
                return {
                    "error": "No articles found in this date range",
                    "date_range": f"{start_date} to {end_date}",
                    "article_count": 0
                }

            # Generate summary using Gemini
            if not GEMINI_API_KEY:
                raise HTTPException(500, "Gemini API key not configured")

            try:
                # Use Gemini 2.0 Flash Experimental (latest preview)
                model = genai.GenerativeModel('gemini-2.0-flash-exp')

                # Prepare data for summarization
                article_count = len(articles)

                # Get top entities
                all_entities = []
                for article in articles:
                    if article['key_entities'] and article['key_entities'] != '[]':
                        all_entities.extend(article['key_entities'])

                # Count entity frequencies
                from collections import Counter
                entity_counts = Counter(all_entities)
                top_entities = [entity for entity, count in entity_counts.most_common(10)]

                # Get sentiment distribution
                sentiment_counts = Counter([a['sentiment_label'] for a in articles if a['sentiment_label']])

                # Sample headlines for context
                sample_headlines = [a['headline'] for a in articles[:20]]

                prompt = f"""You are analyzing {article_count} historical newspaper articles from Pakistan's Dawn newspaper, published between {start_date} and {end_date}.

KEY STATISTICS:
- Total Articles: {article_count}
- Date Range: {start_date} to {end_date}
- Sentiment Distribution: {dict(sentiment_counts)}
- Top Entities: {', '.join(top_entities[:8])}

SAMPLE HEADLINES:
{chr(10).join(['- ' + h for h in sample_headlines[:15]])}

Please provide a comprehensive summary (5-7 paragraphs) covering:

1. **Main Themes & Events**: What were the dominant news topics and major events during this period?

2. **Key Figures & Organizations**: Who were the important people, institutions, and organizations in the news?

3. **Geographic Focus**: Which cities, regions, or countries were prominently featured?

4. **Sentiment & Tone**: What was the overall tone of coverage (based on sentiment analysis)?

5. **Historical Context**: What was happening in Pakistan and globally during this time that influenced the news?

6. **Notable Patterns**: Any interesting trends, recurring themes, or significant patterns in coverage?

Write in a professional, analytical tone suitable for academic or research purposes. Focus on insights that would be valuable for understanding this historical period.

SUMMARY:"""

                response = model.generate_content(prompt)
                summary_text = response.text.strip()

            except Exception as e:
                summary_text = f"AI Summary generation failed. Analyzed {article_count} articles from {start_date} to {end_date}. Top entities include: {', '.join(top_entities[:5])}."
                print(f"Gemini API error: {str(e)}")

            return {
                "date_range": f"{start_date} to {end_date}",
                "article_count": article_count,
                "summary": summary_text,
                "top_entities": top_entities[:8],
                "sentiment_distribution": dict(sentiment_counts)
            }

    except psycopg2.Error as e:
        raise HTTPException(500, f"Database error: {str(e)}")

@app.get("/")
def root():
    return {"message": "MediaScope API", "version": "2.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
