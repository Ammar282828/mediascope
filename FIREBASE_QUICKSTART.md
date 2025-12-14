# 🚀 MediaScope Firebase Quick Start

Deploy MediaScope to Firebase in 3 simple steps!

## Prerequisites

1. **Google Account** - Sign up at [firebase.google.com](https://firebase.google.com)
2. **Node.js** - Download from [nodejs.org](https://nodejs.org)

## Step 1: Install Tools (5 minutes)

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Install Google Cloud CLI
# macOS:
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Windows: Download from https://cloud.google.com/sdk/docs/install
```

## Step 2: Create Firebase Project (2 minutes)

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **"Add Project"**
3. Enter name: `mediascope-app` (or any name you prefer)
4. Disable Google Analytics (optional)
5. Click **"Create Project"**

## Step 3: Deploy! (10 minutes)

```bash
# Navigate to your project
cd /Users/ammarmansa/Downloads/files

# Login to Firebase
firebase login

# Login to Google Cloud
gcloud auth login

# Run the automated deployment script
./deploy-firebase.sh
```

**That's it!** 🎉

The script will ask you a few questions:
- Your Firebase Project ID (e.g., `mediascope-app`)
- Region (press Enter for default: `us-central1`)
- Database password (create a secure one)

After 5-10 minutes, your app will be live at:
- **https://your-project-id.web.app**

## 📊 Import Your Database (Optional)

If you have existing data:

```bash
# 1. Export local database
pg_dump -U mediascope_user mediascope > backup.sql

# 2. Upload to Google Cloud Storage
gsutil mb gs://mediascope-backups
gsutil cp backup.sql gs://mediascope-backups/

# 3. Import to Cloud SQL
gcloud sql import sql mediascope-db \
  gs://mediascope-backups/backup.sql \
  --database=mediascope
```

## 🌐 Custom Domain (Optional)

### Add Your Own Domain:

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Click **Hosting** → **Add Custom Domain**
4. Enter your domain (e.g., `mediascope.com`)
5. Add the DNS records to your domain registrar
6. Wait for verification (can take up to 24 hours)

## 💰 Costs

- **Frontend (Firebase Hosting)**: FREE
- **Backend (Cloud Run)**: FREE for first 2M requests/month
- **Database (Cloud SQL)**: ~$7-25/month

**Most users stay within the free tier!**

## 🔄 Update Your App

Made changes? Redeploy in seconds:

```bash
./deploy-firebase.sh
```

Or manually:

```bash
# Update frontend only
cd mediascope-frontend
npm run build
cd ..
firebase deploy --only hosting

# Update backend only
gcloud run deploy mediascope-api --source .
```

## 📱 Share Your App

Once deployed, anyone can access your MediaScope instance at:
**https://your-project-id.web.app**

Features they can use:
- 🔍 Search historical newspapers
- 📊 View analytics and trends
- 🖼️ Upload and analyze advertisement images
- 📰 Upload newspapers for OCR processing

## 🆘 Troubleshooting

### "Firebase command not found"
```bash
npm install -g firebase-tools
```

### "gcloud command not found"
Install from: https://cloud.google.com/sdk/docs/install

### "Permission denied" on deploy-firebase.sh
```bash
chmod +x deploy-firebase.sh
```

### Backend not connecting to database

1. Check Cloud SQL is running:
```bash
gcloud sql instances list
```

2. Verify connection string:
```bash
gcloud sql instances describe mediascope-db
```

### CORS errors

Update backend environment:
```bash
gcloud run services update mediascope-api \
  --update-env-vars ALLOWED_ORIGINS=https://your-project-id.web.app
```

## 📚 Full Documentation

For detailed instructions, see:
- [FIREBASE_DEPLOYMENT.md](FIREBASE_DEPLOYMENT.md) - Complete guide
- [Firebase Documentation](https://firebase.google.com/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)

## 🎯 Next Steps

After deployment:
1. ✅ Test your app at the provided URL
2. ✅ Import your database (if you have data)
3. ✅ Set up a custom domain (optional)
4. ✅ Share with users!

---

**Questions?** Check the full guide: [FIREBASE_DEPLOYMENT.md](FIREBASE_DEPLOYMENT.md)
