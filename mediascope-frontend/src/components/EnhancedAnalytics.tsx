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
    <div style={{
      display: 'flex',
      gap: '1rem',
      padding: '0.75rem',
      background: '#f9fafb',
      borderRadius: '8px',
      marginBottom: '1rem',
      fontSize: '14px'
    }}>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontSize: '20px' }}>📚</span>
        <div>
          <div style={{ fontSize: '11px', color: '#6b7280' }}>Total Articles</div>
          <div style={{ fontSize: '18px', fontWeight: '700', color: '#374151' }}>
            {stats.totalArticles.toLocaleString()}
          </div>
        </div>
      </div>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontSize: '20px' }}>📅</span>
        <div>
          <div style={{ fontSize: '11px', color: '#6b7280' }}>Coverage Period</div>
          <div style={{ fontSize: '13px', fontWeight: '600', color: '#374151' }}>
            {stats.dateRange}
          </div>
        </div>
      </div>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontSize: '20px' }}>
          {parseFloat(stats.avgSentiment) > 0.1 ? '😊' :
           parseFloat(stats.avgSentiment) < -0.1 ? '😟' : '😐'}
        </span>
        <div>
          <div style={{ fontSize: '11px', color: '#6b7280' }}>Overall Sentiment</div>
          <div style={{
            fontSize: '18px',
            fontWeight: '700',
            color: parseFloat(stats.avgSentiment) > 0.1 ? '#10b981' :
                     parseFloat(stats.avgSentiment) < -0.1 ? '#ef4444' : '#6b7280'
          }}>
            {parseFloat(stats.avgSentiment) > 0 ? '+' : ''}{stats.avgSentiment}
          </div>
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
            label={(entry: any) => `${entry.name}: ${(entry.percent * 100).toFixed(1)}%`}
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
  const [expandedTopic, setExpandedTopic] = useState<number | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await axios.get(`${API_BASE}/topics`);
        const topics = response.data.topics || [];

        // Filter out generic topics and sort by count
        const meaningfulTopics = topics
          .filter((topic: any) => topic.count >= 30)  // Only show substantial topics
          .sort((a: any, b: any) => b.count - a.count);

        setData(meaningfulTopics);
      } catch (error) {
        console.error('Failed to load topics:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) return <p style={{ margin: '1rem 0', fontSize: '14px' }}>Loading topics...</p>;
  if (data.length === 0) return (
    <div style={{ margin: '1rem 0', padding: '1rem', background: '#fef3c7', borderRadius: '6px', fontSize: '13px' }}>
      <strong>No topics found.</strong> Train the topic model first by clicking the "Train Topics" button, or topics may need more articles (minimum 30 per topic).
    </div>
  );

  return (
    <div>
      <h3 style={{ marginBottom: '0.75rem' }}>Discovered Topics ({data.length})</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {data.map((topic, idx) => {
          const isExpanded = expandedTopic === topic.topic_id;
          const topicColor = `hsl(${(idx * 137.5) % 360}, 65%, 50%)`;

          return (
            <div key={topic.topic_id} style={{
              border: `2px solid ${isExpanded ? topicColor : '#e5e7eb'}`,
              borderRadius: '8px',
              background: 'white',
              transition: 'all 0.2s',
              overflow: 'hidden'
            }}>
              {/* Topic Header */}
              <div
                onClick={() => setExpandedTopic(isExpanded ? null : topic.topic_id)}
                style={{
                  padding: '12px',
                  cursor: 'pointer',
                  background: isExpanded ? `${topicColor}15` : 'white'
                }}
                onMouseEnter={(e) => {
                  if (!isExpanded) e.currentTarget.style.background = '#f9fafb';
                }}
                onMouseLeave={(e) => {
                  if (!isExpanded) e.currentTarget.style.background = 'white';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '16px' }}>{isExpanded ? '▼' : '▶'}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <span style={{
                        background: topicColor,
                        width: '10px',
                        height: '10px',
                        borderRadius: '50%',
                        flexShrink: 0
                      }}></span>
                      <span style={{ fontWeight: '700', color: '#1f2937', fontSize: '14px' }}>
                        {topic.name}
                      </span>
                      <span style={{
                        background: topicColor,
                        color: 'white',
                        padding: '2px 10px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: '600'
                      }}>
                        {topic.count} articles
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>
                      {topic.keywords.slice(0, 8).join(' • ')}
                    </div>
                  </div>
                </div>
              </div>

              {/* Expanded Details */}
              {isExpanded && (
                <div style={{ padding: '12px', borderTop: '1px solid #e5e7eb', background: '#fafafa' }}>
                  {/* Keyword Scores */}
                  <div style={{ marginBottom: '12px' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#374151' }}>
                      Top Keywords (with relevance scores)
                    </h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {topic.keyword_scores?.map(([word, score]: [string, number], kidx: number) => (
                        <div key={kidx} style={{
                          padding: '4px 10px',
                          background: 'white',
                          border: '1px solid #e5e7eb',
                          borderRadius: '6px',
                          fontSize: '12px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}>
                          <span style={{ fontWeight: '600', color: '#374151' }}>{word}</span>
                          <span style={{ fontSize: '11px', color: '#9ca3af' }}>({score})</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Representative Documents */}
                  {topic.representative_docs && topic.representative_docs.length > 0 && (
                    <div>
                      <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#374151' }}>
                        Sample Articles
                      </h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {topic.representative_docs.map((doc: any, didx: number) => (
                          <div key={didx} style={{
                            padding: '8px 10px',
                            background: 'white',
                            border: '1px solid #e5e7eb',
                            borderRadius: '6px',
                            fontSize: '12px',
                            color: '#374151'
                          }}>
                            <span style={{ color: '#9ca3af', marginRight: '8px' }}>{didx + 1}.</span>
                            {doc.headline}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
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
        <div className="cooccurrence-table-container">
          <table className="cooccurrence-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Entity 1</th>
                <th>Type</th>
                <th></th>
                <th>Entity 2</th>
                <th>Type</th>
                <th>Appears Together</th>
              </tr>
            </thead>
            <tbody>
              {cooccurrences.map((pair, idx) => (
                <tr key={idx}>
                  <td className="rank-cell">{idx + 1}</td>
                  <td className="entity-cell"><strong>{pair.entity1}</strong></td>
                  <td className="type-cell"><span className="type-badge">{pair.type1}</span></td>
                  <td className="arrow-cell">↔</td>
                  <td className="entity-cell"><strong>{pair.entity2}</strong></td>
                  <td className="type-cell"><span className="type-badge">{pair.type2}</span></td>
                  <td className="count-cell">
                    <span className="count-value">{pair.cooccurrence_count}</span> articles
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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

// Article Length Distribution
export const ArticleLengthDistribution: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await axios.get(`${API_BASE}/articles`);
        const articles = response.data.articles || [];

        // Group by word count ranges
        const ranges: any = {
          '0-100': 0,
          '101-300': 0,
          '301-500': 0,
          '501-800': 0,
          '800+': 0
        };

        articles.forEach((article: any) => {
          const wc = article.word_count || 0;
          if (wc <= 100) ranges['0-100']++;
          else if (wc <= 300) ranges['101-300']++;
          else if (wc <= 500) ranges['301-500']++;
          else if (wc <= 800) ranges['501-800']++;
          else ranges['800+']++;
        });

        setData([
          { range: '0-100', count: ranges['0-100'], label: 'Very Short' },
          { range: '101-300', count: ranges['101-300'], label: 'Short' },
          { range: '301-500', count: ranges['301-500'], label: 'Medium' },
          { range: '501-800', count: ranges['501-800'], label: 'Long' },
          { range: '800+', count: ranges['800+'], label: 'Very Long' }
        ]);
      } catch (error) {
        console.error('Failed to load article lengths:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) return <p>Loading...</p>;
  if (data.length === 0) return <p>No data available</p>;

  return (
    <div>
      <h3>Article Length Distribution</h3>
      <p style={{ fontSize: '13px', color: '#6b7280', margin: '8px 0 16px 0' }}>
        Distribution of articles by word count - shows typical article length patterns
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="count" fill="#f59e0b" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// Coverage Heatmap - Shows publication intensity by month
export const CoverageHeatmap: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await axios.get(`${API_BASE}/analytics/articles-over-time`);
        const timeline = response.data.timeline || [];

        setData(timeline);
      } catch (error) {
        console.error('Failed to load coverage data:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) return <p>Loading...</p>;
  if (data.length === 0) return <p>No data available</p>;

  const maxCount = Math.max(...data.map((d: any) => d.count));

  return (
    <div>
      <h3>Coverage Intensity</h3>
      <p style={{ fontSize: '13px', color: '#6b7280', margin: '8px 0 16px 0' }}>
        Heatmap showing article publication density - darker colors indicate higher coverage
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '20px' }}>
        {data.map((item, idx) => {
          const intensity = item.count / maxCount;
          const bgColor = `rgba(102, 126, 234, ${intensity * 0.9 + 0.1})`;

          return (
            <div
              key={idx}
              style={{
                minWidth: '80px',
                padding: '12px',
                background: bgColor,
                borderRadius: '8px',
                textAlign: 'center',
                color: intensity > 0.5 ? 'white' : '#1f2937',
                fontWeight: 500,
                fontSize: '13px'
              }}
              title={`${item.count} articles`}
            >
              <div>{item.month}</div>
              <div style={{ fontSize: '18px', marginTop: '4px' }}>{item.count}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
