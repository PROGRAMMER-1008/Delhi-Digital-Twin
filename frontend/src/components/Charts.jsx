import React, { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadialBarChart, RadialBar, Cell, PieChart, Pie, Legend,
} from 'recharts';

const TOOLTIP_STYLE = {
  background: '#0c1524',
  border: '1px solid rgba(0,200,255,0.3)',
  borderRadius: 6,
  fontFamily: 'Space Mono, monospace',
  fontSize: 10,
  color: '#e8f4ff',
  boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
};

function getLoSColor(los) {
  const c = { A: '#00e400', B: '#7fe800', C: '#e6e600', D: '#ff7e00', E: '#ff2222', F: '#8f3f97' };
  return c[los] ?? '#888';
}

// ── Road Utilization Bar Chart ───────────────────────────────────────
function RoadUtilizationChart({ roadStates }) {
  if (!roadStates?.length) return null;

  const data = roadStates
    .sort((a, b) => b.vc_ratio - a.vc_ratio)
    .slice(0, 10)
    .map(r => ({
      name: r.road_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()).slice(0, 12),
      vc: parseFloat((r.vc_ratio * 100).toFixed(1)),
      los: r.los,
    }));

  return (
    <div style={{ marginBottom: 'var(--gap-md)' }}>
      <div className="section-title" style={{ marginBottom: 8 }}>Road Utilization (V/C %)</div>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 16, top: 0, bottom: 0 }}>
          <XAxis type="number" domain={[0, 130]} tick={{ fontSize: 8, fill: 'rgba(232,244,255,0.35)', fontFamily: 'Space Mono' }} />
          <YAxis type="category" dataKey="name" width={72} tick={{ fontSize: 8, fill: 'rgba(232,244,255,0.4)', fontFamily: 'Space Mono' }} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(v) => [`${v}%`, 'V/C Ratio']}
            cursor={{ fill: 'rgba(0,200,255,0.05)' }}
          />
          <Bar dataKey="vc" radius={[0, 3, 3, 0]} maxBarSize={12}>
            {data.map((entry, i) => (
              <Cell key={i} fill={getLoSColor(entry.los)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── LOS Distribution Pie Chart ───────────────────────────────────────
function LOSDistributionChart({ roadStates }) {
  if (!roadStates?.length) return null;

  const counts = roadStates.reduce((acc, r) => {
    acc[r.los] = (acc[r.los] ?? 0) + 1;
    return acc;
  }, {});

  const data = ['A','B','C','D','E','F'].map(los => ({
    name: `LOS ${los}`,
    value: counts[los] ?? 0,
    color: getLoSColor(los),
  })).filter(d => d.value > 0);

  return (
    <div style={{ marginBottom: 'var(--gap-md)' }}>
      <div className="section-title" style={{ marginBottom: 8 }}>Level of Service Distribution</div>
      <ResponsiveContainer width="100%" height={140}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={35}
            outerRadius={55}
            dataKey="value"
            strokeWidth={0}
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} opacity={0.85} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(v, n) => [v + ' roads', n]}
          />
          <Legend
            iconSize={8}
            wrapperStyle={{ fontFamily: 'Space Mono', fontSize: 9, color: 'rgba(232,244,255,0.5)' }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Before/After Comparison Bar Chart ────────────────────────────────
function ComparisonChart({ simResult }) {
  if (!simResult) return null;

  const b = simResult.before?.summary ?? {};
  const a = simResult.after?.summary  ?? {};

  const data = [
    { name: 'Congestion', before: +(b.avg_congestion_pct?.toFixed(1) ?? 0), after: +(a.avg_congestion_pct?.toFixed(1) ?? 0) },
    { name: 'Avg Speed',  before: +(b.avg_speed_kmph?.toFixed(1) ?? 0),     after: +(a.avg_speed_kmph?.toFixed(1) ?? 0) },
    { name: 'AQI',        before: +(b.avg_aqi?.toFixed(0) ?? 0),             after: +(a.avg_aqi?.toFixed(0) ?? 0) },
    { name: 'Health',     before: +(b.city_health_score?.toFixed(0) ?? 0),   after: +(a.city_health_score?.toFixed(0) ?? 0) },
  ];

  return (
    <div style={{ marginBottom: 'var(--gap-md)' }}>
      <div className="section-title" style={{ marginBottom: 8 }}>Before vs After Simulation</div>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={data} margin={{ left: 4, right: 8, top: 4, bottom: 0 }}>
          <XAxis dataKey="name" tick={{ fontSize: 8, fill: 'rgba(232,244,255,0.4)', fontFamily: 'Space Mono' }} />
          <YAxis tick={{ fontSize: 8, fill: 'rgba(232,244,255,0.35)', fontFamily: 'Space Mono' }} />
          <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(0,200,255,0.04)' }} />
          <Bar dataKey="before" fill="rgba(0,200,255,0.4)"  radius={[3,3,0,0]} maxBarSize={20} name="Before" />
          <Bar dataKey="after"  fill="rgba(255,179,71,0.7)" radius={[3,3,0,0]} maxBarSize={20} name="After" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Main Charts Component ─────────────────────────────────────────────
export default function Charts({ cityState, simResult }) {
  const roadStates = simResult?.after?.road_states ?? cityState?.road_states;

  return (
    <div style={{ padding: 'var(--gap-md)' }}>
      {simResult && <ComparisonChart simResult={simResult} />}
      <RoadUtilizationChart roadStates={roadStates} />
      <LOSDistributionChart roadStates={roadStates} />
    </div>
  );
}
