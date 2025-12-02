# MediaScope System Architecture Diagram

## High-Level Architecture

```mermaid
graph TB
    subgraph "User Interface Layer"
        UI[React Dashboard<br/>Port 3000]
        Mobile[Mobile Browser]
        Desktop[Desktop Browser]
    end

    subgraph "API Layer"
        API[FastAPI Backend<br/>Port 8000]
        Auth[JWT Authentication]
        Search[Search Service]
        Analytics[Analytics Service]
    end

    subgraph "Data Storage Layer"
        PG[(PostgreSQL<br/>Port 5432)]
        ES[(Elasticsearch<br/>Port 9200)]
        Redis[(Redis Cache<br/>Port 6379)]
    end

    subgraph "Processing Pipeline"
        OCR[Gemini OCR]
        NER[spaCy NER]
        Sentiment[RoBERTa Sentiment]
        Topics[BERTopic]
    end

    subgraph "External Services"
        GeminiAPI[Google Gemini API]
    end

    Mobile --> UI
    Desktop --> UI
    UI --> API
    API --> Auth
    API --> Search
    API --> Analytics
    
    Search --> PG
    Search --> ES
    Search --> Redis
    
    Analytics --> PG
    Analytics --> Redis
    
    OCR --> GeminiAPI
    OCR --> NER
    NER --> Sentiment
    Sentiment --> Topics
    Topics --> PG
    Topics --> ES

    style UI fill:#4f46e5,color:#fff
    style API fill:#10b981,color:#fff
    style PG fill:#2563eb,color:#fff
    style ES fill:#f59e0b,color:#fff
    style OCR fill:#ec4899,color:#fff
```

## Data Flow

```mermaid
flowchart LR
    A[Newspaper Scan] --> B[Image Preprocessing]
    B --> C[Gemini OCR]
    C --> D[Article Extraction]
    D --> E[Named Entity<br/>Recognition]
    E --> F[Sentiment<br/>Analysis]
    F --> G[Topic<br/>Modeling]
    G --> H[PostgreSQL]
    G --> I[Elasticsearch]
    H --> J[FastAPI]
    I --> J
    J --> K[React<br/>Dashboard]

    style A fill:#f3f4f6,stroke:#d1d5db
    style C fill:#ec4899,color:#fff
    style E fill:#8b5cf6,color:#fff
    style F fill:#10b981,color:#fff
    style G fill:#f59e0b,color:#fff
    style H fill:#2563eb,color:#fff
    style I fill:#f59e0b,color:#fff
    style J fill:#10b981,color:#fff
    style K fill:#4f46e5,color:#fff
```

## Component Interaction

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant DB as PostgreSQL
    participant ES as Elasticsearch

    U->>F: Search "politics"
    F->>A: POST /api/search/keyword
    A->>ES: Full-text search query
    ES-->>A: Matching article IDs
    A->>DB: Get article details
    DB-->>A: Article data
    A->>DB: Get entities for articles
    DB-->>A: Entity data
    A-->>F: JSON response
    F-->>U: Display results
