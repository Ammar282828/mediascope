#!/usr/bin/env python3
"""
MediaScope Complete Processing Pipeline
- OCR with Gemini
- Layout Detection
- Named Entity Recognition (spaCy)
- Sentiment Analysis (RoBERTa/DistilBERT)
- Topic Modeling (BERTopic)
- Database Storage (PostgreSQL + Elasticsearch)
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import uuid

# Image processing
from PIL import Image, ImageEnhance
import google.generativeai as genai

# NLP
import spacy
from transformers import pipeline
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

# Database
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

# Configuration
from dataclasses import dataclass

@dataclass
class Config:
    """Configuration for MediaScope pipeline"""
    # Gemini API
    GEMINI_API_KEY: str = "AIzaSyDAZVe8H9Xsrh86xQW7DDgmmHdnyTeVJ8E"
    GEMINI_MODEL: str = "gemini-3-pro-preview"
    
    # PostgreSQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "mediascope"
    DB_USER: str = "mediascope_user"
    DB_PASSWORD: str = "your_password"
    
    # Elasticsearch
    ES_HOST: str = "localhost"
    ES_PORT: int = 9200
    ES_INDEX: str = "mediascope_articles"
    
    # Paths
    INPUT_FOLDER: str = "./input_newspapers"
    OUTPUT_FOLDER: str = "./processed_newspapers"
    
    # Models
    SPACY_MODEL: str = "en_core_web_lg"
    SENTIMENT_MODEL: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"


class MediaScopeDatabase:
    """Database handler for PostgreSQL and Elasticsearch"""
    
    def __init__(self, config: Config):
        self.config = config
        self.pg_conn = None
        self.es_client = None
        
    def connect(self):
        """Connect to PostgreSQL and Elasticsearch"""
        try:
            # PostgreSQL connection
            self.pg_conn = psycopg2.connect(
                host=self.config.DB_HOST,
                port=self.config.DB_PORT,
                database=self.config.DB_NAME,
                user=self.config.DB_USER,
                password=self.config.DB_PASSWORD
            )
            print("✅ Connected to PostgreSQL")
            
            # Elasticsearch connection
            self.es_client = Elasticsearch(
                [f"http://{self.config.ES_HOST}:{self.config.ES_PORT}"]
            )
            print("✅ Connected to Elasticsearch")
            
            # Create Elasticsearch index if not exists
            self._create_es_index()
            
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise
    
    def _create_es_index(self):
        """Create Elasticsearch index with mappings"""
        if not self.es_client.indices.exists(index=self.config.ES_INDEX):
            mapping = {
                "mappings": {
                    "properties": {
                        "article_id": {"type": "keyword"},
                        "headline": {
                            "type": "text",
                            "analyzer": "english",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "english"
                        },
                        "publication_date": {"type": "date"},
                        "sentiment_score": {"type": "float"},
                        "sentiment_label": {"type": "keyword"},
                        "topic_label": {"type": "keyword"},
                        "entities": {
                            "type": "nested",
                            "properties": {
                                "text": {"type": "keyword"},
                                "type": {"type": "keyword"}
                            }
                        }
                    }
                }
            }
            self.es_client.indices.create(index=self.config.ES_INDEX, body=mapping)
            print(f"✅ Created Elasticsearch index: {self.config.ES_INDEX}")
    
    def insert_newspaper(self, pub_date: datetime, page_num: int, 
                        section: str, image_path: str) -> str:
        """Insert newspaper record and return ID"""
        with self.pg_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO newspapers (publication_date, year, month, day, 
                                       page_number, section, image_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (publication_date, page_number) 
                DO UPDATE SET processed_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (pub_date, pub_date.year, pub_date.month, pub_date.day, 
                  page_num, section, image_path))
            newspaper_id = cur.fetchone()[0]
            self.pg_conn.commit()
            return newspaper_id
    
    def insert_article(self, newspaper_id: str, article_data: Dict) -> str:
        """Insert article and return ID"""
        with self.pg_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO articles (
                    newspaper_id, article_number, headline, content, 
                    word_count, bounding_box, sentiment_score, 
                    sentiment_label, topic_label, topic_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                newspaper_id,
                article_data['article_number'],
                article_data['headline'],
                article_data['content'],
                article_data['word_count'],
                json.dumps(article_data.get('bounding_box')),
                article_data.get('sentiment_score'),
                article_data.get('sentiment_label'),
                article_data.get('topic_label'),
                article_data.get('topic_id')
            ))
            article_id = cur.fetchone()[0]
            self.pg_conn.commit()
            return article_id
    
    def insert_entities(self, article_id: str, entities: List[Dict]):
        """Insert entities for an article"""
        if not entities:
            return
        
        with self.pg_conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO entities (article_id, entity_text, entity_type, 
                                     start_char, end_char, confidence)
                VALUES %s
            """, [(
                article_id,
                ent['text'],
                ent['type'],
                ent.get('start', 0),
                ent.get('end', 0),
                ent.get('confidence', 1.0)
            ) for ent in entities])
            self.pg_conn.commit()
    
    def index_article_es(self, article_id: str, article_data: Dict, 
                         entities: List[Dict], pub_date: datetime):
        """Index article in Elasticsearch"""
        doc = {
            "article_id": article_id,
            "headline": article_data['headline'],
            "content": article_data['content'],
            "publication_date": pub_date.isoformat(),
            "sentiment_score": article_data.get('sentiment_score'),
            "sentiment_label": article_data.get('sentiment_label'),
            "topic_label": article_data.get('topic_label'),
            "entities": [{"text": e['text'], "type": e['type']} for e in entities]
        }
        self.es_client.index(index=self.config.ES_INDEX, id=article_id, body=doc)
    
    def close(self):
        """Close database connections"""
        if self.pg_conn:
            self.pg_conn.close()
        print("✅ Database connections closed")


