-- MediaScope Minimal Schema - Quick Setup

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Newspapers
CREATE TABLE newspapers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    publication_date DATE NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    section VARCHAR(100),
    image_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(publication_date, page_number)
);

-- Articles
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    newspaper_id UUID REFERENCES newspapers(id) ON DELETE CASCADE,
    article_number INTEGER NOT NULL,
    headline TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    sentiment_score FLOAT,
    sentiment_label VARCHAR(20),
    topic_label VARCHAR(100),
    topic_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Entities
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    entity_text VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    start_char INTEGER,
    end_char INTEGER
);

-- Topics
CREATE TABLE topics (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER UNIQUE NOT NULL,
    topic_name VARCHAR(255) NOT NULL,
    keywords TEXT[],
    article_count INTEGER DEFAULT 0
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_newspapers_date ON newspapers(publication_date);
CREATE INDEX idx_articles_newspaper ON articles(newspaper_id);
CREATE INDEX idx_articles_sentiment ON articles(sentiment_score);
CREATE INDEX idx_entities_text ON entities(entity_text);
CREATE INDEX idx_entities_article ON entities(article_id);

-- Full-text search indexes
CREATE INDEX idx_articles_headline ON articles USING gin(to_tsvector('english', headline));
CREATE INDEX idx_articles_content ON articles USING gin(to_tsvector('english', content));
