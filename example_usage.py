#!/usr/bin/env python3
"""
MediaScope - Example Usage Script
Demonstrates the complete workflow from processing to analysis
"""

import requests
import json
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
API_BASE = "http://localhost:8000/api"
SAMPLE_IMAGE = "./input_newspapers/sample_newspaper.jpg"


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def check_api_health():
    """Check if API is running"""
    print_section("1. Checking API Health")
    
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy")
            print(f"   Status: {data['status']}")
            print(f"   Timestamp: {data['timestamp']}")
            return True
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {API_BASE}")
        print(f"   Make sure the backend is running:")
        print(f"   uvicorn mediascope_api:app --reload")
        return False


def register_user():
    """Register a test user"""
    print_section("2. Registering Test User")
    
    user_data = {
        "username": "test_user",
        "email": "test@mediascope.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{API_BASE}/auth/register", json=user_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ User registered successfully")
            print(f"   Username: {data['user']['username']}")
            print(f"   Email: {data['user']['email']}")
            return True
        elif response.status_code == 400:
            print(f"ℹ️  User already exists (this is okay)")
            return True
        else:
            print(f"❌ Registration failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def login_user():
    """Login and get access token"""
    print_section("3. Logging In")
    
    credentials = {
        "email": "test@mediascope.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{API_BASE}/auth/login", json=credentials)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login successful")
            print(f"   Token type: {data['token_type']}")
            print(f"   User: {data['user']['username']}")
            return data['access_token']
        else:
            print(f"❌ Login failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def search_keyword(keyword):
    """Search for articles by keyword"""
    print_section(f"4. Searching for '{keyword}'")
    
    search_data = {
        "query": keyword,
        "start_date": "1990-01-01",
        "end_date": "1992-12-31",
        "limit": 5
    }
    
    try:
        response = requests.post(f"{API_BASE}/search/keyword", json=search_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} articles")
            
            if data['articles']:
                print(f"\n   Top Results:")
                for i, article in enumerate(data['articles'][:3], 1):
                    print(f"\n   {i}. {article['headline']}")
                    print(f"      Date: {article['publication_date']}")
                    print(f"      Sentiment: {article['sentiment_label']} ({article['sentiment_score']:.2f})")
                    if article.get('topic_label'):
                        print(f"      Topic: {article['topic_label']}")
            else:
                print(f"   No articles found. Process some newspapers first!")
            
            return data
        else:
            print(f"❌ Search failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def search_entity(entity_name):
    """Search for articles mentioning an entity"""
    print_section(f"5. Searching for Entity: '{entity_name}'")
    
    search_data = {
        "entity_name": entity_name,
        "entity_type": "PERSON",
        "start_date": "1990-01-01",
        "end_date": "1992-12-31",
        "limit": 5
    }
    
    try:
        response = requests.post(f"{API_BASE}/search/entity", json=search_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} articles mentioning {entity_name}")
            
            if data['articles']:
                print(f"\n   Sample Articles:")
                for i, article in enumerate(data['articles'][:3], 1):
                    print(f"\n   {i}. {article['headline']}")
                    print(f"      Date: {article['publication_date']}")
                    
                    # Show relevant entities
                    if article.get('entities'):
                        entity_texts = [e['text'] for e in article['entities'][:3]]
                        print(f"      Entities: {', '.join(entity_texts)}")
            
            return data
        else:
            print(f"❌ Search failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_keyword_trends():
    """Get keyword frequency trends"""
    print_section("6. Analyzing Keyword Trends")
    
    trend_data = {
        "keywords": ["politics", "economy", "education"],
        "start_date": "1990-01-01",
        "end_date": "1992-12-31",
        "granularity": "month"
    }
    
    try:
        response = requests.post(f"{API_BASE}/analytics/keyword-trend", json=trend_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Trend analysis complete")
            print(f"   Period: {data['start_date']} to {data['end_date']}")
            print(f"\n   Sample Data Points:")
            
            for keyword, trends in data['trends'].items():
                if trends:
                    total_mentions = sum(point['count'] for point in trends)
                    print(f"\n   '{keyword}': {total_mentions} total mentions")
                    
                    # Show first 3 data points
                    for point in trends[:3]:
                        print(f"      {point['date']}: {point['count']} mentions")
            
            return data
        else:
            print(f"❌ Trend analysis failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_top_entities():
    """Get most mentioned entities"""
    print_section("7. Finding Top Entities")
    
    try:
        response = requests.get(
            f"{API_BASE}/analytics/top-entities",
            params={"entity_type": "PERSON", "limit": 10}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Top 10 People Mentioned:")
            
            if data['entities']:
                for i, entity in enumerate(data['entities'], 1):
                    print(f"\n   {i}. {entity['text']}")
                    print(f"      Mentions: {entity['mentions']}")
                    print(f"      Avg Sentiment: {entity['avg_sentiment']:.2f}")
            else:
                print(f"   No entities found. Process some newspapers first!")
            
            return data
        else:
            print(f"❌ Failed to get entities: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_sentiment_overview():
    """Get sentiment distribution"""
    print_section("8. Sentiment Analysis Overview")
    
    try:
        response = requests.get(
            f"{API_BASE}/analytics/sentiment-overview",
            params={
                "start_date": "1990-01-01",
                "end_date": "1992-12-31"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sentiment Analysis Complete")
            print(f"   Total Articles: {data['total_articles']}")
            print(f"\n   Distribution:")
            
            for item in data['sentiment_breakdown']:
                emoji = "😊" if item['label'] == 'positive' else "😐" if item['label'] == 'neutral' else "😞"
                print(f"      {emoji} {item['label'].capitalize()}: {item['count']} ({item['percentage']}%)")
                print(f"         Avg Score: {item['avg_score']:.3f}")
            
            return data
        else:
            print(f"❌ Sentiment analysis failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_topic_distribution():
    """Get topic distribution"""
    print_section("9. Topic Distribution Analysis")
    
    topic_data = {
        "start_date": "1990-01-01",
        "end_date": "1990-12-31"
    }
    
    try:
        response = requests.post(f"{API_BASE}/analytics/topic-distribution", json=topic_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Topic Analysis Complete")
            print(f"   Period: {data['start_date']} to {data['end_date']}")
            print(f"\n   Top Topics:")
            
            if data['distribution']:
                for i, topic in enumerate(data['distribution'][:5], 1):
                    print(f"\n   {i}. {topic['topic_name']}")
                    print(f"      Articles: {topic['article_count']}")
                    print(f"      Percentage: {topic['percentage']}%")
            else:
                print(f"   No topics found. Process some newspapers first!")
            
            return data
        else:
            print(f"❌ Topic analysis failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def list_all_articles():
    """List recent articles"""
    print_section("10. Listing Recent Articles")
    
    try:
        response = requests.get(
            f"{API_BASE}/articles",
            params={"limit": 5}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found articles")
            
            if data['articles']:
                print(f"\n   Recent Articles:")
                for i, article in enumerate(data['articles'], 1):
                    print(f"\n   {i}. {article['headline']}")
                    print(f"      Date: {article['publication_date']}")
                    print(f"      Page: {article['page_number']}")
                    if article.get('topic_label'):
                        print(f"      Topic: {article['topic_label']}")
            else:
                print(f"   No articles in database yet.")
                print(f"   Run the processing pipeline to add newspapers:")
                print(f"   python mediascope_complete_pipeline.py")
            
            return data
        else:
            print(f"❌ Failed to list articles: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """Run the complete example workflow"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                MediaScope Example Usage                      ║
║         Demonstrating the complete workflow                  ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 1. Check API health
    if not check_api_health():
        print("\n⚠️  Cannot proceed without API connection")
        return
    
    # 2. Register user (optional, may already exist)
    register_user()
    
    # 3. Login (optional for most read operations)
    token = login_user()
    
    # 4. List articles to see what we have
    list_all_articles()
    
    # 5. Search by keyword
    search_keyword("politics")
    
    # 6. Search by entity
    search_entity("Pakistan")
    
    # 7. Get keyword trends
    get_keyword_trends()
    
    # 8. Get top entities
    get_top_entities()
    
    # 9. Get sentiment overview
    get_sentiment_overview()
    
    # 10. Get topic distribution
    get_topic_distribution()
    
    # Summary
    print_section("Summary")
    print("✅ Example workflow complete!")
    print("\nNext steps:")
    print("1. Process more newspapers: python mediascope_complete_pipeline.py")
    print("2. Explore the web dashboard: http://localhost:3000")
    print("3. Read API documentation: http://localhost:8000/docs")
    print("\nHappy analyzing! 📰📊")


if __name__ == "__main__":
    main()
