import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, LineChart, Line
} from 'recharts';

// Summary Cards Component
export const AnalyticsSummary: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [articlesRes, sentimentRes, entitiesRes] = await Promise.all([
          axios.get(`${API_BASE}/analytics/articles-over-time`),
          axios.get(`${API_BASE}/analytics/sentiment-over-time`),
          axios.get(`${API_BASE}/analytics/top-entities-fixed?limit=1`)
        ]);

        const articles = articlesRes.data.timeline || [];
        const sentiment = sentimentRes.data.timeline || [];

        const totalArticles = articles.reduce((sum: number, item: any) => sum + item.count, 0);

        // Calculate overall sentiment
        let totalPos = 0, totalNeut = 0, totalNeg = 0;
        sentiment.forEach((item: any) => {
          totalPos += item.positive || 0;
          totalNeut += item.neutral || 0;
          totalNeg += item.negative || 0;
        });
        const total = totalPos + totalNeut + totalNeg;
        const avgSentiment = total > 0 ? ((totalPos - totalNeg) / total).toFixed(2) : '0.00';

        // Date range
        const months = articles.map((a: any) => a.month).sort();
        const dateRange = months.length > 0 ? `${months[0]} to ${months[months.length - 1]}` : 'N/A';

        setStats({
          totalArticles,
          avgSentiment,
          dateRange,
          topEntitiesCount: entitiesRes.data.entities?.length || 0
        });
      } catch (error) {
        console.error('Failed to load summary stats:', error);
      } finally {
        setLoading(false);
      }
    };
    loadStats();
  }, []);

  if (loading) return <div>Loading summary...</div>;
  if (!stats) return null;

  return (
    <div className="analytics-summary">
      <div className="summary-card">
        <div className="summary-label">Total Articles</div>
        <div className="summary-value">{stats.totalArticles.toLocaleString()}</div>
      </div>
      <div className="summary-card">
        <div className="summary-label">Date Range</div>
        <div className="summary-value small">{stats.dateRange}</div>
      </div>
      <div className="summary-card">
        <div className="summary-label">Avg Sentiment</div>
        <div className="summary-value" style={{
          color: parseFloat(stats.avgSentiment) > 0.1 ? '#10b981' :
                 parseFloat(stats.avgSentiment) < -0.1 ? '#ef4444' : '#6b7280'
        }}>
          {parseFloat(stats.avgSentiment) > 0 ? '+' : ''}{stats.avgSentiment}
        </div>
      </div>
    </div>
  );
};

