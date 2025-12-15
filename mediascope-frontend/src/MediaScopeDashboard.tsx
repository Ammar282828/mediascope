import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import SearchPanel from './components/SearchPanel';
import ArticleList from './components/ArticleList';
import SearchResultsSummary from './components/SearchResultsSummary';
import { ArticlesOverTime, SentimentOverTime, TopKeywordsCloud } from './components/AnalyticsCharts';
import {
  AnalyticsSummary,
  SentimentDistribution,
  TopicDistribution,
  EntityCooccurrenceNetwork,
  EntityTimeline,
  ArticleLengthDistribution,
  CoverageHeatmap
} from './components/EnhancedAnalytics';
import ImageAnalysisTab from './components/ImageAnalysisTab';
import OCRTab from './components/OCRTab';
import SentimentByEntityChart from './components/SentimentByEntityChart';
import NewspaperBrowser from './components/NewspaperBrowser';
import { API_BASE } from './config';

interface TrendData {
  date: string;
  count: number;
}

const api = {
  getKeywordTrend: async (keywords: string[], startDate: string, endDate: string) => {
    const response = await axios.post(`${API_BASE}/analytics/keyword-trend`, {
      keywords,
      start_date: startDate,
      end_date: endDate,
      granularity: 'day'
    });
    return response.data;
  },
  
  getTopEntities: async (type?: string, limit = 10) => {
    const response = await axios.get(`${API_BASE}/analytics/top-entities-fixed`, {
      params: { entity_type: type, limit }
    });
    return response.data;
  },
  
  getSentimentOverview: async () => {
    const response = await axios.get(`${API_BASE}/analytics/sentiment-fixed`);
    return response.data;
  },
  
  generateAISummary: async (startDate: string, endDate: string, topic?: string) => {
    const response = await axios.post(`${API_BASE}/analytics/ai-summary`, {
      start_date: startDate,
      end_date: endDate,
      topic
    });
    return response.data;
  }
};

