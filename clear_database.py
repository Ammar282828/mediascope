#!/usr/bin/env python3
"""
Clear all data from Firestore database
"""

from firestore_db import get_db

def clear_all_data():
    """Delete all documents from all collections"""
    db = get_db()

    collections = ['articles', 'newspapers', 'entities']

    for collection_name in collections:
        print(f"\nClearing collection: {collection_name}")
        collection_ref = db.db.collection(collection_name)

        # Get all documents
        docs = collection_ref.stream()

        deleted_count = 0
        batch = db.db.batch()
        batch_count = 0

        for doc in docs:
            batch.delete(doc.reference)
            batch_count += 1
            deleted_count += 1

            # Commit batch every 500 documents (Firestore limit)
            if batch_count >= 500:
                batch.commit()
                print(f"  Deleted {deleted_count} documents so far...")
                batch = db.db.batch()
                batch_count = 0

        # Commit remaining documents
        if batch_count > 0:
            batch.commit()

        print(f"  ✓ Deleted {deleted_count} documents from {collection_name}")

    print("\n✅ Database cleared successfully!")
    print("\nYou can now run the pipeline on a fresh dataset.")

if __name__ == "__main__":
    confirm = input("⚠️  This will DELETE ALL DATA from Firestore. Are you sure? (yes/no): ")
    if confirm.lower() == 'yes':
        clear_all_data()
    else:
        print("Operation cancelled.")
