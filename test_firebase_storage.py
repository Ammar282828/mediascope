#!/usr/bin/env python3
"""
Test Firebase Storage connection and list buckets
"""

import os
import firebase_admin
from firebase_admin import credentials, storage

# Initialize Firebase
service_account_path = 'firebase-service-account.json'

if not os.path.exists(service_account_path):
    print(f"❌ Service account file not found: {service_account_path}")
    exit(1)

# Initialize without specifying bucket
if not firebase_admin._apps:
    cred = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)
    print("✓ Firebase Admin initialized")

# Try to get default bucket
try:
    bucket = storage.bucket()
    print(f"✓ Default bucket: {bucket.name}")

    # Test upload
    print("\nTesting bucket access...")
    test_blob = bucket.blob('test/test.txt')
    test_blob.upload_from_string('test')
    print("✓ Upload successful!")

    # Make public
    test_blob.make_public()
    print(f"✓ Public URL: {test_blob.public_url}")

    # Clean up
    test_blob.delete()
    print("✓ Cleanup successful!")

    print(f"\n✅ Firebase Storage is working!")
    print(f"📝 Use this bucket name in .env: {bucket.name}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTrying alternative bucket names...")

    # Try different bucket name formats
    for bucket_name in [
        'fyp2026-87a9b.firebasestorage.app',
        'fyp2026-87a9b.appspot.com',
        'fyp2026-87a9b',
        'gs://fyp2026-87a9b.firebasestorage.app'
    ]:
        try:
            print(f"\nTrying: {bucket_name}")
            bucket = storage.bucket(bucket_name)
            print(f"✓ Found bucket: {bucket.name}")

            # Test access
            test_blob = bucket.blob('test/test.txt')
            test_blob.upload_from_string('test')
            test_blob.make_public()
            print(f"✓ Upload works! Public URL: {test_blob.public_url}")
            test_blob.delete()

            print(f"\n✅ Working bucket: {bucket_name}")
            print(f"📝 Update .env with: FIREBASE_STORAGE_BUCKET={bucket_name}")
            break

        except Exception as e2:
            print(f"  ✗ Failed: {e2}")
