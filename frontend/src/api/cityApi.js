import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── City State ──────────────────────────────────────────────────────
export const getCityState = (refresh = false) =>
  api.get(`/city/state?refresh=${refresh}`).then(r => r.data);

export const getZones = () =>
  api.get('/city/zones').then(r => r.data);

export const getRoads = () =>
  api.get('/city/roads').then(r => r.data);

// ── Simulation ──────────────────────────────────────────────────────
export const runSimulation = (scenarioId, params = {}) =>
  api.post('/simulation/run', { scenario_id: scenarioId, params }).then(r => r.data);

export const getScenarioPresets = () =>
  api.get('/simulation/scenarios').then(r => r.data);

// ── Live Data ───────────────────────────────────────────────────────
export const getLiveWeather = () =>
  api.get('/live/weather').then(r => r.data);

export const getLiveTraffic = () =>
  api.get('/live/traffic').then(r => r.data);

export const getLiveAqi = () =>
  api.get('/live/aqi').then(r => r.data);

export const refreshLiveData = () =>
  api.post('/live/refresh').then(r => r.data);

// ── WebSocket ───────────────────────────────────────────────────────
export const createCityWebSocket = (onMessage, onError) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws/city`);
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)); } catch { /* ignore */ }
  };
  ws.onerror = onError;
  ws.onclose = () => console.log('WebSocket closed');
  return ws;
};

export default api;
