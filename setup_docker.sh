cd ~/Downloads/files

cat > Dockerfile.backend << 'EOF'
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY mediascope_api.py .
COPY .env .

EXPOSE 8000

CMD ["uvicorn", "mediascope_api:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

cat > Dockerfile.frontend << 'EOF'
FROM node:18-alpine as build

WORKDIR /app

COPY mediascope-frontend/package*.json ./
RUN npm install

COPY mediascope-frontend/ .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
EOF

cat > Dockerfile.pipeline << 'EOF'
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY mediascope_complete_pipeline.py .
COPY .env .

CMD ["python3", "mediascope_complete_pipeline.py"]
EOF

cat > nginx.conf << 'EOF'
server {
    listen 80;
    server_name localhost;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
EOF

cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: mediascope-postgres
    environment:
      POSTGRES_DB: mediascope
      POSTGRES_USER: mediascope_user
      POSTGRES_PASSWORD: mediascope_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mediascope_user -d mediascope"]
      interval: 10s
      timeout: 5s
      retries: 5

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.17.4
    container_name: mediascope-elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
      - "9300:9300"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: mediascope-backend
    environment:
      - DATABASE_URL=postgresql://mediascope_user:mediascope_pass@postgres:5432/mediascope
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - GEMINI_API_KEY=AIzaSyDAZVe8H9Xsrh86xQW7DDgmmHdnyTeVJ8E
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      elasticsearch:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    container_name: mediascope-frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

  pipeline:
    build:
      context: .
      dockerfile: Dockerfile.pipeline
    container_name: mediascope-pipeline
    environment:
      - DATABASE_URL=postgresql://mediascope_user:mediascope_pass@postgres:5432/mediascope
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - GEMINI_API_KEY=AIzaSyDAZVe8H9Xsrh86xQW7DDgmmHdnyTeVJ8E
    volumes:
      - ./newspaper_images:/app/newspaper_images:ro
    depends_on:
      postgres:
        condition: service_healthy
      elasticsearch:
        condition: service_healthy
    profiles:
      - processing

volumes:
  postgres_data:
  elasticsearch_data:

networks:
  default:
    name: mediascope-network
EOF

cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
elasticsearch==7.17.9
python-dotenv==1.0.0
pydantic==2.5.0
python-multipart==0.0.6
google-generativeai==0.8.3
spacy==3.7.2
transformers==4.35.2
torch==2.1.1
Pillow==10.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.1.1
bertopic==0.16.0
sentence-transformers==2.2.2
EOF

cat > .dockerignore << 'EOF'
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/
.git/
.gitignore
.vscode/
.idea/
*.log
.DS_Store
node_modules/
.env.local
.env.*.local
npm-debug.log*
yarn-debug.log*
yarn-error.log*
*.bak*
EOF

cat > .env << 'EOF'
DATABASE_URL=postgresql://mediascope_user:mediascope_pass@postgres:5432/mediascope
ELASTICSEARCH_URL=http://elasticsearch:9200
GEMINI_API_KEY=AIzaSyDAZVe8H9Xsrh86xQW7DDgmmHdnyTeVJ8E
EOF

cat > README_DOCKER.md << 'EOF'
# MediaScope Docker Setup

## Quick Start

### 1. Build and Start Services
```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Elasticsearch (port 9200)
- Backend API (port 8000)
- Frontend (port 3000)

### 2. Initialize Database
Wait 30 seconds for services to start, then:
```bash
docker-compose exec backend python3 -c "
from mediascope_api import init_db
init_db()
print('✅ Database initialized')
"
```

### 3. Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 4. Process Newspapers
Place newspaper images in `./newspaper_images/` folder, then:
```bash
# Process all newspapers
docker-compose --profile processing up pipeline

# Process specific range (e.g., first 5 newspapers)
docker-compose run --rm pipeline python3 mediascope_complete_pipeline.py 0 5
```

## Management Commands

### View Logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Restart Service
```bash
docker-compose restart backend
docker-compose restart frontend
```

### Stop Everything
```bash
docker-compose down
```

### Reset All Data (Fresh Start)
```bash
docker-compose down -v
docker-compose up -d
```

### Access Database
```bash
docker-compose exec postgres psql -U mediascope_user -d mediascope
```

### Access Backend Shell
```bash
docker-compose exec backend bash
```

## Troubleshooting

### Services Won't Start
```bash
docker-compose logs
```

### Database Issues
```bash
docker-compose restart postgres
docker-compose exec postgres pg_isready
```

### Rebuild After Code Changes
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

### Port Already in Use
Edit docker-compose.yml and change port mappings:
```yaml
ports:
  - "3001:80"  # Change 3000 to 3001
```

## File Structure
```
mediascope/
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── Dockerfile.pipeline
├── nginx.conf
├── requirements.txt
├── .env
├── mediascope_api.py
├── mediascope_complete_pipeline.py
├── mediascope-frontend/
└── newspaper_images/
```
EOF

cat > start.sh << 'EOF'
#!/bin/bash

echo "🚀 Starting MediaScope..."

if [ ! -f .env ]; then
    echo "❌ .env file not found"
    exit 1
fi

echo "📦 Building containers..."
docker-compose build

echo "🔄 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be ready (30 seconds)..."
sleep 30

echo "🗄️  Initializing database..."
docker-compose exec -T backend python3 -c "
from mediascope_api import init_db
init_db()
print('✅ Database initialized')
"

echo ""
echo "✅ MediaScope is running!"
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "📋 To process newspapers:"
echo "   docker-compose --profile processing up pipeline"
echo ""
echo "📊 View logs: docker-compose logs -f"
echo "🛑 Stop: docker-compose down"
EOF

chmod +x start.sh

cat > stop.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping MediaScope..."
docker-compose down
echo "✅ All services stopped"
EOF

chmod +x stop.sh

echo "✅ Docker setup complete!"
echo ""
echo "📁 Files created:"
ls -1 Dockerfile.* docker-compose.yml nginx.conf requirements.txt .env .dockerignore README_DOCKER.md start.sh stop.sh
echo ""
echo "🚀 To start MediaScope:"
echo "   ./start.sh"
echo ""
echo "Or manually:"
echo "   docker-compose up -d"
echo "   docker-compose exec backend python3 -c 'from mediascope_api import init_db; init_db()'"
