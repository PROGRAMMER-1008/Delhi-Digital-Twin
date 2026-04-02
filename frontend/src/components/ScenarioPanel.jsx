import React, { useState, useMemo } from 'react';
import { Play, X, Settings, ChevronDown, ChevronUp } from 'lucide-react';

const SCENARIO_META = {
  rush_hour:          { icon: '🚗', color: '#ff4d6a', name: 'Rush Hour',          desc: 'Peak morning/evening traffic surge across all zones' },
  nh48_closure:       { icon: '🚧', color: '#ffb347', name: 'NH-48 Closure',      desc: 'NH-48 Gurugram highway closed, traffic redistributed' },
  heavy_rain:         { icon: '🌧️', color: '#00c8ff', name: 'Heavy Rain',         desc: 'Monsoon rain reduces road capacity and visibility' },
  republic_day:       { icon: '🎪', color: '#b57bee', name: 'Republic Day',       desc: 'Mass gathering near CP. Rajpath & central roads restricted' },
  adaptive_signals:   { icon: '🚦', color: '#00e5a0', name: 'Smart Signals',      desc: 'AI-optimized signal timing to improve throughput' },
  construction_ring:  { icon: '🏗️', color: '#ffb347', name: 'Ring Road Work',    desc: 'Lane reduction on Ring Road due to Metro expansion' },
  odd_even:           { icon: '🔢', color: '#b57bee', name: 'Odd-Even Scheme',    desc: 'Alternate vehicle policy — 50% reduction in private cars' },
  road_closure:       { icon: '⛔', color: '#ff4d6a', name: 'Custom Closure',     desc: 'Simulate closure of any specific road segment' },
  traffic_surge:      { icon: '📈', color: '#ff7800', name: 'Traffic Surge',      desc: 'Model an X% increase in overall traffic volume' },
  rainfall:           { icon: '⛈️', color: '#00c8ff', name: 'Custom Rainfall',    desc: 'Model specific rainfall intensity impact' },
  event_crowd:        { icon: '🏟️', color: '#b57bee', name: 'Event Crowd',       desc: 'Large event at a specific zone draws extra traffic' },
  signal_optimization:{ icon: '🤖', color: '#00e5a0', name: 'Signal Optimization', desc: 'Optimize signal timing on selected road/intersection' },
  construction:       { icon: '🔨', color: '#ffb347', name: 'Construction Zone',  desc: 'Model lane reduction on any road segment' },
  emission_reduction: { icon: '🌿', color: '#00e5a0', name: 'Emission Reduction', desc: 'Model green transport policy impact on AQI' },
};

const PARAM_CONFIGS = {
  rush_hour:          [],
  nh48_closure:       [],
  heavy_rain:         [],
  republic_day:       [],
  adaptive_signals:   [],
  construction_ring:  [],
  odd_even:           [],
  road_closure:       [
    { key: 'road_id', label: 'Road ID', type: 'select',
      options: ['ring_road_e','ring_road_w','nh48_gurgaon','nh24_noida','mathura_road',
                'outer_ring_n','outer_ring_s','gtroad_n','dwarka_exp','cp_to_okhla',
                'cp_to_rohini','old_delhi_cp','dwarka_janakpuri','noida_east','south_cp',
                'nehru_lajpat','east_ring','north_ring','west_connector','cp_east'] }
  ],
  traffic_surge:      [
    { key: 'surge_pct', label: 'Surge %', type: 'range', min: 10, max: 100, default: 30 }
  ],
  rainfall:           [
    { key: 'intensity', label: 'Intensity', type: 'select',
      options: ['light', 'moderate', 'heavy', 'very_heavy'] }
  ],
  event_crowd:        [
    { key: 'zone', label: 'Event Zone', type: 'select',
      options: ['cp','old_delhi','dwarka','rohini','south_delhi','east_delhi','north_delhi','janakpuri','lajpat_nagar','nehru_place'] },
    { key: 'crowd_size', label: 'Crowd Size', type: 'range', min: 10000, max: 500000, step: 10000, default: 100000 }
  ],
  signal_optimization:[ { key: 'efficiency_gain', label: 'Efficiency Gain %', type: 'range', min: 5, max: 40, default: 20 } ],
  construction:       [
    { key: 'road_id', label: 'Road', type: 'select',
      options: ['ring_road_e','ring_road_w','nh48_gurgaon','nh24_noida','mathura_road','outer_ring_n','outer_ring_s','gtroad_n'] },
    { key: 'lanes_blocked', label: 'Lanes Blocked', type: 'range', min: 1, max: 3, step: 1, default: 1 }
  ],
  emission_reduction: [
    { key: 'ev_pct', label: 'EV Share %', type: 'range', min: 5, max: 60, default: 20 },
    { key: 'policy', label: 'Policy', type: 'select', options: ['ev_mandate','bs6_only','public_transport_boost','mixed'] }
  ],
};

