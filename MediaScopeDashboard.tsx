// MediaScope Dashboard - Main Component
// React TypeScript with Recharts for visualization

import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import axios from 'axios';

// ============================================
// TYPES
// ============================================

interface Article {
  id: string;
  headline: string;
  content: string;
  publication_date: string;
  sentiment_score: number;
  sentiment_label: string;
  topic_label: string;
  entities: Array<{text: string; type: string}>;
}

interface TrendData {
  date: string;
  count: number;
}

interface EntityTrend {
  date: string;
  mentions: number;
  avg_sentiment: number;
}

interface TopicDist {
  topic_name: string;
  article_count: number;
  percentage: number;
}

// ============================================
// API SERVICE
// ============================================

const API_BASE = 'http://localhost:8000/api';

const api = {
  // Search
  searchKeyword: async (query: string, filters?: any) => {
    const response = await axios.post(`${API_BASE}/search/keyword`, {
      query,
      ...filters,
      limit: 20
    });
    return response.data;
  },

  searchEntity: async (entityName: string, filters?: any) => {
    const response = await axios.post(`${API_BASE}/search/entity`, {
      entity_name: entityName,
      ...filters,
      limit: 20
    });
    return response.data;
  },

  // Analytics
  getKeywordTrend: async (keywords: string[], startDate: string, endDate: string) => {
    const response = await axios.post(`${API_BASE}/analytics/keyword-trend`, {
      keywords,
      start_date: startDate,
      end_date: endDate,
      granularity: 'day'
    });
    return response.data;
  },

  getEntityTrend: async (entity: string, startDate: string, endDate: string) => {
    const response = await axios.get(`${API_BASE}/analytics/entity-trend`, {
      params: {
        entity_name: entity,
        start_date: startDate,
        end_date: endDate
      }
    });
    return response.data;
  },

  getTopicDistribution: async (startDate: string, endDate: string) => {
    const response = await axios.post(`${API_BASE}/analytics/topic-distribution`, {
      start_date: startDate,
      end_date: endDate
    });
    return response.data;
  },

  getTopEntities: async (type?: string, limit = 10) => {
    const response = await axios.get(`${API_BASE}/analytics/top-entities`, {
      params: { entity_type: type, limit }
    });
    return response.data;
  },

  getSentimentOverview: async (startDate: string, endDate: string) => {
    const response = await axios.get(`${API_BASE}/analytics/sentiment-overview`, {
      params: {
        start_date: startDate,
        end_date: endDate
      }
    });
    return response.data;
  }
};

// ============================================
// SEARCH COMPONENT
// ============================================

const SearchPanel: React.FC<{
  onResults: (results: any) => void;
}> = ({ onResults }) => {
  const [searchType, setSearchType] = useState<'keyword' | 'entity'>('keyword');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      if (searchType === 'keyword') {
        const data = await api.searchKeyword(query);
        onResults(data);
      } else {
        const data = await api.searchEntity(query);
        onResults(data);
      }
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="search-panel">
      <div className="search-header">
        <h2>Search Dawn Archives (1990-1992)</h2>
        <div className="search-type-tabs">
          <button
            className={searchType === 'keyword' ? 'active' : ''}
            onClick={() => setSearchType('keyword')}
          >
            Keyword Search
          </button>
          <button
            className={searchType === 'entity' ? 'active' : ''}
            onClick={() => setSearchType('entity')}
          >
            Entity Search
          </button>
        </div>
      </div>

      <div className="search-input-group">
        <input
          type="text"
          placeholder={
            searchType === 'keyword'
              ? 'Search articles by keyword...'
              : 'Search by person, organization, or location...'
          }
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          className="search-input"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="search-button"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>
    </div>
  );
};

// ============================================
// ARTICLE LIST COMPONENT
// ============================================