// Sentiment Distribution Pie Chart
export const SentimentDistribution: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await axios.get(`${API_BASE}/analytics/sentiment-over-time`);
        const timeline = response.data.timeline || [];

        let positive = 0, neutral = 0, negative = 0;
        timeline.forEach((item: any) => {
          positive += item.positive || 0;
          neutral += item.neutral || 0;
          negative += item.negative || 0;
        });

        const total = positive + neutral + negative;
        setData([
          { name: 'Positive', value: positive, percentage: ((positive / total) * 100).toFixed(1) },
          { name: 'Neutral', value: neutral, percentage: ((neutral / total) * 100).toFixed(1) },
          { name: 'Negative', value: negative, percentage: ((negative / total) * 100).toFixed(1) }
        ]);
      } catch (error) {
        console.error('Failed to load sentiment distribution:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const COLORS = ['#10b981', '#6b7280', '#ef4444'];

  if (loading) return <p>Loading...</p>;
  if (data.length === 0) return <p>No data available</p>;

  return (
    <div>
      <h3>Overall Sentiment Distribution</h3>
      <p style={{ fontSize: '13px', color: '#6b7280', margin: '8px 0 16px 0' }}>
        Breakdown of positive, neutral, and negative articles across the entire archive
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={(entry) => `${entry.name}: ${entry.percentage}%`}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

// Topic Distribution Chart
export const TopicDistribution: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await axios.get(`${API_BASE}/analytics/topic-distribution`);
        setData(response.data.topics || []);
      } catch (error) {
        console.error('Failed to load topic distribution:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) return <p>Loading...</p>;
  if (data.length === 0) return <p>No topics available. Train topic model first.</p>;

  return (
    <div>
      <h3>Topic Distribution</h3>
      <p style={{ fontSize: '13px', color: '#6b7280', margin: '8px 0 16px 0' }}>
        Main themes and topics discovered across all articles
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data.slice(0, 10)}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="topic"
            angle={-45}
            textAnchor="end"
            height={100}
            interval={0}
          />
          <YAxis />
          <Tooltip />
          <Bar dataKey="count" fill="#8b5cf6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// Enhanced Entity Co-occurrence with Network Visualization
export const EntityCooccurrenceNetwork: React.FC = () => {
  const [entityType, setEntityType] = useState<string>('');
  const [cooccurrences, setCooccurrences] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadCooccurrences = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/analytics/entity-cooccurrence`, {
        params: {
          entity_type: entityType || undefined,
          min_count: 2,  // Lower threshold for more connections
          limit: 20
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
    <div className="entity-cooccurrence-network">
      <h3>Entity Relationships</h3>
      <p style={{ fontSize: '13px', color: '#6b7280', margin: '8px 0 16px 0' }}>
        People, organizations, and places that frequently appear together in articles
      </p>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ marginRight: '10px', fontWeight: 500 }}>Filter by type:</label>
        <select
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
          style={{
            padding: '8px 12px',
            borderRadius: '6px',
            border: '1px solid #d1d5db',
            fontSize: '14px'
          }}
        >
          <option value="">All Types</option>
          <option value="PERSON">People</option>
          <option value="ORG">Organizations</option>
          <option value="GPE">Locations</option>
        </select>
      </div>

      {loading ? (
        <p>Loading relationships...</p>
      ) : cooccurrences.length > 0 ? (
        <div className="cooccurrence-grid">
          {cooccurrences.map((pair, idx) => (
            <div key={idx} className="cooccurrence-card">
              <div className="cooccurrence-header">
                <span className="rank-badge">#{idx + 1}</span>
                <span className="count-badge">
                  {pair.cooccurrence_count} {pair.cooccurrence_count === 1 ? 'article' : 'articles'}
                </span>
              </div>
              <div className="entity-pair">
                <div className="entity-box">
                  <div className="entity-name">{pair.entity1}</div>
                  <div className="entity-type">{pair.type1}</div>
                </div>
                <div className="connection-line">
                  <svg width="40" height="4" viewBox="0 0 40 4">
                    <line x1="0" y1="2" x2="40" y2="2" stroke="#9ca3af" strokeWidth="2"/>
                    <circle cx="20" cy="2" r="3" fill="#6366f1"/>
                  </svg>
                </div>
                <div className="entity-box">
                  <div className="entity-name">{pair.entity2}</div>
                  <div className="entity-type">{pair.type2}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p>No entity relationships found. Try a different filter or add more articles.</p>
      )}
    </div>
  );
};

// Entity Timeline - shows when entities were mentioned over time
export const EntityTimeline: React.FC = () => {
  const [topEntities, setTopEntities] = useState<string[]>([]);
  const [timelineData, setTimelineData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadTimeline = async () => {
      try {
        // Get top 5 entities
        const entitiesRes = await axios.get(`${API_BASE}/analytics/top-entities-fixed?limit=5`);
        const entities = entitiesRes.data.entities || [];
        const entityNames = entities.map((e: any) => e.text);
        setTopEntities(entityNames);

        // For now, show placeholder - would need backend endpoint to get entity mentions over time
        // This is a simplified version
        setTimelineData([]);
      } catch (error) {
        console.error('Failed to load entity timeline:', error);
      } finally {
        setLoading(false);
      }
    };
    loadTimeline();
  }, []);

  if (loading) return <p>Loading...</p>;

  return (
    <div>
      <h3>Top Entities</h3>
      <p style={{ fontSize: '13px', color: '#6b7280', margin: '8px 0 16px 0' }}>
        Most frequently mentioned people, organizations, and locations
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
        {topEntities.map((entity, idx) => (
          <div
            key={idx}
            style={{
              padding: '10px 16px',
              background: '#f3f4f6',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: 500
            }}
          >
            {entity}
          </div>
        ))}
      </div>
    </div>
  );
};