const KeywordTrendChart: React.FC = () => {
  const [keywords, setKeywords] = useState<string[]>(['karachi']);
  const [newKeyword, setNewKeyword] = useState('');
  const [trendData, setTrendData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadTrend = async () => {
    if (keywords.length === 0) return;

    setLoading(true);
    try {
      const data = await api.getKeywordTrend(keywords, '1990-01-01', '1992-12-31');
      
      const dates = new Set<string>();
      if (data.trends) {
        Object.values(data.trends).forEach((trend: any) => {
          if (Array.isArray(trend)) {
            trend.forEach((point: TrendData) => dates.add(point.date));
          }
        });
      }

      const chartData = Array.from(dates).sort().map(date => {
        const point: any = { date: new Date(date).toLocaleDateString() };
        keywords.forEach(kw => {
          const trend = data.trends?.[kw] || [];
          const match = Array.isArray(trend) ? trend.find((p: TrendData) => p.date === date) : null;
          point[kw] = match ? match.count : 0;
        });
        return point;
      });

      setTrendData(chartData);
    } catch (error) {
      console.error('Error loading trends:', error);
      setTrendData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrend();
  }, [keywords]);

  const addKeyword = () => {
    if (newKeyword && !keywords.includes(newKeyword.toLowerCase())) {
      setKeywords([...keywords, newKeyword.toLowerCase()]);
      setNewKeyword('');
    }
  };

  const removeKeyword = (kw: string) => {
    if (keywords.length > 1) {
      setKeywords(keywords.filter(k => k !== kw));
    }
  };

  const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'];

  return (
    <div className="trend-chart-panel">
      <h2>Keyword Trends Over Time</h2>
      
      <div className="keyword-input-group">
        <input
          type="text"
          placeholder="Add keyword to track..."
          value={newKeyword}
          onChange={(e) => setNewKeyword(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
        />
        <button onClick={addKeyword} className="add-button">+ Add Keyword</button>
      </div>

      <div className="active-keywords">
        {keywords.map((kw, idx) => (
          <span key={kw} className="keyword-badge" style={{ backgroundColor: colors[idx % colors.length] }}>
            {kw}
            {keywords.length > 1 && <button onClick={() => removeKeyword(kw)}>×</button>}
          </span>
        ))}
      </div>

      {loading ? (
        <p>Loading trends...</p>
      ) : trendData.length > 0 ? (
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            {keywords.map((kw, idx) => (
              <Line
                key={kw}
                type="monotone"
                dataKey={kw}
                stroke={colors[idx % colors.length]}
                strokeWidth={2}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div style={{ padding: '40px', textAlign: 'center', color: '#6b7280' }}>
          No trend data available
        </div>
      )}
    </div>
  );
};

const AISummaryPanel: React.FC = () => {
  const [startDate, setStartDate] = useState('1990-01-01');
  const [endDate, setEndDate] = useState('1992-12-31');
  const [topic, setTopic] = useState('');
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const generateSummary = async () => {
    setLoading(true);
    setSummary(null);

    try {
      const data = await api.generateAISummary(startDate, endDate, topic || undefined);
      setSummary(data);
    } catch (error) {
      console.error('Failed to generate summary:', error);
      setSummary({ error: 'Failed to generate summary.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-summary-panel">
      <h2>AI-Powered Summary</h2>

      <div className="summary-controls">
        <div className="date-inputs">
          <label>
            Start Date:
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </label>
          <label>
            End Date:
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </label>
        </div>

        <div className="topic-input">
          <label>
            Topic (optional):
            <input
              type="text"
              placeholder="e.g., politics"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />
          </label>
        </div>

        <button onClick={generateSummary} disabled={loading} className="generate-button">
          {loading ? 'Generating...' : 'Generate Summary'}
        </button>
      </div>

      {summary && !summary.error && (
        <div className="summary-result">
          <div className="summary-meta">
            <div><strong>Period:</strong> {summary.date_range}</div>
            <div><strong>Articles:</strong> {summary.article_count}</div>
          </div>
          <div className="summary-text">
            <h3>Summary:</h3>
            <p style={{ whiteSpace: 'pre-wrap', lineHeight: '1.8' }}>{summary.summary}</p>
          </div>
        </div>
      )}

      {summary && summary.error && (
        <div className="summary-error">[ERROR] {summary.error}</div>
      )}
    </div>
  );
};

const TopEntitiesPanel: React.FC = () => {
  const [entityType, setEntityType] = useState<string>('');
  const [entities, setEntities] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadTopEntities = async () => {
    setLoading(true);
    try {
      const data = await api.getTopEntities(entityType || undefined, 15);
      setEntities(data.entities || []);
    } catch (error) {
      console.error('Error loading entities:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTopEntities();
  }, [entityType]);

  return (
    <div className="top-entities-panel">
      <h3>Top Entities</h3>
      <p style={{ fontSize: '13px', color: '#6b7280', margin: '8px 0 16px 0' }}>
        Most frequently mentioned people, organizations, and locations across all articles
      </p>

      <select value={entityType} onChange={(e) => setEntityType(e.target.value)} className="entity-type-select">
        <option value="">All Types</option>
        <option value="PERSON">People</option>
        <option value="ORG">Organizations</option>
        <option value="GPE">Locations</option>
      </select>

      {loading ? (
        <p>Loading...</p>
      ) : entities.length > 0 ? (
        <div className="entities-grid">
          {entities.map((entity, idx) => (
            <div key={idx} className="entity-item">
              <div className="entity-rank">#{idx + 1}</div>
              <div className="entity-info">
                <div className="entity-name">
                  {entity.text}
                </div>
                <div className="entity-type-label">{entity.type}</div>
              </div>
              <div className="entity-count">{entity.count}</div>
            </div>
          ))}
        </div>
      ) : (
        <p>No entities found</p>
      )}
    </div>
  );
};

const EntityCooccurrence: React.FC = () => {
  const [entityType, setEntityType] = useState<string>('');
  const [cooccurrences, setCooccurrences] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadCooccurrences = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/analytics/entity-cooccurrence`, {
        params: {
          entity_type: entityType || undefined,
          min_count: 3,
          limit: 30
        }
      });
      setCooccurrences(response.data.pairs || []);
    } catch (error) {
      console.error('Error loading entity co-occurrences:', error);
      setCooccurrences([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCooccurrences();
  }, [entityType]);

  return (
    <div className="entity-cooccurrence">
      <h3>Entity Co-occurrence</h3>
      <p className="subtitle">Entities that frequently appear together in articles</p>

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

      {loading ? (
        <p>Loading...</p>
      ) : cooccurrences.length > 0 ? (
        <div className="cooccurrence-list">
          {cooccurrences.map((pair, idx) => (
            <div key={idx} className="cooccurrence-item">
              <div className="cooccurrence-rank">#{idx + 1}</div>
              <div className="cooccurrence-entities">
                <span className="entity">{pair.entity1}</span>
                <span className="connector">+</span>
                <span className="entity">{pair.entity2}</span>
              </div>
              <div className="cooccurrence-count">
                {pair.cooccurrence_count} {pair.cooccurrence_count === 1 ? 'article' : 'articles'}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p>No co-occurrences found</p>
      )}
    </div>
  );
};

const MediaScopeDashboard: React.FC = () => {
  const [searchResults, setSearchResults] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'search' | 'analytics' | 'pages' | 'image-analysis' | 'ocr'>('search');
  const [analyticsSubTab, setAnalyticsSubTab] = useState<'overview' | 'temporal' | 'entities' | 'topics'>('overview');
  const [searchFilters, setSearchFilters] = useState<any>(null);

  useEffect(() => {
    const loadArticles = async () => {
      try {
        const response = await axios.get(`${API_BASE}/articles`);
        setSearchResults({
          total: response.data.articles.length,
          articles: response.data.articles
        });
      } catch (error) {
        console.error('Failed to load articles:', error);
      }
    };
    loadArticles();
  }, []);

  return (
    <div className="mediascope-dashboard">
      <header className="dashboard-header">
        <div className="logo-section">
          <h1>MediaScope</h1>
          <p className="tagline">Dawn Newspaper Archive (1990-1992)</p>
        </div>
        <nav className="dashboard-nav">
          <button
            className={activeTab === 'search' ? 'active' : ''}
            onClick={() => setActiveTab('search')}
          >
            Search
          </button>
          <button
            className={activeTab === 'analytics' ? 'active' : ''}
            onClick={() => setActiveTab('analytics')}
          >
            Analytics
          </button>
          <button
            className={activeTab === 'pages' ? 'active' : ''}
            onClick={() => setActiveTab('pages')}
          >
            Pages
          </button>
          <button
            className={activeTab === 'image-analysis' ? 'active' : ''}
            onClick={() => setActiveTab('image-analysis')}
          >
            Ad Analysis <span style={{fontSize: '0.7em', opacity: 0.8}}>(Beta)</span>
          </button>
          <button
            className={activeTab === 'ocr' ? 'active' : ''}
            onClick={() => setActiveTab('ocr')}
          >
            OCR
          </button>
        </nav>
      </header>

      <main className="dashboard-main">
        {activeTab === 'search' && (
          <div className="search-view">
            <SearchPanel
              onResults={setSearchResults}
              onFiltersChange={setSearchFilters}
            />
            {searchResults && (
              <div className="search-results">
                <SearchResultsSummary
                  totalResults={searchResults.total}
                  filters={searchFilters}
                />
                <ArticleList articles={searchResults.articles || []} />
              </div>
            )}
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="analytics-view">
            {/* Summary Cards */}
            <AnalyticsSummary />

            {/* Sub-navigation */}
            <div className="analytics-tab-nav">
              <button
                className={`analytics-tab-button ${analyticsSubTab === 'overview' ? 'active' : ''}`}
                onClick={() => setAnalyticsSubTab('overview')}
              >
                📊 Overview
              </button>
              <button
                className={`analytics-tab-button ${analyticsSubTab === 'temporal' ? 'active' : ''}`}
                onClick={() => setAnalyticsSubTab('temporal')}
              >
                📈 Trends Over Time
              </button>
              <button
                className={`analytics-tab-button ${analyticsSubTab === 'entities' ? 'active' : ''}`}
                onClick={() => setAnalyticsSubTab('entities')}
              >
                🏷️ Entities & Relationships
              </button>
              <button
                className={`analytics-tab-button ${analyticsSubTab === 'topics' ? 'active' : ''}`}
                onClick={() => setAnalyticsSubTab('topics')}
              >
                💡 Topics & Keywords
              </button>
            </div>

            {/* Content for each sub-tab */}
            <div className="analytics-tab-content">
              {analyticsSubTab === 'overview' && (
                <div className="analytics-section">
                  <h2 className="analytics-section-title">Archive Overview</h2>
                  <p className="analytics-section-subtitle">
                    High-level statistics and sentiment breakdown of the entire newspaper archive
                  </p>

                  <div className="analytics-grid">
                    <div className="analytics-card">
                      <SentimentDistribution />
                    </div>
                    <div className="analytics-card">
                      <ArticleLengthDistribution />
                    </div>
                  </div>

                  <div className="analytics-grid">
                    <div className="analytics-card">
                      <TopicDistribution />
                    </div>
                    <div className="analytics-card">
                      <KeywordTrendChart />
                    </div>
                  </div>
                </div>
              )}

              {analyticsSubTab === 'temporal' && (
                <div className="analytics-section">
                  <h2 className="analytics-section-title">Temporal Analysis</h2>
                  <p className="analytics-section-subtitle">
                    How coverage, sentiment, and topics evolved over time
                  </p>

                  <div className="analytics-card full-width">
                    <CoverageHeatmap />
                  </div>

                  <div className="analytics-grid">
                    <div className="analytics-card">
                      <ArticlesOverTime />
                    </div>
                    <div className="analytics-card">
                      <SentimentOverTime />
                    </div>
                  </div>
                </div>
              )}

              {analyticsSubTab === 'entities' && (
                <div className="analytics-section">
                  <h2 className="analytics-section-title">Entity Analysis</h2>
                  <p className="analytics-section-subtitle">
                    People, organizations, and locations mentioned in the archive
                  </p>

                  <div className="analytics-card full-width">
                    <EntityTimeline />
                  </div>

                  <div className="analytics-card full-width">
                    <SentimentByEntityChart />
                  </div>

                  <div className="analytics-card full-width">
                    <EntityCooccurrenceNetwork />
                  </div>
                </div>
              )}

              {analyticsSubTab === 'topics' && (
                <div className="analytics-section">
                  <h2 className="analytics-section-title">Topics & Keywords</h2>
                  <p className="analytics-section-subtitle">
                    Main themes, topics, and frequently mentioned terms
                  </p>

                  <div className="analytics-grid">
                    <div className="analytics-card">
                      <TopEntitiesPanel />
                    </div>
                    <div className="analytics-card">
                      <TopKeywordsCloud />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'pages' && <NewspaperBrowser />}

        {activeTab === 'image-analysis' && <ImageAnalysisTab />}

        {activeTab === 'ocr' && <OCRTab />}
      </main>
    </div>
  );
};

export default MediaScopeDashboard;
