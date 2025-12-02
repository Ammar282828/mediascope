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