// Grouped scenarios
const SCENARIO_GROUPS = [
  { label: 'Presets', ids: ['rush_hour','nh48_closure','heavy_rain','republic_day','adaptive_signals','construction_ring','odd_even'] },
  { label: 'Custom', ids: ['road_closure','traffic_surge','rainfall','event_crowd','signal_optimization','construction','emission_reduction'] },
];

export default function ScenarioPanel({ scenarios, onSimulate, simLoading, onClear, hasResult }) {
  const [selected,    setSelected]   = useState(null);
  const [params,      setParams]     = useState({});
  const [showCustom,  setShowCustom] = useState(false);

  const meta    = selected ? SCENARIO_META[selected] : null;
  const configs = selected ? (PARAM_CONFIGS[selected] || []) : [];

  const handleSelect = (id) => {
    setSelected(id);
    // Default params
    const defaults = {};
    (PARAM_CONFIGS[id] || []).forEach(p => {
      if (p.default !== undefined) defaults[p.key] = p.default;
      else if (p.options) defaults[p.key] = p.options[0];
    });
    setParams(defaults);
  };

  const handleRun = () => {
    if (!selected) return;
    onSimulate(selected, params);
  };

  const setParam = (key, val) => setParams(prev => ({ ...prev, [key]: val }));

  return (
    <div className="panel-section" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div className="section-header">
        <div className="section-title">Scenario Engine</div>
        {hasResult && (
          <button className="btn btn-ghost btn-sm" onClick={onClear}>
            <X size={10} /> Clear
          </button>
        )}
      </div>

      {SCENARIO_GROUPS.map(group => (
        <div key={group.label} style={{ marginBottom: 'var(--gap-md)' }}>
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 8,
              color: 'var(--text-muted)',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              marginBottom: 6,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: group.label === 'Custom' ? 'pointer' : 'default',
            }}
            onClick={group.label === 'Custom' ? () => setShowCustom(!showCustom) : undefined}
          >
            {group.label} ({group.ids.length})
            {group.label === 'Custom' && (
              showCustom ? <ChevronUp size={10} /> : <ChevronDown size={10} />
            )}
          </div>

          {(group.label !== 'Custom' || showCustom) && (
            <div className="scenario-grid">
              {group.ids.map(id => {
                const m = SCENARIO_META[id];
                return (
                  <div
                    key={id}
                    className={`scenario-card ${selected === id ? 'active' : ''}`}
                    style={{ '--s-color': m.color + '22' }}
                    onClick={() => handleSelect(id)}
                  >
                    <div className="scenario-icon">{m.icon}</div>
                    <div className="scenario-name">{m.name}</div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ))}

      {/* Selected scenario detail */}
      {selected && meta && (
        <div style={{
          background: 'var(--bg-card)',
          border: `1px solid ${meta.color}44`,
          borderRadius: 'var(--r-md)',
          padding: 'var(--gap-md)',
          marginTop: 'auto',
          animation: 'fadeIn 0.2s ease',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 16 }}>{meta.icon}</span>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 13, fontWeight: 700 }}>{meta.name}</div>
            <div style={{ marginLeft: 'auto', width: 8, height: 8, borderRadius: '50%', background: meta.color, boxShadow: `0 0 6px ${meta.color}` }} />
          </div>

          <div style={{ fontFamily: 'var(--font-body)', fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: 12 }}>
            {meta.desc}
          </div>

          {/* Dynamic params */}
          {configs.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
                <Settings size={9} /> Parameters
              </div>
              {configs.map(cfg => (
                <div key={cfg.key}>
                  <label>{cfg.label}
                    {cfg.type === 'range' && (
                      <span style={{ float: 'right', color: 'var(--cyan)' }}>
                        {params[cfg.key] ?? cfg.default}
                        {cfg.key.includes('pct') || cfg.key.includes('gain') ? '%' : ''}
                      </span>
                    )}
                  </label>
                  {cfg.type === 'select' ? (
                    <select value={params[cfg.key] ?? ''} onChange={e => setParam(cfg.key, e.target.value)}>
                      {cfg.options.map(o => <option key={o} value={o}>{o.replace(/_/g, ' ').toUpperCase()}</option>)}
                    </select>
                  ) : (
                    <input
                      type="range"
                      min={cfg.min}
                      max={cfg.max}
                      step={cfg.step ?? 1}
                      value={params[cfg.key] ?? cfg.default}
                      onChange={e => setParam(cfg.key, Number(e.target.value))}
                    />
                  )}
                </div>
              ))}
            </div>
          )}

          <button
            className="btn btn-primary btn-full"
            onClick={handleRun}
            disabled={simLoading}
          >
            {simLoading ? (
              <><div className="spinner" /> Simulating…</>
            ) : (
              <><Play size={11} /> Run Simulation</>
            )}
          </button>
        </div>
      )}

      {!selected && (
        <div className="empty-state" style={{ paddingTop: 'var(--gap-xl)', marginTop: 'auto' }}>
          <div className="empty-icon">🎯</div>
          <div className="empty-text">Select a scenario<br />to begin simulation</div>
        </div>
      )}
    </div>
  );
}
