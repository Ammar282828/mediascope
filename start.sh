#!/bin/bash

echo "🚀 Starting MediaScope..."

if [ ! -f .env ]; then
    echo "❌ .env file not found"
    exit 1
fi

echo "📦 Building containers..."
docker compose build

echo "🔄 Starting services..."
docker compose up -d

echo "⏳ Waiting for services to be ready (30 seconds)..."
sleep 30

echo "🗄️  Initializing database..."
docker compose exec -T backend python3 -c "
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
echo "   docker compose --profile processing up pipeline"
echo ""
echo "📊 View logs: docker compose logs -f"
echo "🛑 Stop: docker compose down"