```

## Database Schema Overview

```mermaid
erDiagram
    NEWSPAPERS ||--o{ ARTICLES : contains
    NEWSPAPERS ||--o{ ADVERTISEMENTS : contains
    ARTICLES ||--o{ ENTITIES : mentions
    ARTICLES }o--|| TOPICS : belongs_to
    USERS ||--o{ COLLECTIONS : creates
    COLLECTIONS ||--o{ COLLECTION_ITEMS : contains
    COLLECTION_ITEMS }o--|| ARTICLES : references

    NEWSPAPERS {
        uuid id PK
        date publication_date
        int page_number
        string section
        string image_path
    }

    ARTICLES {
        uuid id PK
        uuid newspaper_id FK
        string headline
        text content
        float sentiment_score
        string sentiment_label
        int topic_id FK
    }

    ENTITIES {
        uuid id PK
        uuid article_id FK
        string entity_text
        string entity_type
    }

    TOPICS {
        int topic_id PK
        string topic_name
        array keywords
        int article_count
    }

    USERS {
        uuid id PK
        string username
        string email
        string password_hash
    }

    COLLECTIONS {
        uuid id PK
        uuid user_id FK
        string name
        text description
    }

    ADVERTISEMENTS {
        uuid id PK
        uuid newspaper_id FK
        jsonb bounding_box
        string industry_category
        string brand_name
    }
```

## Processing Pipeline Detail

```mermaid
flowchart TD
    Start([Newspaper Image]) --> Load[Load Image]
    Load --> Enhance[Image Enhancement<br/>Contrast, Sharpness]
    Enhance --> Orient[Check Orientation]
    Orient --> Meta[Extract Metadata<br/>Date, Page Number]
    Meta --> OCR[Gemini OCR]
    
    OCR --> Parse[Parse Articles]
    Parse --> Loop{For Each Article}
    
    Loop --> NER[spaCy NER<br/>Extract Entities]
    NER --> Sent[RoBERTa<br/>Sentiment Analysis]
    Sent --> Store[Store in PostgreSQL]
    Store --> Index[Index in<br/>Elasticsearch]
    
    Index --> Next{More Articles?}
    Next -->|Yes| Loop
    Next -->|No| Topic[BERTopic<br/>Batch Topic Modeling]
    
    Topic --> Update[Update Topic IDs]
    Update --> Done([Complete])

    style Start fill:#f3f4f6,stroke:#d1d5db
    style OCR fill:#ec4899,color:#fff
    style NER fill:#8b5cf6,color:#fff
    style Sent fill:#10b981,color:#fff
    style Topic fill:#f59e0b,color:#fff
    style Done fill:#2563eb,color:#fff
```

## API Endpoint Structure

```mermaid
mindmap
  root((MediaScope API))
    Authentication
      POST /auth/register
      POST /auth/login
    Search
      POST /search/keyword
      POST /search/entity
      GET /search/topics
    Analytics
      POST /analytics/keyword-trend
      GET /analytics/entity-trend
      POST /analytics/topic-distribution
      GET /analytics/sentiment-overview
      GET /analytics/top-entities
    Articles
      GET /articles/{id}
      GET /articles
    Health
      GET /health
      GET /
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Docker Host"
        subgraph "Frontend Container"
            React[React App<br/>nginx:3000]
        end
        
        subgraph "Backend Container"
            FastAPI[FastAPI<br/>uvicorn:8000]
        end
        
        subgraph "Database Container"
            Postgres[(PostgreSQL<br/>:5432)]
        end
        
        subgraph "Search Container"
            Elastic[(Elasticsearch<br/>:9200)]
        end
        
        subgraph "Cache Container"
            RedisC[(Redis<br/>:6379)]
        end
    end

    Client[Web Browser] --> React
    React --> FastAPI
    FastAPI --> Postgres
    FastAPI --> Elastic
    FastAPI --> RedisC

    style React fill:#4f46e5,color:#fff
    style FastAPI fill:#10b981,color:#fff
    style Postgres fill:#2563eb,color:#fff
    style Elastic fill:#f59e0b,color:#fff
    style RedisC fill:#dc2626,color:#fff
```

## Technology Stack Layers

```mermaid
graph TD
    subgraph "Presentation Layer"
        A1[React 18]
        A2[TypeScript]
        A3[Recharts]
        A4[Axios]
    end

    subgraph "Application Layer"
        B1[FastAPI]
        B2[Pydantic]
        B3[JWT Auth]
        B4[CORS]
    end

    subgraph "Business Logic Layer"
        C1[Search Service]
        C2[Analytics Service]
        C3[Auth Service]
    end

    subgraph "Data Access Layer"
        D1[SQLAlchemy]
        D2[psycopg2]
        D3[Elasticsearch Client]
    end

    subgraph "ML/AI Layer"
        E1[Gemini API]
        E2[spaCy]
        E3[Transformers]
        E4[BERTopic]
    end

    subgraph "Data Layer"
        F1[(PostgreSQL)]
        F2[(Elasticsearch)]
        F3[(Redis)]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B1
    A4 --> B1

    B1 --> C1
    B1 --> C2
    B1 --> C3

    C1 --> D1
    C2 --> D2
    C3 --> D3

    D1 --> F1
    D2 --> F1
    D3 --> F2

    E1 --> F1
    E2 --> F1
    E3 --> F1
    E4 --> F1
```

---

## How to Use These Diagrams

### In Documentation
Copy the Mermaid code blocks into:
- README.md
- Technical specifications
- Presentation slides (many tools support Mermaid)
- GitHub (renders Mermaid natively)

### Tools that Support Mermaid
- GitHub/GitLab markdown
- VS Code (with Mermaid extension)
- Notion
- Obsidian
- Confluence (with plugin)
- Draw.io (can import)

### Export Options
Use https://mermaid.live to:
- View and edit diagrams
- Export as PNG/SVG
- Share with team

---

These diagrams provide a complete visual understanding of:
✅ System architecture
✅ Data flow
✅ Component interaction
✅ Database relationships
✅ Processing pipeline
✅ API structure
✅ Deployment setup
✅ Technology layers
