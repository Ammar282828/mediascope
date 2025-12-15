#!/usr/bin/env python3
"""
Firebase Firestore Database Layer for MediaScope
Replaces PostgreSQL + Elasticsearch with cloud Firestore
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

class FirestoreDB:
    """Firestore database manager for MediaScope"""

    def __init__(self):
        """Initialize Firestore connection"""
        # Simple in-memory cache to reduce reads
        self._cache = {}
        self._cache_timestamp = {}
        self._cache_ttl = 300  # 5 minutes cache

        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            # Try to load from service account file
            service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')

            if service_account_path and os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
            else:
                # Try to initialize with default credentials or environment variable
                firebase_admin.initialize_app()

        self.db = firestore.client()
        print("[OK] Connected to Firebase Firestore")

    def _get_cached(self, key: str):
        """Get value from cache if not expired"""
        import time
        if key in self._cache:
            if time.time() - self._cache_timestamp.get(key, 0) < self._cache_ttl:
                print(f"[CACHE HIT] {key}")
                return self._cache[key]
        return None

    def _set_cached(self, key: str, value):
        """Store value in cache"""
        import time
        self._cache[key] = value
        self._cache_timestamp[key] = time.time()
        print(f"[CACHE SET] {key}")

    def store_article(self, article_data: Dict) -> str:
        """Store article in Firestore

        Args:
            article_data: Dictionary containing article information

        Returns:
            Document ID of stored article
        """
        try:
            # Generate unique ID if not provided
            article_id = article_data.get('id', self.db.collection('articles').document().id)

            # Prepare data for Firestore
            doc_data = {
                'id': article_id,
                'headline': article_data.get('headline', ''),
                'content': article_data.get('content', ''),
                'publication_date': article_data.get('publication_date'),
                'page_number': article_data.get('page_number', 1),
                'newspaper_id': article_data.get('newspaper_id'),
                'sentiment_score': article_data.get('sentiment_score', 0.0),
                'sentiment_label': article_data.get('sentiment_label', 'neutral'),
                'topic_label': article_data.get('topic_label', ''),
                'word_count': article_data.get('word_count', 0),
                'entities': article_data.get('entities', []),
                'created_at': firestore.SERVER_TIMESTAMP,
            }

            # Store in Firestore
            self.db.collection('articles').document(article_id).set(doc_data)

            print(f"[OK] Stored article: {article_id}")
            return article_id

        except Exception as e:
            print(f"[ERROR] Failed to store article: {e}")
            raise

    def get_article(self, article_id: str) -> Optional[Dict]:
        """Retrieve article by ID

        Args:
            article_id: Article document ID

        Returns:
            Article data dictionary or None if not found
        """
        try:
            doc = self.db.collection('articles').document(article_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"[ERROR] Failed to retrieve article: {e}")
            return None

    def search_articles(self, query: str, limit: int = 50) -> List[Dict]:
        """Search articles by keyword with relevance ranking

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching articles sorted by relevance (mention count, then timestamp)
        """
        try:
            # Get all articles and search in them
            all_articles = self.db.collection('articles').limit(1000).stream()

            results_with_score = []
            query_lower = query.lower()

            for doc in all_articles:
                data = doc.to_dict()
                headline = data.get('headline', '').lower()
                content = data.get('content', '').lower()
                combined_text = headline + ' ' + content

                # Check if query appears in the article
                if query_lower in combined_text:
                    # Count mentions (more mentions = more relevant)
                    mention_count = combined_text.count(query_lower)

                    # Get created_at timestamp for secondary sorting
                    created_at = data.get('created_at')
                    if created_at:
                        timestamp = created_at.timestamp() if hasattr(created_at, 'timestamp') else 0
                    else:
                        timestamp = 0

                    results_with_score.append({
                        'data': data,
                        'mentions': mention_count,
                        'timestamp': timestamp
                    })

            # Sort by mention count (descending), then by timestamp (descending for newest first)
            results_with_score.sort(key=lambda x: (x['mentions'], x['timestamp']), reverse=True)

            # Extract just the article data
            results = [item['data'] for item in results_with_score[:limit]]

            return results

        except Exception as e:
            print(f"[ERROR] Search failed: {e}")
            return []

    def search_by_entity(self, entity_name: str, entity_type: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Search articles by entity

        Args:
            entity_name: Name of entity to search for
            entity_type: Optional entity type filter (PERSON, ORG, GPE, etc.)
            limit: Maximum number of results

        Returns:
            List of matching articles
        """
        try:
            results = []

            # Get all articles and filter by entity (Firestore array queries are limited)
            articles = self.db.collection('articles').limit(300).stream()

            for doc in articles:
                data = doc.to_dict()
                entities = data.get('entities', [])

                for entity in entities:
                    if entity.get('text', '').lower() == entity_name.lower():
                        if entity_type is None or entity.get('type') == entity_type:
                            results.append(data)
                            break

                if len(results) >= limit:
                    break

            return results

        except Exception as e:
            print(f"[ERROR] Entity search failed: {e}")
            return []

    def get_analytics_articles_over_time(self) -> List[Dict]:
        """Get article count grouped by month"""
        # Check cache first
        cached = self._get_cached('articles_over_time')
        if cached is not None:
            return cached

        try:
            # Get all articles
            articles = self.db.collection('articles').limit(1000).stream()

            # Group by month
            monthly_counts = {}
            for doc in articles:
                data = doc.to_dict()
                pub_date = data.get('publication_date')
                if pub_date:
                    # Convert to datetime if needed
                    if isinstance(pub_date, str):
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))

                    month_key = pub_date.strftime('%Y-%m')
                    monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1

            # Convert to list format
            result = [
                {'month': month, 'count': count}
                for month, count in sorted(monthly_counts.items())
            ]

            # Cache the result
            self._set_cached('articles_over_time', result)
            return result

        except Exception as e:
            print(f"[ERROR] Analytics query failed: {e}")
            return []

    def get_analytics_sentiment_over_time(self) -> List[Dict]:
        """Get sentiment distribution over time"""
        try:
            articles = self.db.collection('articles').limit(1000).stream()

            # Group by month and sentiment
            monthly_sentiment = {}
            for doc in articles:
                data = doc.to_dict()
                pub_date = data.get('publication_date')
                sentiment = data.get('sentiment_label', 'neutral')

                if pub_date:
                    if isinstance(pub_date, str):
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))

                    month_key = pub_date.strftime('%Y-%m')
                    if month_key not in monthly_sentiment:
                        monthly_sentiment[month_key] = {'positive': 0, 'neutral': 0, 'negative': 0}

                    monthly_sentiment[month_key][sentiment] = monthly_sentiment[month_key].get(sentiment, 0) + 1

            # Convert to list format
            result = [
                {
                    'month': month,
                    'positive': counts['positive'],
                    'neutral': counts['neutral'],
                    'negative': counts['negative']
                }
                for month, counts in sorted(monthly_sentiment.items())
            ]

            return result

        except Exception as e:
            print(f"[ERROR] Sentiment analytics failed: {e}")
            return []

    def get_top_keywords(self, limit: int = 50) -> List[Dict]:
        """Get top keywords from articles"""
        try:
            import re
            # This is a simplified version - in production you'd use proper keyword extraction
            articles = self.db.collection('articles').limit(1000).stream()

            word_freq = {}
            # Comprehensive stop words list
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'this', 'that', 'these', 'those', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has',
                'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must',
                'can', 'from', 'as', 'it', 'its', 'their', 'them', 'they', 'he', 'she', 'him', 'her',
                'his', 'we', 'our', 'us', 'you', 'your', 'which', 'who', 'whom', 'whose', 'what', 'when',
                'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
                'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
                'also', 'just', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
                'between', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'up', 'down',
                'out', 'over', 'off', 'any', 'being', 'having', 'doing', 'one', 'two', 'three', 'four',
                'five', 'six', 'seven', 'eight', 'nine', 'ten', 'said', 'page', 'continued', 'back'
            }

            for doc in articles:
                data = doc.to_dict()
                content = data.get('content', '') + ' ' + data.get('headline', '')
                words = content.lower().split()

                for word in words:
                    # Clean word
                    word = word.strip('.,!?;:"\'()[]{}')

                    # Filter out: short words, stop words, numbers, dates, mixed alphanumeric
                    if (len(word) > 3 and
                        word not in stop_words and
                        not word.isdigit() and  # Pure numbers
                        not re.match(r'^\d+[a-z]+$', word) and  # Like "1st", "2nd"
                        not re.match(r'^[a-z]+\d+$', word) and  # Like "march11"
                        not re.match(r'^\d{1,2}[-/]\d{1,2}', word) and  # Dates like "11/03"
                        re.search(r'[a-z]', word)):  # Must contain at least one letter
                        word_freq[word] = word_freq.get(word, 0) + 1

            # Sort and return top keywords
            sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            result = [
                {'keyword': word, 'frequency': freq}
                for word, freq in sorted_keywords[:limit]
            ]

            return result

        except Exception as e:
            print(f"[ERROR] Keyword extraction failed: {e}")
            return []

    def get_sentiment_by_entity(self, entity_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get sentiment statistics for entities"""
        try:
            articles = self.db.collection('articles').limit(1000).stream()

            entity_sentiment = {}

            for doc in articles:
                data = doc.to_dict()
                sentiment = data.get('sentiment_label', 'neutral')
                entities = data.get('entities', [])

                for entity in entities:
                    entity_text = entity.get('text', '')
                    entity_type_val = entity.get('type', '')

                    # Skip DATE, TIME, CARDINAL, ORDINAL types (not useful for research)
                    if entity_type_val in ['DATE', 'TIME', 'CARDINAL', 'ORDINAL', 'QUANTITY', 'MONEY', 'PERCENT']:
                        continue

                    # Skip pure numbers and short entities
                    if len(entity_text) < 3 or entity_text.isdigit():
                        continue

                    # Filter by type if specified
                    if entity_type and entity_type_val != entity_type:
                        continue

                    if entity_text not in entity_sentiment:
                        entity_sentiment[entity_text] = {
                            'entity_text': entity_text,
                            'entity_type': entity_type_val,
                            'positive_count': 0,
                            'neutral_count': 0,
                            'negative_count': 0,
                            'article_count': 0,
                            'sentiment_scores': []
                        }

                    entity_sentiment[entity_text][f'{sentiment}_count'] += 1
                    entity_sentiment[entity_text]['article_count'] += 1

                    # Track sentiment scores for averaging
                    sentiment_score = data.get('sentiment_score', 0.0)
                    entity_sentiment[entity_text]['sentiment_scores'].append(sentiment_score)

            # Calculate avg_sentiment and clean up data
            for entity_data in entity_sentiment.values():
                scores = entity_data.pop('sentiment_scores', [])
                entity_data['avg_sentiment'] = sum(scores) / len(scores) if scores else 0.0

            # Sort by article count and return top entities
            sorted_entities = sorted(
                entity_sentiment.values(),
                key=lambda x: x['article_count'],
                reverse=True
            )

            # Filter entities with at least 2 mentions to reduce noise
            filtered_entities = [e for e in sorted_entities if e['article_count'] >= 2]

            return filtered_entities[:limit]

        except Exception as e:
            print(f"[ERROR] Entity sentiment analysis failed: {e}")
            return []

    def get_top_entities(self, entity_type: Optional[str] = None, limit: int = 15) -> List[Dict]:
        """Get top entities by frequency"""
        try:
            import re
            articles = self.db.collection('articles').limit(1000).stream()

            entity_counts = {}

            for doc in articles:
                data = doc.to_dict()
                entities = data.get('entities', [])

                for entity in entities:
                    entity_text = entity.get('text', '')
                    entity_type_val = entity.get('type', '')

                    # Skip DATE, TIME, CARDINAL, ORDINAL types (not useful for research)
                    if entity_type_val in ['DATE', 'TIME', 'CARDINAL', 'ORDINAL', 'QUANTITY', 'MONEY', 'PERCENT']:
                        continue

                    # Skip pure numbers and short entities
                    if len(entity_text) < 3 or entity_text.isdigit():
                        continue

                    # Filter by type if specified
                    if entity_type and entity_type_val != entity_type:
                        continue

                    # Create unique key for entity
                    entity_key = (entity_text, entity_type_val)

                    if entity_key not in entity_counts:
                        entity_counts[entity_key] = {
                            'text': entity_text,
                            'type': entity_type_val,
                            'count': 0
                        }

                    entity_counts[entity_key]['count'] += 1

            # Sort by count and return top entities
            sorted_entities = sorted(
                entity_counts.values(),
                key=lambda x: x['count'],
                reverse=True
            )

            return sorted_entities[:limit]

        except Exception as e:
            print(f"[ERROR] Top entities query failed: {e}")
            return []

    def close(self):
        """Close Firestore connection (no-op for Firestore)"""
        print("[OK] Firestore connection closed")


# Global instance
_db_instance = None

def get_db() -> FirestoreDB:
    """Get or create Firestore database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = FirestoreDB()
    return _db_instance