const ArticleList: React.FC<{
  articles: Article[];
}> = ({ articles }) => {
  const getSentimentColor = (label: string) => {
    switch (label) {
      case 'positive': return '#10b981';
      case 'negative': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getSentimentEmoji = (label: string) => {
    switch (label) {
      case 'positive': return '😊';
      case 'negative': return '😞';
      default: return '😐';
    }
  };

  return (
    <div className="article-list">
      {articles.map((article) => (
        <div key={article.id} className="article-card">
          <div className="article-header">
            <h3 className="article-headline">{article.headline}</h3>
            <span className="article-date">
              {new Date(article.publication_date).toLocaleDateString()}
            </span>
          </div>

          <div className="article-content-preview">
            {article.content.substring(0, 300)}...
          </div>

          <div className="article-meta">
            <div
              className="sentiment-badge"
              style={{ backgroundColor: getSentimentColor(article.sentiment_label) }}
            >
              {getSentimentEmoji(article.sentiment_label)} {article.sentiment_label}
              <span className="sentiment-score">
                ({article.sentiment_score?.toFixed(2)})
              </span>
            </div>

            {article.topic_label && (
              <div className="topic-badge">
                📚 {article.topic_label}
              </div>
            )}

            {article.entities && article.entities.length > 0 && (
              <div className="entities-list">
                {article.entities.slice(0, 3).map((entity, idx) => (
                  <span key={idx} className="entity-tag">
                    {entity.type}: {entity.text}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

// ============================================
// KEYWORD TREND CHART
// ============================================

const KeywordTrendChart: React.FC = () => {
  const [keywords, setKeywords] = useState<string[]>(['politics']);
  const [newKeyword, setNewKeyword] = useState('');
  const [trendData, setTrendData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadTrend = async () => {
    if (keywords.length === 0) return;

    setLoading(true);
    try {
      const data = await api.getKeywordTrend(
        keywords,
        '1990-01-01',
        '1992-12-31'
      );

      // Transform data for Recharts
      const dates = new Set<string>();
      Object.values(data.trends).forEach((trend: any) => {
        trend.forEach((point: TrendData) => dates.add(point.date));
      });

      const chartData = Array.from(dates).sort().map(date => {
        const point: any = { date };
        keywords.forEach(keyword => {
          const keywordData = data.trends[keyword];
          const match = keywordData.find((d: TrendData) => d.date === date);
          point[keyword] = match ? match.count : 0;
        });
        return point;
      });

      setTrendData(chartData);
    } catch (error) {
      console.error('Error loading trend:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrend();
  }, [keywords]);

  const addKeyword = () => {
    if (newKeyword.trim() && !keywords.includes(newKeyword.trim())) {
      setKeywords([...keywords, newKeyword.trim()]);
      setNewKeyword('');
    }
  };

  const removeKeyword = (keyword: string) => {
    setKeywords(keywords.filter(k => k !== keyword));
  };

  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1'];

  return (
    <div className="trend-chart-panel">
      <h3>Keyword Frequency Trends</h3>

      <div className="keyword-controls">
        <div className="keyword-input-group">
          <input
            type="text"
            placeholder="Add keyword to track..."
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
          />
          <button onClick={addKeyword}>Add</button>
        </div>

        <div className="keyword-tags">
          {keywords.map((keyword, idx) => (
            <span key={keyword} className="keyword-tag">
              {keyword}
              <button onClick={() => removeKeyword(keyword)}>×</button>
            </span>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="loading-spinner">Loading trend data...</div>
      ) : (
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', {
                month: 'short',
                year: '2-digit'
              })}
            />
            <YAxis label={{ value: 'Mentions', angle: -90, position: 'insideLeft' }} />
            <Tooltip
              labelFormatter={(date) => new Date(date).toLocaleDateString()}
            />
            <Legend />
            {keywords.map((keyword, idx) => (
              <Line
                key={keyword}
                type="monotone"
                dataKey={keyword}
                stroke={COLORS[idx % COLORS.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

// ============================================
// TOP ENTITIES COMPONENT
// ============================================

const TopEntitiesPanel: React.FC = () => {
  const [entityType, setEntityType] = useState<string>('');
  const [entities, setEntities] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTopEntities();
  }, [entityType]);

  const loadTopEntities = async () => {
    setLoading(true);
    try {
      const data = await api.getTopEntities(entityType || undefined, 10);
      setEntities(data.entities);
    } catch (error) {
      console.error('Error loading entities:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="top-entities-panel">
      <div className="panel-header">
        <h3>Most Mentioned Entities</h3>
        <select
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
          className="entity-type-select"
        >
          <option value="">All Types</option>
          <option value="PERSON">People</option>
          <option value="ORG">Organizations</option>
          <option value="GPE">Locations</option>
        </select>
      </div>

      {loading ? (
        <div className="loading">Loading...</div>
      ) : (
        <div className="entities-list-panel">
          {entities.map((entity, idx) => (
            <div key={idx} className="entity-item">
              <div className="entity-rank">{idx + 1}</div>
              <div className="entity-info">
                <div className="entity-name">{entity.text}</div>
                <div className="entity-type-badge">{entity.type}</div>
              </div>
              <div className="entity-stats">
                <div className="mention-count">{entity.mentions} mentions</div>
                <div
                  className="sentiment-indicator"
                  style={{
                    color: entity.avg_sentiment > 0 ? '#10b981' :
                           entity.avg_sentiment < 0 ? '#ef4444' : '#6b7280'
                  }}
                >
                  Sentiment: {entity.avg_sentiment.toFixed(2)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ============================================
// SENTIMENT DISTRIBUTION COMPONENT
// ============================================

const SentimentDistribution: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSentimentData();
  }, []);

  const loadSentimentData = async () => {
    setLoading(true);
    try {
      const result = await api.getSentimentOverview('1990-01-01', '1992-12-31');
      setData(result);
    } catch (error) {
      console.error('Error loading sentiment data:', error);
    } finally {
      setLoading(false);
    }
  };

  const COLORS = {
    positive: '#10b981',
    neutral: '#6b7280',
    negative: '#ef4444'
  };

  if (loading || !data) return <div>Loading...</div>;

  return (
    <div className="sentiment-distribution-panel">
      <h3>Sentiment Distribution (1990-1992)</h3>
      <div className="sentiment-stats">
        <div className="total-articles">
          Total Articles: {data.total_articles}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data.sentiment_breakdown}
            dataKey="count"
            nameKey="label"
            cx="50%"
            cy="50%"
            outerRadius={100}
            label={(props: any) => `${props.name}: ${(props.percent * 100).toFixed(1)}%`}
          >
            {data.sentiment_breakdown.map((entry: any, index: number) => (
              <Cell key={`cell-${index}`} fill={COLORS[entry.label as keyof typeof COLORS]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>

      <div className="sentiment-breakdown-list">
        {data.sentiment_breakdown.map((item: any) => (
          <div key={item.label} className="sentiment-item">
            <div
              className="sentiment-color"
              style={{ backgroundColor: COLORS[item.label as keyof typeof COLORS] }}
            />
            <div className="sentiment-label">{item.label}</div>
            <div className="sentiment-count">{item.count} articles</div>
            <div className="sentiment-percentage">{item.percentage}%</div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================
// MAIN DASHBOARD COMPONENT
// ============================================

const MediaScopeDashboard: React.FC = () => {
  const [searchResults, setSearchResults] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'search' | 'trends' | 'analytics'>('search');

  return (
    <div className="mediascope-dashboard">
      <header className="dashboard-header">
        <div className="logo-section">
          <h1>📰 MediaScope</h1>
          <p className="tagline">Dawn Newspaper Archive (1990-1992)</p>
        </div>
        <nav className="dashboard-nav">
          <button
            className={activeTab === 'search' ? 'active' : ''}
            onClick={() => setActiveTab('search')}
          >
            🔍 Search
          </button>
          <button
            className={activeTab === 'trends' ? 'active' : ''}
            onClick={() => setActiveTab('trends')}
          >
            📈 Trends
          </button>
          <button
            className={activeTab === 'analytics' ? 'active' : ''}
            onClick={() => setActiveTab('analytics')}
          >
            📊 Analytics
          </button>
        </nav>
      </header>

      <main className="dashboard-main">
        {activeTab === 'search' && (
          <div className="search-view">
            <SearchPanel onResults={setSearchResults} />
            {searchResults && (
              <div className="search-results">
                <div className="results-header">
                  <h3>Found {searchResults.total} articles</h3>
                </div>
                <ArticleList articles={searchResults.articles || []} />
              </div>
            )}
          </div>
        )}

        {activeTab === 'trends' && (
          <div className="trends-view">
            <KeywordTrendChart />
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="analytics-view">
            <div className="analytics-grid">
              <div className="analytics-card">
                <TopEntitiesPanel />
              </div>
              <div className="analytics-card">
                <SentimentDistribution />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default MediaScopeDashboard;