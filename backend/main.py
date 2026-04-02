"""
AI Digital Twin of Delhi — FastAPI Backend
==========================================
Entry point: uvicorn main:app --reload --port 8000

Adapter layer bridges engine's internal data model to the frontend's API contract:
  Engine             →   Frontend / API
  ──────────────────────────────────────
  roads[]            →   road_states[]
  road.id            →   road_state.road_id
  road.congestion_ratio  → road_state.vc_ratio
  road.speed_kmh     →   road_state.effective_speed
  metrics            →   summary
  metrics.avg_congestion × 100 → summary.avg_congestion_pct
  metrics.avg_speed_kmh  → summary.avg_speed_kmph
  metrics.health_score   → summary.city_health_score
  weather.description    → weather.condition
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from data.delhi_network import ROADS, ZONES, get_scenario_presets
from data.live_fetcher import fetch_all_live_data
from simulation.engine import SimulationEngine


# ──────────────────────────────────────────────────────────────────────
#  App Bootstrap
# ──────────────────────────────────────────────────────────────────────

engine = SimulationEngine()
_live_cache: dict = {}
_ws_clients: list = []


@asynccontextmanager
async def lifespan(app):
    await _refresh_cache()
    yield


app = FastAPI(
    title="Delhi Digital Twin API",
    version="2.0.0",
    description="AI-powered city simulation engine for Delhi",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────
#  Request models
# ──────────────────────────────────────────────────────────────────────

class ScenarioRequest(BaseModel):
    scenario_id: str
    params: Optional[Dict[str, Any]] = {}


# ──────────────────────────────────────────────────────────────────────
#  Adapter helpers
# ──────────────────────────────────────────────────────────────────────

def _normalize_weather(w: dict) -> dict:
    if not w:
        return {}
    out = dict(w)
    out.setdefault("condition", w.get("description", "Clear"))
    out.setdefault("feels_like", w.get("temperature", 25))
    out.setdefault("visibility", int(w.get("visibility_km", 8) * 1000))
    out.setdefault("pressure", 1012)
    return out


def _normalize_road_states(roads: list) -> list:
    out = []
    for r in roads or []:
        out.append({
            "road_id":         r.get("id", ""),
            "road_name":       r.get("name", r.get("id", "")),
            "vc_ratio":        r.get("congestion_ratio", 0),
            "effective_speed": r.get("speed_kmh", 0),
            "los":             r.get("los", "C"),
            "volume":          r.get("volume", 0),
            "capacity":        r.get("capacity", 1),
            "travel_time_min": r.get("travel_time_min", 0),
            "emissions":       r.get("emissions", 0),
            "num_lanes":       r.get("num_lanes", 2),
            "road_type":       r.get("road_type", "arterial"),
            "length_km":       r.get("length_km", 1),
            "free_flow_speed": r.get("free_flow_speed", 60),
            "is_closed":       r.get("is_closed", False),
            "is_construction": r.get("is_construction", False),
            "is_flooded":      r.get("is_flooded", False),
            "start_point":     [r.get("from_lat", 0), r.get("from_lng", 0)],
            "end_point":       [r.get("to_lat", 0),   r.get("to_lng", 0)],
        })
    return out


def _normalize_summary(metrics: dict) -> dict:
    if not metrics:
        return {}
    return {
        "avg_congestion_pct":  round(metrics.get("avg_congestion", 0) * 100, 1),
        "avg_aqi":             metrics.get("avg_aqi", 0),
        "avg_speed_kmph":      metrics.get("avg_speed_kmh", 0),
        "city_health_score":   metrics.get("health_score", 50),
        "total_vehicles":      metrics.get("total_vehicles", 0),
        "critical_roads":      metrics.get("critical_roads", 0),
        "closed_roads":        metrics.get("closed_roads", 0),
        "flooded_roads":       metrics.get("flooded_roads", 0),
        "los_distribution":    metrics.get("los_distribution", {}),
    }


def _normalize_state(raw: dict) -> dict:
    return {
        "timestamp":   raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "weather":     _normalize_weather(raw.get("weather", {})),
        "zones":       raw.get("zones", []),
        "roads":       raw.get("roads", []),
        "road_states": _normalize_road_states(raw.get("roads", [])),
        "summary":     _normalize_summary(raw.get("metrics", {})),
        "data_sources":raw.get("data_sources", {}),
    }


def _resolve_scenario(scenario_id: str, params: dict) -> dict:
    presets = get_scenario_presets()

    PARAM_MAP = {
        "surge_pct":       "surge_percentage",
        "crowd_size":      "crowd_size",
        "efficiency_gain": "efficiency_gain",
        "lanes_blocked":   "lanes_closed",
        "ev_pct":          "ev_percentage",
        "policy":          "reduction_type",
        "intensity":       "_intensity",
        "road_id":         "road_id",
        "zone":            "venue_zone",
    }

    TYPE_MAP = {
        "rush_hour":          "traffic_surge",
        "nh48_closure":       "road_closure",
        "heavy_rain":         "rainfall",
        "republic_day":       "event_crowd",
        "adaptive_signals":   "signal_optimization",
        "construction_ring":  "construction",
        "odd_even":           "emission_reduction",
        "road_closure":       "road_closure",
        "traffic_surge":      "traffic_surge",
        "rainfall":           "rainfall",
        "event_crowd":        "event_crowd",
        "signal_optimization":"signal_optimization",
        "construction":       "construction",
        "emission_reduction": "emission_reduction",
    }

    RAIN_MM = {"light": 8, "moderate": 25, "heavy": 50, "very_heavy": 80}

    base = dict(presets[scenario_id]) if scenario_id in presets else {}
    base["type"] = TYPE_MAP.get(scenario_id, scenario_id)

    for fk, ek in PARAM_MAP.items():
        if fk in (params or {}):
            val = params[fk]
            if fk == "intensity":
                base["rainfall_mm"] = RAIN_MM.get(val, 25)
            elif not ek.startswith("_"):
                base[ek] = val

    for k, v in (params or {}).items():
        if k not in PARAM_MAP:
            base.setdefault(k, v)

    return base


# ──────────────────────────────────────────────────────────────────────
#  Cache
# ──────────────────────────────────────────────────────────────────────

async def _refresh_cache():
    global _live_cache
    raw = await fetch_all_live_data(ROADS, ZONES)
    _live_cache = raw
    _live_cache["last_refresh"] = datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────────────
#  REST Endpoints
# ──────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"name": "Delhi AI Digital Twin", "version": "2.0.0",
            "city": settings.CITY_NAME, "zones": len(ZONES), "roads": len(ROADS)}


@app.get("/api/city/state")
async def get_city_state(refresh: bool = Query(False)):
    if refresh or not _live_cache:
        await _refresh_cache()
    raw = engine.get_base_state(
        weather=_live_cache.get("weather"),
        live_traffic=_live_cache.get("traffic_volumes"),
        live_aqi=_live_cache.get("aqi"),
    )
    raw["data_sources"] = {
        "weather": _live_cache.get("weather", {}).get("source", "synthetic"),
        "traffic": "live" if _live_cache.get("is_live_traffic") else "synthetic",
        "aqi":     "openaq" if _live_cache.get("is_live_aqi") else "synthetic",
        "last_refresh": _live_cache.get("last_refresh"),
    }
    return _normalize_state(raw)


@app.get("/api/city/zones")
async def get_zones():
    return {"zones": list(ZONES.values())}


@app.get("/api/city/roads")
async def get_roads():
    roads_out = []
    for rid, r in ROADS.items():
        roads_out.append({
            **r, "road_id": rid,
            "start_point": [r.get("from_lat", 0), r.get("from_lng", 0)],
            "end_point":   [r.get("to_lat", 0),   r.get("to_lng", 0)],
        })
    return {"roads": roads_out}


@app.post("/api/simulation/run")
async def run_simulation(req: ScenarioRequest):
    if not _live_cache:
        await _refresh_cache()

    scenario_dict = _resolve_scenario(req.scenario_id, req.params or {})

    raw = engine.run_scenario(
        scenario=scenario_dict,
        weather=_live_cache.get("weather"),
        live_traffic=_live_cache.get("traffic_volumes"),
        live_aqi=_live_cache.get("aqi"),
    )

    impact = dict(raw.get("impact", {}))
    impact.setdefault("speed_change_kmph", impact.get("speed_change_kmh", 0))
    impact.setdefault("affected_roads", [])

    return {
        "scenario_id":     req.scenario_id,
        "scenario":        scenario_dict,
        "before":          _normalize_state(raw["before"]),
        "after":           _normalize_state(raw["after"]),
        "impact":          impact,
        "recommendations": raw.get("recommendations", []),
    }


@app.get("/api/simulation/scenarios")
async def get_scenarios():
    return [{"id": sid, **s} for sid, s in get_scenario_presets().items()]


@app.get("/api/live/weather")
async def get_live_weather():
    if not _live_cache:
        await _refresh_cache()
    return _normalize_weather(_live_cache.get("weather", {}))


@app.get("/api/live/traffic")
async def get_live_traffic():
    if not _live_cache:
        await _refresh_cache()
    return {"traffic": _live_cache.get("traffic_volumes", {})}


@app.get("/api/live/aqi")
async def get_live_aqi():
    if not _live_cache:
        await _refresh_cache()
    return {"aqi": _live_cache.get("aqi", {})}


@app.post("/api/live/refresh")
async def refresh_live():
    await _refresh_cache()
    return {"status": "refreshed", "timestamp": _live_cache.get("last_refresh")}


# ──────────────────────────────────────────────────────────────────────
#  WebSocket
# ──────────────────────────────────────────────────────────────────────

@app.websocket("/ws/city")
async def websocket_city(ws: WebSocket):
    await ws.accept()
    _ws_clients.append(ws)
    try:
        while True:
            if not _live_cache:
                await _refresh_cache()
            raw = engine.get_base_state(
                weather=_live_cache.get("weather"),
                live_traffic=_live_cache.get("traffic_volumes"),
                live_aqi=_live_cache.get("aqi"),
            )
            state = _normalize_state(raw)
            state["ws_update"] = True
            await ws.send_json(state)
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        _ws_clients.remove(ws)
    except Exception:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


# ──────────────────────────────────────────────────────────────────────
#  ML Endpoints
# ──────────────────────────────────────────────────────────────────────

# Lazy-load ML models so they don't slow startup
_predictor   = None
_clusterer   = None
_optimizer   = None


def _get_predictor():
    global _predictor
    if _predictor is None:
        from ml.predictor import TrafficPredictor
        roads_list   = list(ROADS.values())
        _predictor   = TrafficPredictor(roads_list)
        _predictor.train()
    return _predictor


def _get_clusterer():
    global _clusterer
    if _clusterer is None:
        from ml.kmeans import RoadCongestionClusterer
        _clusterer = RoadCongestionClusterer()
    return _clusterer


def _get_optimizer():
    global _optimizer
    if _optimizer is None:
        from ml.router import RouteOptimizer
        _optimizer = RouteOptimizer(ROADS)
    return _optimizer


@app.get("/api/ml/forecast")
async def ml_forecast(hours: int = Query(6, ge=1, le=12)):
    """
    AI Traffic Forecast — Polynomial Regression (degree 2, Ridge regularised).
    Predicts traffic volume + LOS for each road for the next `hours` hours.
    Returns: per-road forecast + peak risk assessment.
    """
    if not _live_cache:
        await _refresh_cache()

    predictor  = _get_predictor()
    weather    = _live_cache.get("weather", {})
    forecast   = predictor.predict_next_hours(hours, weather)
    risks      = predictor.peak_risk_assessment(weather)

    return {
        "algorithm":    "Ridge Polynomial Regression (degree=2, λ=0.1)",
        "description":  "Traffic volume prediction using time cyclical encoding + weather features",
        "features":     ["hour_sin", "hour_cos", "is_peak", "weekday_factor",
                         "temperature_norm", "rain_factor", "road_capacity"],
        "n_features":   36,
        "forecast_hours": hours,
        "road_forecasts": forecast,
        "peak_risk":    risks[:10],
        "model_trained_on": "14-day × 24-hour Delhi synthetic traffic matrix (6720 samples)",
    }


@app.get("/api/ml/clusters")
async def ml_clusters():
    """
    AI Road Clustering — K-Means++ with automatic K selection (elbow method).
    Groups roads by congestion profile: VC ratio, speed drop, road type, emissions.
    Returns: cluster assignments + congestion hotspot identification.
    """
    if not _live_cache:
        await _refresh_cache()

    raw        = engine.get_base_state(
        weather=_live_cache.get("weather"),
        live_traffic=_live_cache.get("traffic_volumes"),
        live_aqi=_live_cache.get("aqi"),
    )
    road_states = _normalize_road_states(raw.get("roads", []))

    clusterer  = _get_clusterer()
    result     = clusterer.fit(road_states, ROADS)

    return {
        "algorithm":   "K-Means++ (Lloyd's algorithm, elbow K selection)",
        "description": "Road segment grouping by: VC ratio, speed drop, road type weight, emission index",
        "features":    ["vc_ratio", "norm_volume", "road_type_weight",
                        "speed_drop_ratio", "emission_index", "is_freeway"],
        **result,
    }


class RouteRequest(BaseModel):
    origin:      str
    destination: str


@app.post("/api/ml/routes")
async def ml_routes(req: RouteRequest):
    """
    AI Route Optimizer — Dijkstra shortest path (3 objectives: fastest/balanced/eco).
    Edge weights = BPR travel time × road type emission penalty.
    Returns primary + alternative routes with full road-by-road breakdown.
    """
    if not _live_cache:
        await _refresh_cache()

    raw        = engine.get_base_state(
        weather=_live_cache.get("weather"),
        live_traffic=_live_cache.get("traffic_volumes"),
        live_aqi=_live_cache.get("aqi"),
    )
    road_states = _normalize_road_states(raw.get("roads", []))

    optimizer  = _get_optimizer()
    result     = optimizer.find_routes(req.origin, req.destination, road_states)

    return {
        "algorithm":   "Dijkstra shortest path (NetworkX) — 3 objectives",
        "description": "Edge weight = BPR travel time × emission penalty factor",
        **result,
    }


@app.get("/api/ml/network")
async def ml_network():
    """
    Network analysis — Betweenness Centrality + connectivity stats.
    Returns: most critical zones, avg travel time, isolation check.
    """
    if not _live_cache:
        await _refresh_cache()

    raw        = engine.get_base_state(
        weather=_live_cache.get("weather"),
        live_traffic=_live_cache.get("traffic_volumes"),
        live_aqi=_live_cache.get("aqi"),
    )
    road_states = _normalize_road_states(raw.get("roads", []))

    optimizer  = _get_optimizer()
    summary    = optimizer.network_summary(road_states)

    return {
        "algorithm": "Dijkstra + Betweenness Centrality (NetworkX)",
        "description": "Network-wide reachability and zone criticality analysis",
        **summary,
    }
