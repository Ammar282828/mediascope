#!/usr/bin/env python3
"""
Migration script to transfer data from PostgreSQL to Firebase Firestore
Transfers all articles, entities, and related data to the cloud database
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from firestore_db import get_db
from datetime import datetime
import json

# Load environment variables
load_dotenv()

def get_postgres_connection():
    """Create PostgreSQL connection"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "mediascope"),
        user=os.getenv("DB_USER", "mediascope_user"),
        password=os.getenv("DB_PASSWORD", "mediascope_pass"),
        cursor_factory=RealDictCursor
    )

def migrate_articles():
    """Migrate all articles from PostgreSQL to Firestore"""

    print("[MIGRATION] Starting migration from PostgreSQL to Firebase Firestore...")
    print("[MIGRATION] Connecting to PostgreSQL...")

    try:
        # Connect to PostgreSQL
        pg_conn = get_postgres_connection()
        pg_cursor = pg_conn.cursor()

        # Connect to Firestore
        print("[MIGRATION] Connecting to Firestore...")
        firestore_db = get_db()

        # Get total count
        pg_cursor.execute("SELECT COUNT(*) as count FROM articles")
        total_articles = pg_cursor.fetchone()['count']
        print(f"[MIGRATION] Found {total_articles} articles to migrate")

        # Fetch all articles with related data
        print("[MIGRATION] Fetching articles from PostgreSQL...")
        pg_cursor.execute("""
            SELECT
                a.id,
                a.headline,
                a.content,
                a.sentiment_score,
                a.sentiment_label,
                a.topic_label,
                a.word_count,
                a.newspaper_id,
                n.publication_date,
                n.page_number,
                COALESCE(
                    json_agg(
                        json_build_object('text', e.entity_text, 'type', e.entity_type)
                    ) FILTER (WHERE e.id IS NOT NULL),
                    '[]'
                ) as entities
            FROM articles a
            LEFT JOIN newspapers n ON a.newspaper_id = n.id
            LEFT JOIN entities e ON a.id = e.article_id
            GROUP BY a.id, a.headline, a.content, a.sentiment_score,
                     a.sentiment_label, a.topic_label, a.word_count,
                     a.newspaper_id, n.publication_date, n.page_number
            ORDER BY n.publication_date
        """)

        articles = pg_cursor.fetchall()

        print(f"[MIGRATION] Migrating {len(articles)} articles to Firestore...")

        # Migrate each article
        migrated_count = 0
        failed_count = 0

        for idx, article in enumerate(articles, 1):
            try:
                # Prepare article data for Firestore
                article_data = {
                    'id': article['id'],
                    'headline': article['headline'] or '',
                    'content': article['content'] or '',
                    'publication_date': article['publication_date'],
                    'page_number': article['page_number'] or 1,
                    'newspaper_id': article['newspaper_id'],
                    'sentiment_score': float(article['sentiment_score']) if article['sentiment_score'] else 0.0,
                    'sentiment_label': article['sentiment_label'] or 'neutral',
                    'topic_label': article['topic_label'] or '',
                    'word_count': article['word_count'] or 0,
                    'entities': []
                }

                # Parse entities from JSON
                if article['entities']:
                    if isinstance(article['entities'], str):
                        entities = json.loads(article['entities'])
                    else:
                        entities = article['entities']

                    # Filter out null entities
                    article_data['entities'] = [
                        e for e in entities
                        if e and e.get('text') and e.get('type')
                    ]

                # Store in Firestore
                firestore_db.store_article(article_data)

                migrated_count += 1

                # Progress update every 10 articles
                if idx % 10 == 0:
                    print(f"[PROGRESS] Migrated {idx}/{len(articles)} articles ({(idx/len(articles)*100):.1f}%)")

            except Exception as e:
                print(f"[ERROR] Failed to migrate article {article['id']}: {e}")
                failed_count += 1
                continue

        # Close connections
        pg_cursor.close()
        pg_conn.close()
        firestore_db.close()

        # Summary
        print("\n" + "="*60)
        print("[MIGRATION COMPLETE]")
        print(f"  Total articles in PostgreSQL: {total_articles}")
        print(f"  Successfully migrated: {migrated_count}")
        print(f"  Failed: {failed_count}")
        print("="*60)

        if failed_count > 0:
            print(f"\n[WARNING] {failed_count} articles failed to migrate. Check errors above.")
        else:
            print("\n[SUCCESS] All articles migrated successfully to Firebase Firestore!")
            print("[INFO] You can now use the shared cloud database.")
            print("[INFO] Other users will see this data when they connect.")

    except psycopg2.Error as e:
        print(f"\n[ERROR] PostgreSQL error: {e}")
        print("[INFO] Make sure your PostgreSQL database is running and accessible.")
        return False

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

def verify_migration():
    """Verify the migration by counting articles in Firestore"""
    print("\n[VERIFICATION] Checking migrated data in Firestore...")

    try:
        firestore_db = get_db()

        # Count articles in Firestore
        articles_ref = firestore_db.db.collection('articles')
        articles_count = len(list(articles_ref.stream()))

        print(f"[VERIFICATION] Found {articles_count} articles in Firestore")

        # Sample a few articles
        sample_articles = list(articles_ref.limit(3).stream())

        if sample_articles:
            print("\n[VERIFICATION] Sample articles:")
            for doc in sample_articles:
                data = doc.to_dict()
                print(f"  - {data.get('headline', 'No headline')[:60]}...")
                print(f"    Date: {data.get('publication_date')}, Sentiment: {data.get('sentiment_label')}")

        return True

    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("  MediaScope: PostgreSQL to Firebase Migration")
    print("="*60)
    print()

    # Check if Firebase is configured
    if not os.path.exists('firebase-service-account.json'):
        print("[ERROR] Firebase service account key not found!")
        print("[INFO] Please follow FIREBASE_SETUP.md to configure Firebase first.")
        print("[INFO] Download your service account key and save it as 'firebase-service-account.json'")
        exit(1)

    # Run migration
    success = migrate_articles()

    if success:
        # Verify migration
        verify_migration()

        print("\n[NEXT STEPS]")
        print("1. Start your backend: python mediascope_api.py")
        print("2. The backend will now use Firebase Firestore")
        print("3. All users connecting will see the same data")
        print("4. You can keep PostgreSQL as a backup or remove it")
    else:
        print("\n[MIGRATION FAILED]")
        print("Please check the errors above and try again.")
        exit(1)
