import React, { useEffect, useRef, useCallback } from 'react';
import L from 'leaflet';

const ZONE_RINGS = {
  cp:              { center: [28.6315, 77.2167], radius: 1900,  color: '#00c8ff', name: 'Connaught Place' },
  old_delhi:       { center: [28.6562, 77.2310], radius: 2600,  color: '#ffb347', name: 'Old Delhi' },
  dwarka:          { center: [28.5921, 77.0460], radius: 3100,  color: '#b57bee', name: 'Dwarka' },
  rohini:          { center: [28.7495, 77.1134], radius: 2900,  color: '#00e5a0', name: 'Rohini' },
  noida_border:    { center: [28.5355, 77.3910], radius: 2300,  color: '#ff4d6a', name: 'Noida Border' },
  gurugram_border: { center: [28.4595, 77.0266], radius: 2600,  color: '#ffb347', name: 'Gurugram Border' },
  south_delhi:     { center: [28.5244, 77.1855], radius: 3100,  color: '#00c8ff', name: 'South Delhi' },
  east_delhi:      { center: [28.6508, 77.3152], radius: 2500,  color: '#b57bee', name: 'East Delhi' },
  north_delhi:     { center: [28.7041, 77.1025], radius: 2500,  color: '#00e5a0', name: 'North Delhi' },
  janakpuri:       { center: [28.6219, 77.0819], radius: 2000,  color: '#ff4d6a', name: 'Janakpuri' },
  lajpat_nagar:    { center: [28.5677, 77.2433], radius: 1800,  color: '#00c8ff', name: 'Lajpat Nagar' },
  nehru_place:     { center: [28.5491, 77.2518], radius: 1600,  color: '#ffb347', name: 'Nehru Place' },
};

function getTrafficColor(vc) {
  if (vc < 0.50) return '#00e400';
  if (vc < 0.70) return '#7fe800';
  if (vc < 0.85) return '#e6e600';
  if (vc < 0.95) return '#ff7e00';
  if (vc < 1.10) return '#ff2222';
  return '#8f3f97';
}

function getRoadWeight(road_type) {
  return { expressway: 7, highway: 6, arterial: 4, collector: 3 }[road_type] ?? 3;
}

function buildTooltip(rs) {
  const color = getTrafficColor(rs.vc_ratio);
  const extras = [
    rs.is_closed       ? '<span style="color:#ff4d6a;grid-column:1/-1">⛔ ROAD CLOSED</span>' : '',
    rs.is_construction ? '<span style="color:#ffb347;grid-column:1/-1">🏗️ CONSTRUCTION ZONE</span>' : '',
    rs.is_flooded      ? '<span style="color:#00c8ff;grid-column:1/-1">💧 FLOODED</span>' : '',
  ].filter(Boolean).join('');
  return `<div style="font-family:'Space Mono',monospace;background:#0c1524;border:1px solid rgba(0,200,255,0.4);border-radius:6px;padding:10px 14px;font-size:10px;color:#e8f4ff;min-width:190px;box-shadow:0 4px 20px rgba(0,0,0,0.7)">
    <div style="font-family:'Syne',sans-serif;font-size:12px;font-weight:700;margin-bottom:8px;color:${color}">${rs.road_name || rs.road_id}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;color:rgba(232,244,255,0.7)">
      <span>V/C Ratio</span><span style="color:${color};font-weight:700">${rs.vc_ratio?.toFixed(2) ?? '—'}</span>
      <span>Speed</span><span style="color:#fff">${Math.round(rs.effective_speed ?? 0)} km/h</span>
      <span>LOS</span><span style="color:${color};font-weight:700">${rs.los ?? '—'}</span>
      <span>Lanes</span><span style="color:#fff">${rs.num_lanes ?? '—'}</span>
      <span>Capacity</span><span style="color:#fff">${rs.capacity?.toLocaleString() ?? '—'} PCU/hr</span>
      <span>Type</span><span style="color:#fff;text-transform:uppercase">${rs.road_type || '—'}</span>
      ${extras}
    </div>
  </div>`;
}

export default function MapView({ cityState, simResult }) {
  const mapRef    = useRef(null);
  const layersRef = useRef({ zones: [], roads: [] });

  useEffect(() => {
    if (mapRef.current) return;
    mapRef.current = L.map('map-container', {
      center: [28.6139, 77.2090],
      zoom: 11,
      zoomControl: false,
      attributionControl: false,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18, opacity: 0.5, className: 'dark-tiles',
    }).addTo(mapRef.current);

    if (!document.getElementById('dark-tile-style')) {
      const s = document.createElement('style');
      s.id = 'dark-tile-style';
      s.textContent = '.dark-tiles { filter: brightness(0.3) saturate(0.4) hue-rotate(200deg); }';
      document.head.appendChild(s);
    }

    L.control.zoom({ position: 'bottomright' }).addTo(mapRef.current);

    Object.entries(ZONE_RINGS).forEach(([id, z]) => {
      const circle = L.circle(z.center, {
        radius: z.radius, color: z.color, fillColor: z.color,
        fillOpacity: 0.04, weight: 1, opacity: 0.22, dashArray: '4 6',
      }).addTo(mapRef.current);

      const label = L.marker(z.center, {
        icon: L.divIcon({
          className: '',
          html: `<div style="font-family:'Space Mono',monospace;font-size:9px;color:${z.color};white-space:nowrap;opacity:0.7;text-shadow:0 0 10px ${z.color};letter-spacing:0.08em;pointer-events:none;transform:translateX(-50%)">${z.name.toUpperCase()}</div>`,
          iconAnchor: [0, 0],
        }),
        interactive: false,
      }).addTo(mapRef.current);

      layersRef.current.zones.push(circle, label);
    });

    return () => {
      if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }
    };
  }, []);

  const drawRoads = useCallback((roadStates, highlightIds) => {
    const map = mapRef.current;
    if (!map || !roadStates?.length) return;

    layersRef.current.roads.forEach(l => { try { map.removeLayer(l); } catch {} });
    layersRef.current.roads = [];

    roadStates.forEach(rs => {
      const sp = rs.start_point, ep = rs.end_point;
      if (!sp || !ep || (sp[0] === 0 && sp[1] === 0)) return;

      const color   = rs.is_closed ? '#444' : getTrafficColor(rs.vc_ratio);
      const weight  = getRoadWeight(rs.road_type);
      const isHL    = highlightIds?.includes(rs.road_id);
      const opacity = rs.is_closed ? 0.3 : isHL ? 1.0 : 0.78;

      const glow = L.polyline([sp, ep], { color, weight: weight + 8, opacity: isHL ? 0.45 : 0.08, lineCap: 'round' }).addTo(map);
      const line = L.polyline([sp, ep], {
        color: isHL ? '#ffffff' : color,
        weight: isHL ? weight + 3 : weight,
        opacity,
        lineCap: 'round',
        dashArray: rs.is_closed ? '6 4' : rs.is_construction ? '8 4' : null,
      }).addTo(map);
      line.bindTooltip(buildTooltip(rs), { sticky: true, opacity: 1 });
      layersRef.current.roads.push(glow, line);
    });
  }, []);

  useEffect(() => {
    if (!cityState?.road_states) return;
    const roadStates  = simResult?.after?.road_states ?? cityState.road_states;
    const highlightIds = simResult?.impact?.affected_zones?.map(z => z.id) ?? null;
    drawRoads(roadStates, highlightIds);
  }, [cityState, simResult, drawRoads]);

  return <div id="map-container" style={{ width: '100%', height: '100%' }} />;
}
