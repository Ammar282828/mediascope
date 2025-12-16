#!/usr/bin/env python3
"""
Diagnose Firebase authentication issues
"""

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def test_firebase_auth():
    """Test Firebase authentication and diagnose issues"""

    service_account_path = 'firebase-service-account.json'

    print("=" * 60)
    print("Firebase Authentication Diagnostic")
    print("=" * 60)

    # Check if file exists
    if not os.path.exists(service_account_path):
        print(f"\n❌ ERROR: Service account file not found")
        print(f"   Looking for: {os.path.abspath(service_account_path)}")
        print(f"\n📝 To fix:")
        print(f"   1. Go to Firebase Console > Project Settings > Service Accounts")
        print(f"   2. Click 'Generate New Private Key'")
        print(f"   3. Save as 'firebase-service-account.json' in project root")
        return False

    print(f"\n✓ Service account file found: {service_account_path}")

    # Check if file is valid JSON
    try:
        with open(service_account_path, 'r') as f:
            service_account = json.load(f)
        print(f"✓ File is valid JSON")
    except json.JSONDecodeError as e:
        print(f"\n❌ ERROR: Invalid JSON file")
        print(f"   Error: {e}")
        print(f"\n📝 To fix: Re-download the service account key from Firebase Console")
        return False

    # Check required fields
    required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
    missing_fields = [f for f in required_fields if f not in service_account]

    if missing_fields:
        print(f"\n❌ ERROR: Missing required fields: {missing_fields}")
        print(f"\n📝 To fix: Download a fresh service account key from Firebase Console")
        return False

    print(f"✓ All required fields present")
    print(f"   Project ID: {service_account['project_id']}")
    print(f"   Client Email: {service_account['client_email']}")

    # Check private key format
    private_key = service_account.get('private_key', '')
    if not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
        print(f"\n❌ ERROR: Invalid private key format")
        print(f"\n📝 To fix: Download a fresh service account key from Firebase Console")
        return False

    print(f"✓ Private key format valid")

    # Try to initialize Firebase
    try:
        # Clean up any existing apps
        try:
            firebase_admin.get_app()
            firebase_admin.delete_app(firebase_admin.get_app())
        except ValueError:
            pass

        print(f"\n🔄 Testing Firebase connection...")
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        print(f"✓ Firebase Admin initialized successfully")

        # Try to connect to Firestore
        db = firestore.client()
        print(f"✓ Connected to Firestore")

        # Try to read from a collection (this tests actual permissions)
        collections = list(db.collections(limit=1))
        print(f"✓ Firestore permissions verified")

        print(f"\n" + "=" * 60)
        print(f"✅ ALL TESTS PASSED - Firebase is working correctly!")
        print(f"=" * 60)
        return True

    except Exception as e:
        error_str = str(e)
        print(f"\n❌ ERROR: Firebase connection failed")
        print(f"   Error: {error_str}")

        if 'invalid_grant' in error_str or 'Invalid JWT' in error_str:
            print(f"\n📝 DIAGNOSIS: Service account credentials are invalid or expired")
            print(f"\n🔧 HOW TO FIX:")
            print(f"   1. Go to: https://console.firebase.google.com/")
            print(f"   2. Select your project: {service_account.get('project_id', 'N/A')}")
            print(f"   3. Click gear icon ⚙️ > Project Settings")
            print(f"   4. Go to 'Service Accounts' tab")
            print(f"   5. Click 'Generate New Private Key' button")
            print(f"   6. Save the downloaded file as 'firebase-service-account.json'")
            print(f"   7. Replace the existing file in your project")
            print(f"   8. Restart your backend server")

        elif 'permission' in error_str.lower():
            print(f"\n📝 DIAGNOSIS: Service account lacks required permissions")
            print(f"\n🔧 HOW TO FIX:")
            print(f"   1. Go to Firebase Console > Project Settings > Service Accounts")
            print(f"   2. Make sure the service account has 'Firebase Admin SDK' role")
            print(f"   3. Or generate a new key (which will have correct permissions)")

        else:
            print(f"\n📝 DIAGNOSIS: Unknown error - check network/firewall")
            print(f"\n🔧 HOW TO FIX:")
            print(f"   1. Check internet connection")
            print(f"   2. Check if firewall is blocking Firebase")
            print(f"   3. Try generating a fresh service account key")

        return False

if __name__ == '__main__':
    success = test_firebase_auth()
    exit(0 if success else 1)
