import React, { useState, useEffect } from 'react';
import { RefreshCw, Wifi, WifiOff, AlertTriangle } from 'lucide-react';
import { useCityData } from './hooks/useCityData';
import MapView           from './components/MapView';
import Dashboard         from './components/Dashboard';
import ScenarioPanel     from './components/ScenarioPanel';
import ComparisonTable   from './components/ComparisonTable';
import RecommendationPanel from './components/RecommendationPanel';
import WeatherWidget     from './components/WeatherWidget';
import Charts            from './components/Charts';
import MLPanel           from './components/MLPanel';

// ── Clock ─────────────────────────────────────────────────────────────
function LiveClock() {
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <span className="header-time">
      {time.toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'short' })}
      &nbsp;·&nbsp;
      {time.toLocaleTimeString('en-IN', { hour12: false })}
    </span>
  );
}

// ── Logo SVG ──────────────────────────────────────────────────────────
function LogoSVG() {
  return (
    <svg viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="2" width="24" height="24" rx="4" stroke="#00c8ff" strokeWidth="1.5" strokeOpacity="0.6"/>
      <path d="M7 20L11 12L15 16L19 8" stroke="#00c8ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="7" cy="20" r="1.5" fill="#00c8ff"/>
      <circle cx="19" cy="8" r="1.5" fill="#00c8ff"/>
      <circle cx="14" cy="14" r="4" stroke="#00c8ff" strokeWidth="1" strokeOpacity="0.3" strokeDasharray="2 2"/>
    </svg>
  );
}

