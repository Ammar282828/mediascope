# 🔥 Deploy MediaScope to Firebase

This guide will help you deploy MediaScope using Firebase Hosting (frontend) and Google Cloud Run (backend).

## 📋 Prerequisites

1. A Google/Firebase account
2. Node.js and npm installed
3. Firebase CLI installed
4. gcloud CLI installed (for backend deployment)

## 🚀 Quick Setup

### Step 1: Install Firebase CLI

```bash
npm install -g firebase-tools
```

### Step 2: Login to Firebase

```bash
firebase login
```

### Step 3: Create a Firebase Project

```bash
# Option A: Via Firebase Console (Recommended)
# Go to https://console.firebase.google.com/
# Click "Add Project" and follow the wizard

# Option B: Via CLI
firebase projects:create mediascope-app
```

## 📱 Deploy Frontend to Firebase Hosting

### 1. Initialize Firebase in Your Project

```bash
cd /Users/ammarmansa/Downloads/files
firebase init hosting
```

**Answer the prompts:**
- Use an existing project: Select your `mediascope-app` project
- What do you want to use as your public directory? `mediascope-frontend/build`
- Configure as a single-page app? `Yes`
- Set up automatic builds with GitHub? `No` (or Yes if you want)
- Overwrite index.html? `No`

### 2. Update Frontend API URL

Edit `mediascope-frontend/src/components/SearchPanel.tsx` and other API files:

```typescript
// Change from:
const API_BASE = 'http://localhost:8000/api';

// To:
const API_BASE = process.env.REACT_APP_API_URL || 'https://YOUR_CLOUD_RUN_URL/api';
```

Create `mediascope-frontend/.env.production`:
```bash
REACT_APP_API_URL=https://YOUR_CLOUD_RUN_URL/api
```

### 3. Build the Frontend

```bash
cd mediascope-frontend
npm install
npm run build
cd ..
```

### 4. Deploy to Firebase Hosting

```bash
firebase deploy --only hosting
```

**Your frontend will be live at:**
`https://mediascope-app.web.app` or `https://mediascope-app.firebaseapp.com`

## 🐳 Deploy Backend to Google Cloud Run

Cloud Run is perfect for your FastAPI backend and integrates seamlessly with Firebase.

### 1. Install Google Cloud SDK

```bash
# macOS
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Initialize
gcloud init
```

### 2. Enable Required APIs

```bash
gcloud services enable run.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

### 3. Create Cloud SQL Database

```bash
# Create PostgreSQL instance (this takes 5-10 minutes)
gcloud sql instances create mediascope-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Set password for postgres user
gcloud sql users set-password postgres \
  --instance=mediascope-db \
  --password=YOUR_SECURE_PASSWORD

# Create database
gcloud sql databases create mediascope --instance=mediascope-db
```

### 4. Update Backend Configuration

Create `mediascope-frontend/.env.production` if it doesn't exist:
```bash
DB_HOST=/cloudsql/YOUR_PROJECT_ID:us-central1:mediascope-db
DB_NAME=mediascope
DB_USER=postgres
DB_PASSWORD=YOUR_SECURE_PASSWORD
ALLOWED_ORIGINS=https://mediascope-app.web.app,https://mediascope-app.firebaseapp.com
```

### 5. Deploy Backend to Cloud Run

```bash
# Build and deploy
gcloud run deploy mediascope-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DB_HOST=/cloudsql/YOUR_PROJECT_ID:us-central1:mediascope-db,DB_NAME=mediascope,DB_USER=postgres,DB_PASSWORD=YOUR_SECURE_PASSWORD,ALLOWED_ORIGINS=https://mediascope-app.web.app" \
  --add-cloudsql-instances YOUR_PROJECT_ID:us-central1:mediascope-db
```

**Your backend will be at:**
`https://mediascope-api-XXXXX-uc.a.run.app`

### 6. Update Frontend with Backend URL

Now update the frontend environment variable with your actual Cloud Run URL:

```bash
# In mediascope-frontend/.env.production
REACT_APP_API_URL=https://mediascope-api-XXXXX-uc.a.run.app/api
```

Rebuild and redeploy frontend:
```bash
cd mediascope-frontend
npm run build
cd ..
firebase deploy --only hosting
```

## 🗄️ Import Your Database

### 1. Export Your Local Database

```bash
pg_dump -U mediascope_user -h localhost mediascope > mediascope_export.sql
```

### 2. Import to Cloud SQL

```bash
# Upload to Cloud Storage first
gsutil mb gs://mediascope-db-backups
gsutil cp mediascope_export.sql gs://mediascope-db-backups/

# Import to Cloud SQL
gcloud sql import sql mediascope-db \
  gs://mediascope-db-backups/mediascope_export.sql \
  --database=mediascope
```

## 📁 Complete Firebase Configuration

### firebase.json

Create/update `firebase.json`:

```json
{
  "hosting": {
    "public": "mediascope-frontend/build",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "**",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "public, max-age=3600"
          }
        ]
      }
    ]
  }
}
```

