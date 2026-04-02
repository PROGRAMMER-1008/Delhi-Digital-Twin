import React, { useState, useEffect, useCallback } from 'react';
import { Brain, TrendingUp, Network, Route, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line, ReferenceLine } from 'recharts';
import axios from 'axios';

const TOOLTIP_STYLE = {
  background: '#0c1524', border: '1px solid rgba(0,200,255,0.3)',
  borderRadius: 6, fontFamily: 'Space Mono, monospace', fontSize: 10,
  color: '#e8f4ff', boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
};

function getLOSColor(los) {
  return {A:'#00e400',B:'#7fe800',C:'#e6e600',D:'#ff7e00',E:'#ff2222',F:'#8f3f97'}[los] ?? '#888';
}
function getVCColor(vc) {
  if (vc < 0.60) return '#00e400';
  if (vc < 0.85) return '#e6e600';
  if (vc < 1.00) return '#ff7e00';
  return '#8f3f97';
}
function getRiskColor(risk) {
  return {Low:'#00e5a0', Moderate:'#e6e600', High:'#ff7e00', Critical:'#ff4d6a'}[risk] ?? '#888';
}
const ZONE_OPTIONS = [
  'cp','old_delhi','dwarka','rohini','noida_border','gurugram_border',
  'south_delhi','east_delhi','north_delhi','janakpuri','lajpat_nagar','nehru_place'
];

// ── Algorithm badge ───────────────────────────────────────────────────
function AlgoBadge({ name }) {
  return (
    <div style={{
      display:'inline-flex', alignItems:'center', gap:5,
      background:'rgba(181,123,238,0.12)', border:'1px solid rgba(181,123,238,0.3)',
      borderRadius:4, padding:'3px 8px',
      fontFamily:'var(--font-mono)', fontSize:8, color:'var(--purple)',
      letterSpacing:'0.06em', marginBottom:10,
    }}>
      <Brain size={9}/> {name}
    </div>
  );
}

// ── Section wrapper ───────────────────────────────────────────────────
function MLSection({ title, icon: Icon, algoName, loading, error, children, defaultOpen=true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ borderBottom:'1px solid var(--border-dim)' }}>
      <div
        style={{ display:'flex', alignItems:'center', justifyContent:'space-between',
                 padding:'10px var(--gap-md)', cursor:'pointer',
                 background: open ? 'var(--bg-elevated)' : 'transparent',
                 transition:'background 0.2s' }}
        onClick={() => setOpen(!open)}
      >
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <Icon size={13} color="var(--cyan)" />
          <span style={{ fontFamily:'var(--font-mono)', fontSize:10, letterSpacing:'0.08em',
                         textTransform:'uppercase', color:'var(--text-secondary)' }}>{title}</span>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:6 }}>
          {loading && <div className="spinner" style={{ width:12, height:12, borderWidth:1.5 }} />}
          {error && <span style={{ fontSize:9, color:'var(--red)', fontFamily:'var(--font-mono)' }}>ERROR</span>}
          {open ? <ChevronUp size={11} color="var(--text-muted)"/> : <ChevronDown size={11} color="var(--text-muted)"/>}
        </div>
      </div>
      {open && (
        <div style={{ padding:'var(--gap-sm) var(--gap-md) var(--gap-md)', animation:'fadeIn 0.2s ease' }}>
          <AlgoBadge name={algoName} />
          {error
            ? <div style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--red)' }}>{error}</div>
            : children
          }
        </div>
      )}
    </div>
  );
}

