# MediaScope Deployment Guide

This guide will help you deploy MediaScope so that anyone can access it online.

## 🚀 Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed
- A server with at least 4GB RAM
- Port 80 (HTTP) and 8000 (API) available

### 1. Clone and Prepare

```bash
git clone <your-repository>
cd files
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file:
```bash
# Database Configuration
DB_HOST=postgres  # Use 'postgres' for Docker, 'localhost' for local
DB_NAME=mediascope
DB_USER=mediascope_user
DB_PASSWORD=your_secure_password_here  # CHANGE THIS!

# CORS Configuration
ALLOWED_ORIGINS=http://your-domain.com,https://your-domain.com

# API Configuration
API_PORT=8000
```

### 3. Start the Application

```bash
docker-compose up -d
```

The application will be available at:
- Frontend: http://localhost (port 80)
- API: http://localhost:8000

## 🌐 Deploy to the Cloud

### Option 1: Deploy to DigitalOcean (Recommended)

1. **Create a Droplet**
   - Go to digitalocean.com
   - Create a new Droplet (Ubuntu 22.04)
   - Choose at least 4GB RAM
   - Add your SSH key

2. **SSH into your server**
   ```bash
   ssh root@your_server_ip
   ```

3. **Install Docker**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   apt install docker-compose -y
   ```

4. **Clone and deploy**
   ```bash
   git clone <your-repository>
   cd files
   cp .env.example .env
   nano .env  # Edit configuration
   docker-compose up -d
   ```

5. **Configure Firewall**
   ```bash
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw allow 22/tcp
   ufw enable
   ```

6. **Access your application**
   - Visit http://your_server_ip

### Option 2: Deploy to AWS EC2

1. **Launch EC2 Instance**
   - Instance type: t3.medium (4GB RAM)
   - OS: Ubuntu 22.04
   - Security Group: Allow ports 22, 80, 443, 8000

2. **Connect and install**
   ```bash
   ssh -i your-key.pem ubuntu@your_instance_ip
   sudo apt update
   sudo apt install docker.io docker-compose -y
   sudo usermod -aG docker ubuntu
   ```

3. **Deploy application** (same as DigitalOcean steps 4-6)

### Option 3: Deploy to Heroku

1. **Install Heroku CLI**
   ```bash
   curl https://cli-assets.heroku.com/install.sh | sh
   ```

2. **Login and create app**
   ```bash
   heroku login
   heroku create mediascope-app
   ```

3. **Add Postgres addon**
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

### Option 4: Deploy to Vercel (Frontend) + Railway (Backend)

#### Frontend on Vercel:
1. Visit vercel.com
2. Import your GitHub repository
3. Set build command: `cd mediascope-frontend && npm run build`
4. Set output directory: `mediascope-frontend/build`
5. Deploy!

#### Backend on Railway:
1. Visit railway.app
2. New Project → Deploy from GitHub
3. Add PostgreSQL database
4. Set environment variables from `.env`
5. Deploy!

## 🔒 Production Security Checklist

Before making your app public, ensure:

- [ ] Changed default database password in `.env`
- [ ] Set strong `DB_PASSWORD`
- [ ] Updated `ALLOWED_ORIGINS` to your actual domain
- [ ] Enabled HTTPS (use Let's Encrypt)
- [ ] Set up database backups
- [ ] Configure firewall rules
- [ ] Remove or secure any debug endpoints
- [ ] Set up monitoring (optional but recommended)

## 📝 Setting up HTTPS (SSL Certificate)

### Using Let's Encrypt (Free)

1. **Install Certbot**
   ```bash
   sudo apt install certbot python3-certbot-nginx -y
   ```

2. **Get SSL Certificate**
   ```bash
   sudo certbot --nginx -d your-domain.com -d www.your-domain.com
   ```

3. **Auto-renewal**
   ```bash
   sudo certbot renew --dry-run
   ```

## 🗄️ Database Setup

### Initialize Database with Your Data

1. **Export your local database**
   ```bash
   pg_dump -U mediascope_user mediascope > mediascope_backup.sql
   ```

2. **Copy to server**
   ```bash
   scp mediascope_backup.sql root@your_server_ip:/root/
   ```

3. **Import on server**
   ```bash
   docker-compose exec postgres psql -U mediascope_user mediascope < mediascope_backup.sql
   ```

## 📊 Monitoring and Maintenance

### View Logs
```bash
docker-compose logs -f
docker-compose logs -f api     # API logs only
docker-compose logs -f frontend # Frontend logs only
```

### Restart Services
```bash
docker-compose restart
```

### Stop Services
```bash
docker-compose down
```

### Update Application
```bash
git pull
docker-compose build
docker-compose up -d
```

## 🔧 Troubleshooting

### Port Already in Use
```bash
# Check what's using port 80
sudo lsof -i :80
# Kill the process or use a different port
```

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps
docker-compose logs postgres
```

### Frontend Can't Connect to API
- Check API is running: `curl http://localhost:8000`
- Check CORS settings in `.env`
- Update frontend API_BASE URL if needed

## 💰 Cost Estimates

### DigitalOcean
- Basic Droplet (4GB RAM): $24/month
- Domain name: ~$12/year
- Total: ~$25/month

### AWS EC2
- t3.medium instance: ~$30/month
- Data transfer: ~$5-10/month
- Total: ~$35-40/month

### Free Options
- **Heroku**: Free tier available (limited hours)
- **Railway**: $5/month with generous free trial
- **Vercel**: Free for frontend hosting

## 🌍 Making it Publicly Accessible

### 1. Get a Domain Name
- Purchase from Namecheap, GoDaddy, or Google Domains (~$12/year)

### 2. Point Domain to Your Server
- Add an A record pointing to your server IP
- Wait for DNS propagation (can take up to 48 hours)

### 3. Update Configuration
```bash
# In .env
ALLOWED_ORIGINS=http://your-domain.com,https://your-domain.com
```

### 4. Set up HTTPS
- Follow the "Setting up HTTPS" section above

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Backup Guide](https://www.postgresql.org/docs/current/backup.html)
- [Nginx Configuration](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/getting-started/)

## 🆘 Support

If you encounter issues:
1. Check the logs: `docker-compose logs`
2. Verify environment variables in `.env`
3. Ensure all ports are open in firewall
4. Check database connectivity

## 🎉 You're Live!

Once deployed, share your MediaScope instance:
- http://your-domain.com - Frontend
- http://your-domain.com/api - API docs

Users can now:
- 🔍 Search historical Dawn newspaper archives
- 📊 View analytics and trends
- 🖼️ Upload and analyze advertisement images
- 📰 Upload newspapers for OCR processing

---

**Note**: Remember to regularly backup your database and keep your application updated!