### .firebaserc

Create `.firebaserc`:

```json
{
  "projects": {
    "default": "mediascope-app"
  }
}
```

## 🔐 Environment Variables for Cloud Run

Create a `.env.yaml` for Cloud Run:

```yaml
DB_HOST: /cloudsql/YOUR_PROJECT_ID:us-central1:mediascope-db
DB_NAME: mediascope
DB_USER: postgres
DB_PASSWORD: YOUR_SECURE_PASSWORD
ALLOWED_ORIGINS: https://mediascope-app.web.app,https://mediascope-app.firebaseapp.com
```

Deploy with env file:
```bash
gcloud run deploy mediascope-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --env-vars-file .env.yaml \
  --add-cloudsql-instances YOUR_PROJECT_ID:us-central1:mediascope-db
```

## 🌐 Custom Domain (Optional)

### For Firebase Hosting:

1. Go to Firebase Console → Hosting
2. Click "Add custom domain"
3. Follow the wizard to add your domain (e.g., `mediascope.com`)
4. Firebase will provide DNS records to add to your domain registrar

### For Cloud Run:

1. Map custom domain:
```bash
gcloud run domain-mappings create \
  --service mediascope-api \
  --domain api.mediascope.com \
  --region us-central1
```

2. Add the DNS records shown in the output to your domain registrar

## 💰 Cost Estimate

### Firebase Hosting (Spark Plan - Free)
- Storage: 10 GB
- Transfer: 360 MB/day
- **Cost: FREE** for most small projects

### Cloud Run (Pay-as-you-go)
- **Free tier**: 2 million requests/month
- After free tier: $0.40 per million requests
- **Estimated: $0-5/month** for moderate traffic

### Cloud SQL
- db-f1-micro: **~$7/month**
- db-g1-small: **~$25/month** (better performance)

**Total: ~$7-30/month** depending on database size

## 🔄 Update/Redeploy

### Update Frontend:
```bash
cd mediascope-frontend
npm run build
cd ..
firebase deploy --only hosting
```

### Update Backend:
```bash
gcloud run deploy mediascope-api \
  --source . \
  --platform managed \
  --region us-central1
```

## 📊 Monitoring

### View Logs:

**Frontend:**
- Firebase Console → Hosting → Usage

**Backend:**
```bash
gcloud run services logs read mediascope-api --region us-central1
```

**Database:**
```bash
gcloud sql operations list --instance=mediascope-db
```

### Performance Monitoring:

Enable Firebase Performance Monitoring:
```bash
firebase init performance
```

## 🔒 Security Checklist

- [ ] Change default database password
- [ ] Update ALLOWED_ORIGINS in backend
- [ ] Enable Cloud SQL SSL/TLS
- [ ] Set up Firebase App Check (prevents API abuse)
- [ ] Review Cloud Run IAM permissions
- [ ] Enable Cloud Armor (DDoS protection)

## 🚨 Troubleshooting

### CORS Errors:
Update `ALLOWED_ORIGINS` in Cloud Run:
```bash
gcloud run services update mediascope-api \
  --update-env-vars ALLOWED_ORIGINS=https://mediascope-app.web.app
```

### Database Connection Issues:
Check Cloud SQL connection:
```bash
gcloud sql instances describe mediascope-db
```

### Backend Not Responding:
Check logs:
```bash
gcloud run services logs read mediascope-api --region us-central1 --limit 50
```

## 📦 One-Command Deployment Script

Create `deploy.sh`:

```bash
#!/bin/bash

# Build frontend
cd mediascope-frontend
npm run build
cd ..

# Deploy frontend to Firebase
firebase deploy --only hosting

# Deploy backend to Cloud Run
gcloud run deploy mediascope-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --env-vars-file .env.yaml \
  --add-cloudsql-instances YOUR_PROJECT_ID:us-central1:mediascope-db

echo "✅ Deployment complete!"
echo "Frontend: https://mediascope-app.web.app"
echo "Backend: Check Cloud Run console for URL"
```

Make executable and run:
```bash
chmod +x deploy.sh
./deploy.sh
```

## 🎉 You're Live!

Your MediaScope instance is now publicly accessible:

- **Frontend**: `https://mediascope-app.web.app`
- **Backend**: `https://mediascope-api-XXXXX-uc.a.run.app`

Share these URLs with anyone to let them:
- 🔍 Search Dawn newspaper archives
- 📊 View analytics and trends
- 🖼️ Upload and analyze ads
- 📰 Process newspapers with OCR

---

## 📚 Resources

- [Firebase Hosting Docs](https://firebase.google.com/docs/hosting)
- [Cloud Run Docs](https://cloud.google.com/run/docs)
- [Cloud SQL Docs](https://cloud.google.com/sql/docs)
- [Firebase Console](https://console.firebase.google.com/)
- [Cloud Console](https://console.cloud.google.com/)

Need help? Check the [Firebase Community](https://firebase.google.com/community) or [Stack Overflow](https://stackoverflow.com/questions/tagged/firebase).
