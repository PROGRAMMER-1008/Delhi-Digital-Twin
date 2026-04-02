import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Lightbulb, Clock, TrendingUp } from 'lucide-react';

const PRIORITY_ORDER = { Critical: 0, High: 1, Medium: 2, Low: 3 };

function RecCard({ rec, index }) {
  const [expanded, setExpanded] = useState(false);

  const priorityColor = {
    Critical: 'var(--red)',
    High:     'var(--amber)',
    Medium:   'var(--cyan)',
    Low:      'var(--green)',
  }[rec.priority] ?? 'var(--cyan)';

  return (
    <div
      className="rec-card"
      style={{
        '--priority-color': priorityColor,
        animationDelay: `${index * 0.06}s`,
      }}
    >
      <div className="rec-header">
        <div className="rec-title">
          <span>{rec.icon}</span>
          <span>{rec.action}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          <span className={`priority-badge priority-${rec.priority}`}>{rec.priority}</span>
          <button
            onClick={() => setExpanded(!expanded)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 2 }}
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
        </div>
      </div>

      {/* Priority bar */}
      <div className="progress-bar" style={{ marginBottom: 6 }}>
        <div
          className="progress-fill"
          style={{
            width: `${rec.priority_score}%`,
            background: `linear-gradient(90deg, ${priorityColor}88, ${priorityColor})`,
          }}
        />
      </div>

      <div className="rec-detail">{rec.detail}</div>

      {expanded && (
        <div style={{ animation: 'fadeIn 0.2s ease' }}>
          <div className="divider" />

          {/* Metrics */}
          {rec.metrics && Object.keys(rec.metrics).length > 0 && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 4,
              marginBottom: 8,
            }}>
              {Object.entries(rec.metrics).map(([k, v]) => (
                <div key={k} style={{
                  background: 'var(--bg-elevated)',
                  borderRadius: 'var(--r-sm)',
                  padding: '4px 8px',
                  display: 'flex',
                  flexDirection: 'column',
                }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7, color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>{k.replace(/_/g, ' ')}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-primary)', marginTop: 1 }}>{v}</span>
                </div>
              ))}
            </div>
          )}

          <div className="rec-meta">
            <div className="rec-tag">
              <TrendingUp size={7} style={{ display: 'inline', marginRight: 3 }} />
              {rec.estimated_impact}
            </div>
            <div className="rec-tag">
              <Clock size={7} style={{ display: 'inline', marginRight: 3 }} />
              {rec.implementation_time}
            </div>
            <div className="rec-tag">Score: {rec.priority_score}/100</div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function RecommendationPanel({ simResult }) {
  const [filter, setFilter] = useState('All');

  if (!simResult?.recommendations?.length) {
    return (
      <div style={{ padding: 'var(--gap-md)' }}>
        <div className="empty-state">
          <div className="empty-icon"><Lightbulb size={32} opacity={0.2} /></div>
          <div className="empty-text">Run a simulation to<br />get AI recommendations</div>
        </div>
      </div>
    );
  }

  const recs = [...simResult.recommendations].sort(
    (a, b) => (PRIORITY_ORDER[a.priority] ?? 9) - (PRIORITY_ORDER[b.priority] ?? 9)
  );

  const priorities = ['All', ...new Set(recs.map(r => r.priority))];
  const filtered   = filter === 'All' ? recs : recs.filter(r => r.priority === filter);

  const counts = {
    Critical: recs.filter(r => r.priority === 'Critical').length,
    High:     recs.filter(r => r.priority === 'High').length,
    Medium:   recs.filter(r => r.priority === 'Medium').length,
    Low:      recs.filter(r => r.priority === 'Low').length,
  };

  return (
    <div style={{ padding: 'var(--gap-md)', display: 'flex', flexDirection: 'column', gap: 'var(--gap-md)' }}>
      {/* Summary bar */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--r-md)',
        padding: 'var(--gap-md)',
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 8,
        textAlign: 'center',
      }}>
        {Object.entries(counts).map(([p, c]) => {
          const color = { Critical: 'var(--red)', High: 'var(--amber)', Medium: 'var(--cyan)', Low: 'var(--green)' }[p];
          return (
            <div key={p} style={{ cursor: 'pointer' }} onClick={() => setFilter(p === filter ? 'All' : p)}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 800, color, opacity: c === 0 ? 0.3 : 1 }}>{c}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 7, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{p}</div>
            </div>
          );
        })}
      </div>

      {/* Filter tabs */}
      {priorities.length > 2 && (
        <div style={{ display: 'flex', gap: 4 }}>
          {priorities.map(p => (
            <button
              key={p}
              className={`tab-btn ${filter === p ? 'active' : ''}`}
              style={{ padding: '6px 10px', flex: 1 }}
              onClick={() => setFilter(p)}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {/* Recommendations */}
      <div>
        {filtered.map((rec, i) => (
          <RecCard key={rec.id} rec={rec} index={i} />
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="empty-state">
          <div className="empty-text">No {filter} priority recommendations</div>
        </div>
      )}
    </div>
  );
}
