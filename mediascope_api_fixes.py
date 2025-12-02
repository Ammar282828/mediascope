@app.get("/api/analytics/keyword-trend-fixed")
def get_keyword_trend_fixed():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count
            FROM articles
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        return {"trends": {"articles": [{"date": str(r['date']), "count": r['count']} for r in results]}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/sentiment-fixed")
def get_sentiment_fixed():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                sentiment_label,
                COUNT(*) as count
            FROM articles
            WHERE sentiment_label IS NOT NULL
            GROUP BY sentiment_label
        """)
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        sentiment_data = {"positive": 0, "neutral": 0, "negative": 0, "total": 0}
        for r in results:
            sentiment_data[r['sentiment_label']] = r['count']
            sentiment_data['total'] += r['count']
        
        return sentiment_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/top-entities-fixed")
def get_top_entities_fixed(entity_type: str = None, limit: int = 10):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                entity_text as text,
                entity_type as type,
                COUNT(*) as count
            FROM entities
        """
        
        params = []
        if entity_type:
            query += " WHERE entity_type = %s"
            params.append(entity_type)
        
        query += " GROUP BY entity_text, entity_type ORDER BY count DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        return {"entities": [dict(r) for r in results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
Articles:
{articles_text}

Provide a concise 200-word summary."""
        
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-3-pro-preview')
        response = model.generate_content(prompt)
        
        return {
            "summary": response.text,
            "article_count": len(articles),
            "date_range": f"{start_date} to {end_date}",
            "topic": topic
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