class ImageProcessor:
    """Handle image preprocessing and OCR"""
    
    def __init__(self, config: Config):
        self.config = config
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(config.GEMINI_MODEL)
    
    def extract_metadata(self, image_path: str) -> Dict:
        """Extract date and page number from newspaper"""
        try:
            img = Image.open(image_path)
            
            prompt = """Extract from this newspaper scan:
1. Publication date (month, day, year)
2. Page number

Respond ONLY in this format:
MONTH: [month name]
DAY: [day number]
YEAR: [4-digit year like 1990]
PAGE: [page number]

If not found, write UNKNOWN."""

            response = self.model.generate_content([prompt, img])
            text = response.text
            
            month_match = re.search(r'MONTH:\s*(\w+)', text, re.IGNORECASE)
            day_match = re.search(r'DAY:\s*(\d+)', text, re.IGNORECASE)
            year_match = re.search(r'YEAR:\s*(\d+)', text, re.IGNORECASE)
            page_match = re.search(r'PAGE:\s*(\d+)', text, re.IGNORECASE)
            
            month = month_match.group(1) if month_match else "January"
            day = int(day_match.group(1)) if day_match else 1
            year = int(year_match.group(1)) if year_match else 1990
            page = int(page_match.group(1)) if page_match else 1
            
            # Convert month name to number
            month_num = datetime.strptime(month[:3], '%b').month
            pub_date = datetime(year, month_num, day)
            
            return {
                'date': pub_date,
                'page': page,
                'success': True
            }
            
        except Exception as e:
            print(f"  ⚠️  Metadata extraction failed: {e}")
            return {
                'date': datetime(1990, 1, 1),
                'page': 1,
                'success': False
            }
    
    def enhance_image(self, image: Image.Image) -> Image.Image:
        """Enhance image for better OCR"""
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.3)
        
        # Increase sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        # Increase brightness slightly
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.1)
        
        return image
    
    def extract_articles(self, image_path: str) -> List[Dict]:
        """Extract article text using Gemini OCR"""
        try:
            img = Image.open(image_path)
            img = self.enhance_image(img)
            
            prompt = """This is a historical newspaper from 1990 being digitized for academic research.

Identify and extract article structure from this newspaper page:
- Number each distinct article (1, 2, 3...)
- Provide the headline for each
- Extract the text content for digital preservation

Format:
ARTICLE_START
NUMBER: [number]
HEADLINE: [headline text]
CONTENT: [article text for research archive]
ARTICLE_END

This is for educational and historical research purposes."""

            response = self.model.generate_content([prompt, img])
            text = response.text
            
            articles = []
            article_blocks = re.findall(
                r'ARTICLE_START(.*?)ARTICLE_END', 
                text, 
                re.DOTALL
            )
            
            for block in article_blocks:
                num_match = re.search(r'NUMBER:\s*(\d+)', block)
                headline_match = re.search(r'HEADLINE:\s*(.+?)(?=\n)', block)
                content_match = re.search(r'CONTENT:\s*(.+)', block, re.DOTALL)
                
                if headline_match and content_match:
                    headline = headline_match.group(1).strip()
                    content = content_match.group(1).strip()
                    
                    articles.append({
                        'number': int(num_match.group(1)) if num_match else len(articles) + 1,
                        'headline': headline,
                        'text': content,
                        'word_count': len(content.split())
                    })
            
            return articles
            
        except Exception as e:
            print(f"  ❌ Article extraction failed: {e}")
            return []


