import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getCityState,
  getScenarioPresets,
  runSimulation,
  refreshLiveData,
  createCityWebSocket,
} from '../api/cityApi';

export function useCityData() {
  const [cityState,   setCityState]   = useState(null);
  const [scenarios,   setScenarios]   = useState([]);
  const [simResult,   setSimResult]   = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [simLoading,  setSimLoading]  = useState(false);
  const [error,       setError]       = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const wsRef = useRef(null);

  // ── Initial load ─────────────────────────────────────────────────
  const loadCity = useCallback(async (refresh = false) => {
    try {
      setLoading(true);
      setError(null);
      const [state, presets] = await Promise.all([
        getCityState(refresh),
        getScenarioPresets(),
      ]);
      setCityState(state);
      setScenarios(presets);
      setLastUpdated(new Date());
    } catch (e) {
      setError(e.message || 'Failed to load city data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadCity(); }, [loadCity]);

  // ── WebSocket for live updates ────────────────────────────────────
  useEffect(() => {
    const connect = () => {
      wsRef.current = createCityWebSocket(
        (data) => {
          setCityState(data);
          setLastUpdated(new Date());
        },
        () => {
          // Reconnect after 5 seconds on error
          setTimeout(connect, 5000);
        }
      );
    };

    const timeout = setTimeout(connect, 2000); // connect after initial load
    return () => {
      clearTimeout(timeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // ── Run scenario ──────────────────────────────────────────────────
  const simulate = useCallback(async (scenarioId, params = {}) => {
    try {
      setSimLoading(true);
      setError(null);
      const result = await runSimulation(scenarioId, params);
      setSimResult(result);
      return result;
    } catch (e) {
      setError(e.message || 'Simulation failed');
      return null;
    } finally {
      setSimLoading(false);
    }
  }, []);

  // ── Clear simulation ──────────────────────────────────────────────
  const clearSim = useCallback(() => setSimResult(null), []);

  // ── Force refresh ─────────────────────────────────────────────────
  const refresh = useCallback(async () => {
    try {
      await refreshLiveData();
      await loadCity(true);
    } catch (e) {
      setError(e.message);
    }
  }, [loadCity]);

  return {
    cityState,
    scenarios,
    simResult,
    loading,
    simLoading,
    error,
    lastUpdated,
    simulate,
    clearSim,
    refresh,
  };
}