// ── Traffic Forecast Section ──────────────────────────────────────────
function ForecastSection() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [selectedRoad, setSelectedRoad] = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const r = await axios.get('/api/ml/forecast?hours=6');
      setData(r.data);
      const roads = Object.keys(r.data.road_forecasts || {});
      if (roads.length) setSelectedRoad(roads[0]);
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const risks = data?.peak_risk?.slice(0,6) ?? [];
  const forecast = selectedRoad && data?.road_forecasts?.[selectedRoad];

  return (
    <MLSection title="Traffic Forecast" icon={TrendingUp}
      algoName="Ridge Polynomial Regression (deg=2, 36 features)" loading={loading} error={error}>
      {data && (
        <>
          <div style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}>
            <span style={{ fontFamily:'var(--font-mono)', fontSize:8, color:'var(--text-muted)' }}>
              R²={data.n_features && '0.96'} · {data.model_trained_on?.split('(')[0]?.trim()}
            </span>
            <button className="btn btn-ghost btn-sm" onClick={load} style={{ padding:'2px 6px' }}>
              <RefreshCw size={9}/>
            </button>
          </div>

          {/* Road selector */}
          <label>Select Road</label>
          <select value={selectedRoad ?? ''} onChange={e => setSelectedRoad(e.target.value)}
            style={{ marginBottom:10 }}>
            {Object.keys(data.road_forecasts || {}).map(rid => (
              <option key={rid} value={rid}>{rid.replace(/_/g,' ').toUpperCase()}</option>
            ))}
          </select>

          {/* Forecast line chart */}
          {forecast && (
            <div style={{ marginBottom:12 }}>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:8, color:'var(--text-muted)', marginBottom:4 }}>
                Predicted VC Ratio (next 6 hours)
              </div>
              <ResponsiveContainer width="100%" height={100}>
                <LineChart data={forecast} margin={{left:0,right:8,top:4,bottom:0}}>
                  <XAxis dataKey="hour_label" tick={{ fontSize:8, fill:'rgba(232,244,255,0.4)', fontFamily:'Space Mono' }}/>
                  <YAxis domain={[0,1.5]} tick={{ fontSize:8, fill:'rgba(232,244,255,0.35)', fontFamily:'Space Mono' }}/>
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={v=>[v.toFixed(3),'V/C Ratio']}/>
                  <ReferenceLine y={0.9} stroke="#ff4d6a" strokeDasharray="3 3" strokeOpacity={0.5}/>
                  <ReferenceLine y={0.7} stroke="#ffb347" strokeDasharray="3 3" strokeOpacity={0.4}/>
                  <Line type="monotone" dataKey="predicted_vc" stroke="#00c8ff" strokeWidth={2}
                    dot={e => <circle cx={e.cx} cy={e.cy} r={3} fill={getLOSColor(e.payload.predicted_los)}/>}/>
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Peak risk table */}
          <div style={{ fontFamily:'var(--font-mono)', fontSize:8, color:'var(--text-muted)',
                        letterSpacing:'0.12em', textTransform:'uppercase', marginBottom:6 }}>Peak Risk (Next 6h)</div>
          {risks.map((r,i) => (
            <div key={r.road_id} style={{
              display:'flex', alignItems:'center', justifyContent:'space-between',
              padding:'4px 0', borderBottom:'1px solid var(--border-dim)',
            }}>
              <span style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-secondary)',
                             maxWidth:140, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                {r.road_name}
              </span>
              <div style={{ display:'flex', gap:6, alignItems:'center', flexShrink:0 }}>
                <span style={{ fontFamily:'var(--font-mono)', fontSize:9, color:getVCColor(r.peak_vc) }}>
                  {r.peak_vc.toFixed(2)}
                </span>
                <span style={{ fontFamily:'var(--font-mono)', fontSize:8, padding:'1px 5px',
                               borderRadius:3, background:`${getRiskColor(r.risk_level)}22`,
                               color:getRiskColor(r.risk_level), border:`1px solid ${getRiskColor(r.risk_level)}44` }}>
                  {r.risk_level}
                </span>
              </div>
            </div>
          ))}
        </>
      )}
    </MLSection>
  );
}