class NLPProcessor:
    """Handle NER, sentiment analysis, and topic modeling"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Load spaCy model
        print("📦 Loading spaCy model...")
        self.nlp = spacy.load(config.SPACY_MODEL)
        
        # Load sentiment model
        print("📦 Loading sentiment analysis model...")
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model=config.SENTIMENT_MODEL,
            top_k=None
        )
        
        # Load BERTopic
        # print("📦 Loading topic modeling...")
        # self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
        self.topic_model = None  # Skip for now  # Will be trained on full dataset
        
        print("✅ NLP models loaded")
    
    def extract_entities(self, text: str) -> List[Dict]:
        """Extract named entities using spaCy"""
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'type': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char,
                'confidence': 1.0
            })
        
        return entities
    
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment using RoBERTa"""
        # Truncate if too long (RoBERTa has 512 token limit)
        text = text[:1000]
        
        results = self.sentiment_analyzer(text)[0]
        
        # Convert to score from -1 to 1
        label_map = {'negative': -1, 'neutral': 0, 'positive': 1}
        
        # Get the highest scoring label
        top_result = max(results, key=lambda x: x['score'])
        label = top_result['label'].lower()
        
        # Calculate weighted score
        score = 0
        for result in results:
            lbl = result['label'].lower()
            score += label_map.get(lbl, 0) * result['score']
        
        return {
            'score': round(score, 3),
            'label': label,
            'confidence': round(top_result['score'], 3)
        }
    
    def train_topic_model(self, documents: List[str]) -> BERTopic:
        """Train BERTopic model on documents"""
        print("🤖 Training topic model...")
        
        self.topic_model = BERTopic(
            embedding_model=self.embedding_model,
            nr_topics="auto",
            min_topic_size=10
        )
        
        topics, probs = self.topic_model.fit_transform(documents)
        
        print(f"✅ Discovered {len(set(topics))} topics")
        return self.topic_model
    
    def assign_topic(self, text: str) -> Dict:
        """Assign topic to a document"""
        if not self.topic_model:
            return {'topic_id': -1, 'topic_label': 'Uncategorized'}
        
        topic, prob = self.topic_model.transform([text])
        
        if topic[0] == -1:
            return {'topic_id': -1, 'topic_label': 'Uncategorized'}
        
        topic_info = self.topic_model.get_topic(topic[0])
        keywords = [word for word, _ in topic_info[:5]]
        
        return {
            'topic_id': int(topic[0]),
            'topic_label': '_'.join(keywords),
            'confidence': float(prob[0])
        }


class MediaScopePipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db = MediaScopeDatabase(config)
        self.image_processor = ImageProcessor(config)
        self.nlp_processor = NLPProcessor(config)
    
    def initialize(self):
        """Initialize pipeline components"""
        self.db.connect()
    
    def process_single_newspaper(self, image_path: str) -> bool:
        """Process a single newspaper image"""
        print(f"\n{'='*70}")
        print(f"Processing: {Path(image_path).name}")
        print(f"{'='*70}")
        
        try:
            # Use default metadata (no Gemini API call)
            from datetime import date
            pub_date = date(1990, 1, 1)  # Default date
            page_num = 1  # Default page
            
            # Insert newspaper record
            newspaper_id = self.db.insert_newspaper(
                pub_date=pub_date,
                page_num=page_num,
                section='Main',
                image_path=image_path
            )
            print(f"✅ Newspaper record created: {newspaper_id}")
            
            # Extract articles
            print("📰 Extracting articles...")
            articles = self.image_processor.extract_articles(image_path)
            print(f"✅ Found {len(articles)} articles")
            
            # Process each article
            articles_processed = 0
            articles_failed = 0

            for article in articles:
                try:
                    print(f"\n  📄 Article {article['number']}: {article['headline'][:50]}...")

                    # NER
                    print("    🏷️  Extracting entities...")
                    entities = self.nlp_processor.extract_entities(article['text'])
                    print(f"    ✅ Found {len(entities)} entities")

                    # Sentiment
                    print("    😊 Analyzing sentiment...")
                    sentiment = self.nlp_processor.analyze_sentiment(article['text'])
                    print(f"    ✅ Sentiment: {sentiment['label']} ({sentiment['score']})")

                    # Topic (will be assigned after batch training)
                    topic = {'topic_id': None, 'topic_label': None}

                    # Prepare article data
                    article_data = {
                        'article_number': article['number'],
                        'headline': article['headline'],
                        'content': article['text'],
                        'word_count': article['word_count'],
                        'bounding_box': None,
                        'sentiment_score': sentiment['score'],
                        'sentiment_label': sentiment['label'],
                        'topic_id': topic['topic_id'],
                        'topic_label': topic['topic_label']
                    }

                    # Insert article
                    article_id = self.db.insert_article(newspaper_id, article_data)
                    print(f"    ✅ Article saved: {article_id}")

                    # Insert entities
                    self.db.insert_entities(article_id, entities)

                    # Index in Elasticsearch
                    self.db.index_article_es(
                        article_id,
                        article_data,
                        entities,
                        pub_date
                    )

                    articles_processed += 1

                except Exception as e:
                    articles_failed += 1
                    print(f"    ❌ Failed to process article {article.get('number', '?')}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue  # Continue with next article

            print(f"\n{'='*50}")
            print(f"✅ Newspaper processing complete")
            print(f"   Articles processed: {articles_processed}")
            if articles_failed > 0:
                print(f"   Articles failed: {articles_failed}")
            print(f"{'='*50}")
            return True
            
        except Exception as e:
            print(f"\n❌ Error processing newspaper: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_batch(self, image_folder: str, start_idx: int = 0, end_idx: int = None):
        """Process a batch of newspaper images"""
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.heic', '*.JPG', '*.JPEG', '*.PNG', '*.HEIC']:
            image_files.extend(Path(image_folder).glob(ext))
        
        if not image_files:
            print("❌ No images found")
            return
        
        image_files.sort()
        
        if end_idx is None:
            end_idx = len(image_files)
        
        image_files = image_files[start_idx:end_idx]
        print(f"📚 Processing newspapers {start_idx+1} to {min(end_idx, len(image_files)+start_idx)} (Total: {len(image_files)})")
        
        success_count = 0
        fail_count = 0
        
        for i, image_path in enumerate(image_files, 1):
            print(f"\n[{i}/{len(image_files)}]")
            
            if self.process_single_newspaper(str(image_path)):
                success_count += 1
            else:
                fail_count += 1
        
        # Summary
        print(f"\n{'='*70}")
        print("PROCESSING COMPLETE")
        print(f"{'='*70}")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {fail_count}")
        print(f"📊 Total: {len(image_files)}")
        print(f"{'='*70}")
    
    def close(self):
        """Cleanup resources"""
        self.db.close()


def main():
    """Main entry point"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║              MediaScope Processing Pipeline                      ║
║         Dawn Newspaper Archive (1990-1992)                       ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Load configuration
    config = Config()
    
    # Initialize pipeline
    pipeline = MediaScopePipeline(config)
    pipeline.initialize()
    
    try:
        # Process newspapers
        import sys
        
        start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
        end = int(sys.argv[2]) if len(sys.argv) > 2 else None
        
        if start > 0 or end:
            print(f"📋 Processing range: {start+1} to {end if end else 'end'}")
        
        pipeline.process_batch(config.INPUT_FOLDER, start, end)
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()