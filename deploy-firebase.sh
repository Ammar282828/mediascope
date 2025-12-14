#!/bin/bash

# MediaScope Firebase Deployment Script
# This script automates the deployment of MediaScope to Firebase

set -e  # Exit on error

echo "🔥 MediaScope Firebase Deployment"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    echo -e "${RED}❌ Firebase CLI not found!${NC}"
    echo "Install it with: npm install -g firebase-tools"
    exit 1
fi

# Check if gcloud CLI is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Google Cloud CLI not found!${NC}"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo -e "${GREEN}✅ All required tools found${NC}"
echo ""

# Get project configuration
read -p "Enter your Firebase/GCP Project ID: " PROJECT_ID
read -p "Enter your Cloud Run region (default: us-central1): " REGION
REGION=${REGION:-us-central1}

read -p "Enter your Cloud SQL instance name (default: mediascope-db): " SQL_INSTANCE
SQL_INSTANCE=${SQL_INSTANCE:-mediascope-db}

read -sp "Enter your database password: " DB_PASSWORD
echo ""

# Set project
echo -e "${YELLOW}📋 Setting project to $PROJECT_ID...${NC}"
gcloud config set project $PROJECT_ID
firebase use $PROJECT_ID || firebase use --add $PROJECT_ID

# Create .env.yaml for Cloud Run
echo -e "${YELLOW}📝 Creating environment configuration...${NC}"
cat > .env.yaml <<EOF
DB_HOST: /cloudsql/$PROJECT_ID:$REGION:$SQL_INSTANCE
DB_NAME: mediascope
DB_USER: postgres
DB_PASSWORD: $DB_PASSWORD
ALLOWED_ORIGINS: https://$PROJECT_ID.web.app,https://$PROJECT_ID.firebaseapp.com
EOF

# Build frontend
echo -e "${YELLOW}🔨 Building frontend...${NC}"
cd mediascope-frontend

# Create production environment file
cat > .env.production <<EOF
REACT_APP_API_URL=https://mediascope-api-$PROJECT_ID-$REGION.a.run.app/api
EOF

npm install
npm run build

cd ..

# Deploy backend to Cloud Run
echo -e "${YELLOW}🚀 Deploying backend to Cloud Run...${NC}"
gcloud run deploy mediascope-api \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --env-vars-file .env.yaml \
  --add-cloudsql-instances $PROJECT_ID:$REGION:$SQL_INSTANCE \
  --timeout 300 \
  --memory 1Gi

# Get Cloud Run URL
BACKEND_URL=$(gcloud run services describe mediascope-api --region $REGION --format 'value(status.url)')
echo -e "${GREEN}✅ Backend deployed to: $BACKEND_URL${NC}"

# Update frontend with actual backend URL
echo -e "${YELLOW}🔄 Updating frontend with backend URL...${NC}"
cat > mediascope-frontend/.env.production <<EOF
REACT_APP_API_URL=$BACKEND_URL/api
EOF

# Rebuild frontend with correct API URL
cd mediascope-frontend
npm run build
cd ..

# Deploy frontend to Firebase Hosting
echo -e "${YELLOW}🚀 Deploying frontend to Firebase Hosting...${NC}"
firebase deploy --only hosting

# Get frontend URL
FRONTEND_URL="https://$PROJECT_ID.web.app"

echo ""
echo -e "${GREEN}=================================="
echo "🎉 Deployment Complete!"
echo "==================================${NC}"
echo ""
echo "Your MediaScope instance is live:"
echo -e "${GREEN}Frontend: $FRONTEND_URL${NC}"
echo -e "${GREEN}Backend:  $BACKEND_URL${NC}"
echo ""
echo "Share these URLs with anyone to let them access your archive!"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Import your database (see FIREBASE_DEPLOYMENT.md)"
echo "2. Set up a custom domain (optional)"
echo "3. Enable monitoring and analytics"
echo ""

# Clean up sensitive files
rm -f .env.yaml

echo -e "${GREEN}✅ All done!${NC}"