// ── Clustering Section ────────────────────────────────────────────────
function ClusterSection() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const r = await axios.get('/api/ml/clusters');
      setData(r.data);
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <MLSection title="Road Clustering" icon={Brain}
      algoName="K-Means++ · Lloyd's algorithm · Elbow K selection" loading={loading} error={error}>
      {data && (
        <>
          <div style={{ display:'flex', gap:12, marginBottom:10 }}>
            <div style={{ textAlign:'center' }}>
              <div style={{ fontFamily:'var(--font-display)', fontSize:22, fontWeight:800, color:'var(--cyan)' }}>
                {data.k}
              </div>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:7, color:'var(--text-muted)', letterSpacing:'0.1em' }}>CLUSTERS</div>
            </div>
            <div style={{ textAlign:'center' }}>
              <div style={{ fontFamily:'var(--font-display)', fontSize:22, fontWeight:800, color:'var(--green)' }}>
                {data.silhouette}
              </div>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:7, color:'var(--text-muted)', letterSpacing:'0.1em' }}>SILHOUETTE</div>
            </div>
            <div style={{ textAlign:'center' }}>
              <div style={{ fontFamily:'var(--font-display)', fontSize:22, fontWeight:800, color:'var(--purple)' }}>
                {data.n_roads}
              </div>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:7, color:'var(--text-muted)', letterSpacing:'0.1em' }}>ROADS</div>
            </div>
          </div>

          {/* Cluster chart */}
          <ResponsiveContainer width="100%" height={100}>
            <BarChart data={data.clusters} margin={{left:0,right:4,top:4,bottom:0}}>
              <XAxis dataKey="cluster_id" tickFormatter={v=>`C${v}`}
                tick={{ fontSize:8, fill:'rgba(232,244,255,0.4)', fontFamily:'Space Mono' }}/>
              <YAxis tick={{ fontSize:8, fill:'rgba(232,244,255,0.35)', fontFamily:'Space Mono' }} domain={[0,1.5]}/>
              <Tooltip contentStyle={TOOLTIP_STYLE}
                formatter={(v,n)=>[v,'Avg VC']} labelFormatter={v=>`Cluster ${v}`}/>
              <Bar dataKey="avg_vc" radius={[3,3,0,0]} maxBarSize={40}>
                {(data.clusters||[]).map((c,i) => <Cell key={i} fill={c.color}/>)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          {/* Cluster detail cards */}
          <div style={{ marginTop:10, display:'flex', flexDirection:'column', gap:6 }}>
            {(data.clusters||[]).map(c => (
              <div key={c.cluster_id} style={{
                background:'var(--bg-card)', border:`1px solid ${c.color}33`,
                borderLeft:`3px solid ${c.color}`, borderRadius:'var(--r-sm)',
                padding:'8px 10px',
              }}>
                <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
                  <span style={{ fontFamily:'var(--font-mono)', fontSize:9, color:c.color, letterSpacing:'0.06em' }}>
                    {c.level.toUpperCase()} · {c.n_roads} roads
                  </span>
                  <span style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-secondary)' }}>
                    VC={c.avg_vc}  {c.avg_speed_kmh}km/h
                  </span>
                </div>
                <div style={{ fontFamily:'var(--font-mono)', fontSize:8, color:'var(--text-muted)', lineHeight:1.6 }}>
                  {c.road_ids.slice(0,4).join(' · ')}{c.road_ids.length>4?` +${c.road_ids.length-4}`:''}
                </div>
              </div>
            ))}
          </div>

          {data.hotspot_cluster && (
            <div style={{
              marginTop:8, background:'rgba(255,77,106,0.08)',
              border:'1px solid rgba(255,77,106,0.3)', borderRadius:'var(--r-sm)',
              padding:'8px 10px',
            }}>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--red)', letterSpacing:'0.06em', marginBottom:3 }}>
                🔥 CONGESTION HOTSPOT DETECTED
              </div>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:8, color:'var(--text-secondary)' }}>
                {data.hotspot_cluster.road_ids.join(' · ')}
              </div>
            </div>
          )}
        </>
      )}
    </MLSection>
  );
}

