import React, { useMemo } from 'react';
import { Activity, Wind, Users, Zap, TrendingUp, TrendingDown } from 'lucide-react';

function HealthRing({ score, size = 80 }) {
  const r   = (size / 2) - 8;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  const color = score >= 75 ? 'var(--green)'
    : score >= 50 ? 'var(--cyan)'
    : score >= 30 ? 'var(--amber)'
    : 'var(--red)';

  return (
    <div className="health-ring" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="var(--border-dim)" strokeWidth="6"
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: 'stroke-dasharray 0.6s ease', filter: `drop-shadow(0 0 4px ${color})` }}
        />
      </svg>
      <div className="health-ring-label">
        <span className="health-score-val" style={{ color }}>{Math.round(score)}</span>
        <span className="health-score-sub">health</span>
      </div>
    </div>
  );
}

function MetricCard({ label, value, unit, delta, deltaLabel, accentColor, icon: Icon }) {
  const hasDelta = delta !== undefined && delta !== null;
  const isPos    = hasDelta && delta >= 0;

  return (
    <div className="metric-card" style={{ '--accent-color': accentColor }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <div className="metric-label">{label}</div>
        {Icon && <Icon size={12} color={accentColor || 'var(--text-muted)'} opacity={0.6} />}
      </div>
      <div className="metric-value">
        {value ?? '—'}
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
      {hasDelta && (
        <div className={`metric-delta ${isPos ? 'positive' : 'negative'}`}>
          {isPos ? '▲' : '▼'} {Math.abs(delta).toFixed(1)} {deltaLabel}
        </div>
      )}
    </div>
  );
}

export default function Dashboard({ cityState, simResult }) {
  const summary = cityState?.summary;
  const weather = cityState?.weather;
  const impact  = simResult?.impact;

  const congPct  = summary?.avg_congestion_pct  ?? 0;
  const aqiVal   = summary?.avg_aqi             ?? 0;
  const healthSc = summary?.city_health_score   ?? 0;
  const avgSpeed = summary?.avg_speed_kmph      ?? 0;

  const aqiLabel = useMemo(() => {
    if (aqiVal <= 50)  return { text: 'GOOD',      color: 'var(--aqi-good)' };
    if (aqiVal <= 100) return { text: 'MODERATE',  color: 'var(--aqi-moderate)' };
    if (aqiVal <= 150) return { text: 'SENSITIVE',  color: 'var(--aqi-sensitive)' };
    if (aqiVal <= 200) return { text: 'UNHEALTHY', color: 'var(--aqi-unhealthy)' };
    if (aqiVal <= 300) return { text: 'VERY UNHEALTHY', color: 'var(--aqi-very)' };
    return { text: 'HAZARDOUS', color: 'var(--aqi-hazardous)' };
  }, [aqiVal]);

  return (
    <div className="panel-section">
      <div className="section-header">
        <div className="section-title">City Overview</div>
        {impact && (
          <span className={`severity-badge severity-${impact.severity}`}>
            {impact.severity}
          </span>
        )}
      </div>

      {/* Health ring + AQI */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap-md)', marginBottom: 'var(--gap-md)' }}>
        <HealthRing score={healthSc} />
        <div style={{ flex: 1 }}>
          <div className="metric-label" style={{ marginBottom: 4 }}>Air Quality Index</div>
          <div className="metric-value" style={{ color: aqiLabel.color, fontSize: 24 }}>
            {Math.round(aqiVal)}
          </div>
          <div className="aqi-bar" style={{ marginTop: 6, marginBottom: 4 }}>
            <div
              className="aqi-needle"
              style={{ left: `${Math.min((aqiVal / 500) * 100, 100)}%` }}
            />
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: aqiLabel.color, letterSpacing: '0.1em' }}>
            {aqiLabel.text}
          </span>
        </div>
      </div>

      {/* Metrics grid */}
      <div className="metric-grid">
        <MetricCard
          label="Congestion"
          value={Math.round(congPct)}
          unit="%"
          accentColor={congPct > 80 ? 'var(--red)' : congPct > 60 ? 'var(--amber)' : 'var(--green)'}
          icon={Activity}
          delta={impact ? impact.congestion_change_pct : undefined}
          deltaLabel="%"
        />
        <MetricCard
          label="Avg Speed"
          value={Math.round(avgSpeed)}
          unit=" km/h"
          accentColor="var(--cyan)"
          icon={Zap}
          delta={impact ? impact.speed_change_kmph : undefined}
          deltaLabel="km/h"
        />
        <MetricCard
          label="Active Roads"
          value={cityState?.road_states?.length ?? 0}
          accentColor="var(--purple)"
          icon={TrendingUp}
        />
        <MetricCard
          label="Zone Health"
          value={cityState?.zones?.length ?? 0}
          unit=" zones"
          accentColor="var(--green)"
          icon={Users}
        />
      </div>

      {/* Simulation impact summary */}
      {impact && (
        <div style={{
          marginTop: 'var(--gap-md)',
          background: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--r-md)',
          padding: 'var(--gap-md)',
          animation: 'fadeIn 0.3s ease',
        }}>
          <div className="section-title" style={{ marginBottom: 8 }}>Simulation Impact</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {[
              { k: 'Congestion Δ',  v: `${impact.congestion_change_pct >= 0 ? '+' : ''}${impact.congestion_change_pct?.toFixed(1)}%`, neg: impact.congestion_change_pct > 0 },
              { k: 'AQI Δ',         v: `${impact.aqi_change >= 0 ? '+' : ''}${impact.aqi_change?.toFixed(1)}`,     neg: impact.aqi_change > 0 },
              { k: 'Speed Δ',       v: `${impact.speed_change_kmph >= 0 ? '+' : ''}${impact.speed_change_kmph?.toFixed(1)} km/h`, neg: impact.speed_change_kmph < 0 },
              { k: 'Affected Zones', v: impact.affected_zones?.length ?? 0, neg: false },
            ].map(({ k, v, neg }) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.06em' }}>{k}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: neg ? 'var(--red)' : 'var(--green)', fontWeight: 700 }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