// ── Map Legend ────────────────────────────────────────────────────────
function MapLegend() {
  const levels = [
    { label: 'Free Flow',  color: '#00e400' },
    { label: 'Good',       color: '#7fe800' },
    { label: 'Moderate',   color: '#ffff00' },
    { label: 'Congested',  color: '#ff7e00' },
    { label: 'Heavy',      color: '#ff2222' },
    { label: 'Gridlock',   color: '#8f3f97' },
  ];
  return (
    <div className="map-overlay-badge bottom-left">
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 6 }}>
        Traffic Level
      </div>
      {levels.map(l => (
        <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
          <div style={{ width: 20, height: 3, borderRadius: 2, background: l.color, boxShadow: `0 0 4px ${l.color}` }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-secondary)' }}>{l.label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Simulation Status Badge ───────────────────────────────────────────
function SimBadge({ simResult }) {
  if (!simResult) return null;
  const impact = simResult.impact;
  return (
    <div className="map-overlay-badge top-right" style={{ textAlign: 'right' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: 4 }}>
        ACTIVE SIMULATION
      </div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: 13, fontWeight: 700, color: 'var(--cyan)' }}>
        {simResult.scenario_id?.replace(/_/g, ' ').toUpperCase()}
      </div>
      <div style={{ marginTop: 4, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: impact?.congestion_change_pct > 0 ? 'var(--red)' : 'var(--green)' }}>
          {impact?.congestion_change_pct >= 0 ? '+' : ''}{impact?.congestion_change_pct?.toFixed(1)}% congestion
        </span>
        <span className={`severity-badge severity-${impact?.severity}`}>{impact?.severity}</span>
      </div>
    </div>
  );
}

// ── Right Panel Tabs ──────────────────────────────────────────────────
const RIGHT_TABS = [
  { id: 'recommendations', label: '💡 Recs' },
  { id: 'comparison',      label: '📊 Compare' },
  { id: 'charts',          label: '📈 Charts' },
  { id: 'ml',              label: '🧠 AI/ML' },
];

// ── Left Panel Tabs ───────────────────────────────────────────────────
const LEFT_TABS = [
  { id: 'overview',  label: '🏙️ Overview' },
  { id: 'scenario',  label: '⚡ Scenario' },
];

export default function App() {
  const {
    cityState, scenarios, simResult,
    loading, simLoading, error,
    lastUpdated, simulate, clearSim, refresh,
  } = useCityData();

  const [leftTab,  setLeftTab]  = useState('overview');
  const [rightTab, setRightTab] = useState('recommendations');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Auto-switch to recommendations after simulation
  useEffect(() => {
    if (simResult) setRightTab('recommendations');
  }, [simResult]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refresh();
    setIsRefreshing(false);
  };

  return (
    <div className="app-shell">

      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="app-header">
        <div className="header-brand">
          <div className="header-logo"><LogoSVG /></div>
          <div className="brand-text">
            <h1>Delhi Digital Twin</h1>
            <span>Decision Intelligence System v2.0</span>
          </div>
        </div>

        <div className="header-status">
          {error && (
            <div className="status-pill" style={{ borderColor: 'rgba(255,77,106,0.4)', color: 'var(--red)' }}>
              <AlertTriangle size={10} />
              {error.slice(0, 40)}
            </div>
          )}

          <div className="status-pill">
            <div className="status-dot" style={{ background: cityState ? 'var(--green)' : 'var(--amber)' }} />
            {cityState ? 'LIVE DATA' : 'CONNECTING'}
          </div>

          {lastUpdated && (
            <div className="status-pill">
              <Wifi size={9} color="var(--green)" />
              {lastUpdated.toLocaleTimeString('en-IN', { hour12: false })}
            </div>
          )}

          <button
            className="btn btn-ghost btn-sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
            title="Refresh live data"
          >
            <RefreshCw size={11} className={isRefreshing ? 'spin' : ''} style={isRefreshing ? { animation: 'spin 0.6s linear infinite' } : {}} />
          </button>

          <LiveClock />
        </div>
      </header>

      {/* ── Left Panel ─────────────────────────────────────────────── */}
      <aside className="panel-left">

        {/* Tab bar */}
        <div className="tab-bar">
          {LEFT_TABS.map(t => (
            <button
              key={t.id}
              className={`tab-btn ${leftTab === t.id ? 'active' : ''}`}
              onClick={() => setLeftTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {leftTab === 'overview' && (
          <>
            <Dashboard cityState={cityState} simResult={simResult} />
            <WeatherWidget cityState={cityState} />
          </>
        )}

        {leftTab === 'scenario' && (
          <ScenarioPanel
            scenarios={scenarios}
            onSimulate={simulate}
            simLoading={simLoading}
            onClear={clearSim}
            hasResult={!!simResult}
          />
        )}
      </aside>

      {/* ── Map ────────────────────────────────────────────────────── */}
      <main className="map-area">
        {loading && (
          <div className="loading-overlay">
            <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
            <div className="loading-text">Initializing City Twin…</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>
              Loading live data feeds from Delhi APIs
            </div>
          </div>
        )}

        <MapView cityState={cityState} simResult={simResult} />

        {/* Map overlays */}
        <MapLegend />
        {simResult && <SimBadge simResult={simResult} />}

        {/* Simulation loading overlay */}
        {simLoading && (
          <div className="loading-overlay">
            <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
            <div className="loading-text">Running Simulation…</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>
              Computing traffic flow, pollution impact & recommendations
            </div>
          </div>
        )}
      </main>

      {/* ── Right Panel ────────────────────────────────────────────── */}
      <aside className="panel-right">

        {/* Tab bar */}
        <div className="tab-bar">
          {RIGHT_TABS.map(t => (
            <button
              key={t.id}
              className={`tab-btn ${rightTab === t.id ? 'active' : ''}`}
              onClick={() => setRightTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {rightTab === 'recommendations' && (
          <RecommendationPanel simResult={simResult} />
        )}

        {rightTab === 'comparison' && (
          simResult
            ? <ComparisonTable simResult={simResult} />
            : (
              <div className="empty-state" style={{ padding: 'var(--gap-2xl)' }}>
                <div className="empty-icon">📊</div>
                <div className="empty-text">Run a simulation to<br />compare before/after metrics</div>
              </div>
            )
        )}

        {rightTab === 'charts' && (
          <Charts cityState={cityState} simResult={simResult} />
        )}

        {rightTab === 'ml' && (
          <MLPanel />
        )}
      </aside>
    </div>
  );
}