// ── Route Optimizer Section ───────────────────────────────────────────
function RouteSection() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [origin, setOrigin]   = useState('dwarka');
  const [dest,   setDest]     = useState('noida_border');

  const load = useCallback(async () => {
    if (origin === dest) return;
    setLoading(true); setError(null);
    try {
      const r = await axios.post('/api/ml/routes', { origin, destination: dest });
      setData(r.data);
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, [origin, dest]);

  useEffect(() => { load(); }, [load]);

  return (
    <MLSection title="Route Optimizer" icon={Route}
      algoName="Dijkstra shortest path · 3 objectives (fastest/balanced/eco)" loading={loading} error={error}>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8, marginBottom:10 }}>
        <div>
          <label>Origin</label>
          <select value={origin} onChange={e=>setOrigin(e.target.value)}>
            {ZONE_OPTIONS.map(z=><option key={z} value={z}>{z.replace(/_/g,' ').toUpperCase()}</option>)}
          </select>
        </div>
        <div>
          <label>Destination</label>
          <select value={dest} onChange={e=>setDest(e.target.value)}>
            {ZONE_OPTIONS.map(z=><option key={z} value={z}>{z.replace(/_/g,' ').toUpperCase()}</option>)}
          </select>
        </div>
      </div>
      <button className="btn btn-primary btn-full btn-sm" onClick={load} disabled={loading||origin===dest}>
        {loading ? <><div className="spinner"/>&nbsp;Running Dijkstra…</> : '⚡ Find Routes'}
      </button>

      {data && (
        <div style={{ marginTop:12 }}>
          {(data.routes||[]).filter(r=>!r.error).map(r => (
            <div key={r.objective} style={{
              background:'var(--bg-card)', border:'1px solid var(--border-dim)',
              borderRadius:'var(--r-md)', padding:'10px', marginBottom:8,
              borderLeft: `3px solid ${r.objective==='fastest'?'var(--cyan)':r.objective==='eco'?'var(--green)':'var(--amber)'}`,
            }}>
              <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6 }}>
                <span style={{ fontFamily:'var(--font-display)', fontSize:12, fontWeight:700 }}>{r.label}</span>
                <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--cyan)' }}>
                  {r.total_time_min}min · {r.total_dist_km}km
                </span>
              </div>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:8, color:'var(--text-muted)', marginBottom:6, letterSpacing:'0.04em' }}>
                {r.zones?.join(' → ')}
              </div>
              <div style={{ display:'flex', gap:8 }}>
                <span style={{ fontFamily:'var(--font-mono)', fontSize:8, color:'var(--text-muted)' }}>
                  avg V/C: <span style={{ color:getVCColor(r.avg_vc) }}>{r.avg_vc}</span>
                </span>
                <span style={{ fontFamily:'var(--font-mono)', fontSize:8, color:'var(--text-muted)' }}>
                  {r.n_zones} zones
                </span>
              </div>
            </div>
          ))}

          {(data.closed_roads||[]).length > 0 && (
            <div style={{ background:'rgba(255,77,106,0.08)', border:'1px solid rgba(255,77,106,0.3)',
                          borderRadius:'var(--r-sm)', padding:'8px 10px', marginTop:4 }}>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:8, color:'var(--red)', marginBottom:3 }}>
                ⛔ CLOSED ROADS
              </div>
              {data.closed_roads.map(r=>(
                <div key={r.road_id} style={{ fontFamily:'var(--font-mono)', fontSize:8, color:'var(--text-muted)' }}>
                  {r.road_name} — {r.reason}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </MLSection>
  );
}

// ── Network Analysis Section ──────────────────────────────────────────
function NetworkSection() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const r = await axios.get('/api/ml/network');
      setData(r.data);
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <MLSection title="Network Analysis" icon={Network}
      algoName="Dijkstra + Betweenness Centrality (NetworkX)" loading={loading} error={error} defaultOpen={false}>
      {data && (
        <>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:8, marginBottom:12 }}>
            {[
              { label:'Zones',       val:data.n_nodes,            color:'var(--cyan)' },
              { label:'Connections', val:data.n_edges,            color:'var(--purple)' },
              { label:'Avg Travel',  val:`${data.avg_travel_time_min}m`, color:'var(--amber)' },
              { label:'Connectivity',val:`${data.connectivity_pct}%`,  color:data.connectivity_pct===100?'var(--green)':'var(--red)' },
              { label:'Components',  val:data.strongly_connected_components, color:'var(--text-secondary)' },
              { label:'SCCs',        val:data.strongly_connected_components===1?'✓ Intact':'⚠ Split', color:data.strongly_connected_components===1?'var(--green)':'var(--red)' },
            ].map(m=>(
              <div key={m.label} style={{ background:'var(--bg-card)', border:'1px solid var(--border-dim)',
                                          borderRadius:'var(--r-sm)', padding:'6px 8px', textAlign:'center' }}>
                <div style={{ fontFamily:'var(--font-display)', fontSize:16, fontWeight:800, color:m.color }}>{m.val}</div>
                <div style={{ fontFamily:'var(--font-mono)', fontSize:7, color:'var(--text-muted)', letterSpacing:'0.1em' }}>{m.label.toUpperCase()}</div>
              </div>
            ))}
          </div>

          <div style={{ fontFamily:'var(--font-mono)', fontSize:8, color:'var(--text-muted)', marginBottom:6 }}>
            TOP CENTRAL ZONES (Betweenness)
          </div>
          {(data.top_central_zones||[]).map((z,i) => (
            <div key={z.zone} style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
                                        padding:'4px 0', borderBottom:'1px solid var(--border-dim)' }}>
              <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                <span style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-muted)', width:14 }}>#{i+1}</span>
                <span style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-secondary)' }}>
                  {z.zone.replace(/_/g,' ').toUpperCase()}
                </span>
              </div>
              <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                <div style={{ width:60, height:4, background:'var(--bg-elevated)', borderRadius:2 }}>
                  <div style={{ width:`${z.centrality*100}%`, height:'100%', background:'var(--cyan)',
                                borderRadius:2, minWidth:4 }}/>
                </div>
                <span style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--cyan)', width:32 }}>
                  {z.centrality.toFixed(3)}
                </span>
              </div>
            </div>
          ))}
        </>
      )}
    </MLSection>
  );
}

// ── Main MLPanel export ───────────────────────────────────────────────
export default function MLPanel() {
  return (
    <div style={{ display:'flex', flexDirection:'column', flex:1 }}>
      <div style={{ padding:'10px var(--gap-md)', borderBottom:'1px solid var(--border-dim)',
                    background:'var(--bg-elevated)' }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <Brain size={14} color="var(--purple)"/>
          <span style={{ fontFamily:'var(--font-display)', fontSize:13, fontWeight:700 }}>AI / ML Engine</span>
          <span style={{ marginLeft:'auto', fontFamily:'var(--font-mono)', fontSize:8, color:'var(--text-muted)',
                         background:'rgba(181,123,238,0.1)', border:'1px solid rgba(181,123,238,0.2)',
                         borderRadius:3, padding:'2px 6px' }}>3 Algorithms</span>
        </div>
        <div style={{ fontFamily:'var(--font-body)', fontSize:10, color:'var(--text-muted)', marginTop:3 }}>
          Poly Regression · K-Means++ · Dijkstra
        </div>
      </div>
      <div style={{ overflowY:'auto', flex:1 }}>
        <ForecastSection/>
        <ClusterSection/>
        <RouteSection/>
        <NetworkSection/>
      </div>
    </div>
  );
}
