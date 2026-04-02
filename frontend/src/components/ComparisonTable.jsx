import React, { useMemo } from 'react';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

function fmt(v, decimals = 1) {
  if (v === null || v === undefined) return '—';
  return typeof v === 'number' ? v.toFixed(decimals) : v;
}

function Delta({ val, unit = '', betterWhenLower = true }) {
  if (val === null || val === undefined) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
  const n    = Number(val);
  const isGood = betterWhenLower ? n < 0 : n > 0;
  const color  = n === 0 ? 'var(--text-muted)' : isGood ? 'var(--green)' : 'var(--red)';
  const Icon   = n === 0 ? Minus : isGood ? ArrowDownRight : ArrowUpRight;
  return (
    <span style={{ color, display: 'inline-flex', alignItems: 'center', gap: 2 }}>
      <Icon size={10} />
      {n >= 0 ? '+' : ''}{fmt(n)}{unit}
    </span>
  );
}

export default function ComparisonTable({ simResult }) {
  if (!simResult) return null;

  const { before, after, impact, scenario_id } = simResult;
  const bSummary = before?.summary ?? {};
  const aSummary = after?.summary  ?? {};

  const rows = useMemo(() => [
    {
      metric: 'Avg Congestion',
      unit: '%',
      before: bSummary.avg_congestion_pct,
      after:  aSummary.avg_congestion_pct,
      lowerBetter: true,
    },
    {
      metric: 'Avg Speed',
      unit: ' km/h',
      before: bSummary.avg_speed_kmph,
      after:  aSummary.avg_speed_kmph,
      lowerBetter: false,
    },
    {
      metric: 'Avg AQI',
      unit: '',
      before: bSummary.avg_aqi,
      after:  aSummary.avg_aqi,
      lowerBetter: true,
    },
    {
      metric: 'City Health Score',
      unit: '/100',
      before: bSummary.city_health_score,
      after:  aSummary.city_health_score,
      lowerBetter: false,
    },
    {
      metric: 'Critical Roads',
      unit: '',
      before: before?.road_states?.filter(r => r.los === 'F' || r.los === 'E').length ?? 0,
      after:  after?.road_states?.filter(r => r.los === 'F' || r.los === 'E').length ?? 0,
      lowerBetter: true,
    },
    {
      metric: 'LOS F Roads',
      unit: '',
      before: before?.road_states?.filter(r => r.los === 'F').length ?? 0,
      after:  after?.road_states?.filter(r => r.los === 'F').length ?? 0,
      lowerBetter: true,
    },
  ], [bSummary, aSummary, before, after]);

  // Per-road comparison
  const roadRows = useMemo(() => {
    if (!before?.road_states || !after?.road_states) return [];
    return before.road_states.map(br => {
      const ar = after.road_states.find(r => r.road_id === br.road_id);
      if (!ar) return null;
      const vcDelta = (ar.vc_ratio - br.vc_ratio);
      if (Math.abs(vcDelta) < 0.02) return null; // skip unchanged
      return {
        road_id: br.road_id,
        name:    br.road_id.replace(/_/g, ' ').toUpperCase(),
        bLOS:    br.los, aLOS: ar.los,
        bVC:     br.vc_ratio, aVC: ar.vc_ratio,
        bSpeed:  br.effective_speed, aSpeed: ar.effective_speed,
        vcDelta,
      };
    }).filter(Boolean).sort((a, b) => Math.abs(b.vcDelta) - Math.abs(a.vcDelta)).slice(0, 8);
  }, [before, after]);

  const sceneName = scenario_id?.replace(/_/g, ' ').toUpperCase();

  return (
    <div style={{ padding: 'var(--gap-md)', animation: 'fadeIn 0.3s ease' }}>
      {/* Header */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--r-md)',
        padding: 'var(--gap-md)',
        marginBottom: 'var(--gap-md)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 13, fontWeight: 700 }}>
            Scenario: {sceneName}
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', marginTop: 2 }}>
            BEFORE / AFTER COMPARISON
          </div>
        </div>
        <span className={`severity-badge severity-${impact?.severity ?? 'Low'}`}>
          {impact?.severity ?? '—'}
        </span>
      </div>

      {/* City-wide metrics */}
      <div style={{ marginBottom: 'var(--gap-md)' }}>
        <div className="section-title" style={{ marginBottom: 8 }}>City-Wide Metrics</div>
        <table className="compare-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Before</th>
              <th>After</th>
              <th>Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => {
              const diff = (r.after ?? 0) - (r.before ?? 0);
              return (
                <tr key={r.metric}>
                  <td style={{ color: 'var(--text-secondary)' }}>{r.metric}</td>
                  <td>{fmt(r.before)}{r.unit}</td>
                  <td>{fmt(r.after)}{r.unit}</td>
                  <td><Delta val={diff} unit={r.unit} betterWhenLower={r.lowerBetter} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Per-road impact */}
      {roadRows.length > 0 && (
        <div>
          <div className="section-title" style={{ marginBottom: 8 }}>Most Impacted Roads</div>
          <table className="compare-table">
            <thead>
              <tr>
                <th>Road</th>
                <th>LOS</th>
                <th>V/C</th>
                <th>Speed Δ</th>
              </tr>
            </thead>
            <tbody>
              {roadRows.map(r => (
                <tr key={r.road_id}>
                  <td style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} className="truncate" title={r.name}>
                    {r.name.length > 16 ? r.name.slice(0,16) + '…' : r.name}
                  </td>
                  <td>
                    <span className={`los-badge los-${r.bLOS}`}>{r.bLOS}</span>
                    <span style={{ margin: '0 4px', color: 'var(--text-muted)' }}>→</span>
                    <span className={`los-badge los-${r.aLOS}`}>{r.aLOS}</span>
                  </td>
                  <td>
                    <span style={{ color: r.vcDelta > 0 ? 'var(--red)' : 'var(--green)', fontFamily: 'var(--font-mono)', fontSize: 10 }}>
                      {r.aVC.toFixed(2)}
                    </span>
                  </td>
                  <td>
                    <Delta val={(r.aSpeed - r.bSpeed)} unit=" km/h" betterWhenLower={false} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
