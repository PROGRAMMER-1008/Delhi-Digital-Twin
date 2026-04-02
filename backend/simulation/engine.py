"""
Simulation Engine
=================
Implements the Bureau of Public Roads (BPR) traffic flow model,
Gaussian plume pollution dispersion, and city-state management.

BPR function:  t(v) = t₀ · (1 + 0.15·(v/c)⁴)
"""

import copy
import math
import random
import numpy as np
import networkx as nx
from datetime import datetime, timezone
from typing import Dict, List, Optional

from data.delhi_network import ZONES, ROADS, get_city_graph
from simulation.recommender import RecommendationEngine


# ─────────────────────────────────────────────────────────────────────
#  TRAFFIC FLOW MODULE (BPR)
# ─────────────────────────────────────────────────────────────────────

class TrafficFlow:
    BPR_ALPHA = 0.15
    BPR_BETA = 4

    @staticmethod
    def bpr(t0: float, volume: float, capacity: float) -> float:
        if capacity <= 0:
            return t0 * 10
        r = volume / capacity
        return t0 * (1 + TrafficFlow.BPR_ALPHA * r ** TrafficFlow.BPR_BETA)

    @staticmethod
    def vc(volume: float, capacity: float) -> float:
        return volume / capacity if capacity > 0 else 9.99

    @staticmethod
    def los(vc_ratio: float) -> str:
        """Highway Capacity Manual Level of Service A–F."""
        if vc_ratio < 0.35: return "A"
        if vc_ratio < 0.54: return "B"
        if vc_ratio < 0.77: return "C"
        if vc_ratio < 0.90: return "D"
        if vc_ratio < 1.00: return "E"
        return "F"

    @staticmethod
    def effective_speed(free_speed: float, vc_ratio: float, length_km: float = 1) -> float:
        factor = 1.0 / (1 + TrafficFlow.BPR_ALPHA * vc_ratio ** TrafficFlow.BPR_BETA)
        return max(4.0, free_speed * factor)


# ─────────────────────────────────────────────────────────────────────
#  POLLUTION MODULE (Gaussian dispersion)
# ─────────────────────────────────────────────────────────────────────

class PollutionModel:
    EMIT = {"highway": 0.75, "arterial": 1.20, "collector": 1.55, "local": 1.90}

    @classmethod
    def emissions(cls, volume: float, speed: float, road_type: str, length_km: float) -> float:
        ef = cls.EMIT.get(road_type, 1.2)
        if speed < 15:
            sf = 2.5 + (15 - speed) / 5
        elif speed < 30:
            sf = 1.8
        elif speed < 50:
            sf = 1.2
        elif speed < 70:
            sf = 1.0
        else:
            sf = 1.15
        return volume * ef * sf * length_km

    @staticmethod
    def weather_factor(wind_kmh: float, humidity_pct: float, temp_c: float) -> float:
        wf = max(0.25, 1.0 - wind_kmh * 0.05)
        hf = 1.0 + (humidity_pct - 50) * 0.008
        tf = 1.0 if temp_c > 15 else 1.2
        return round(wf * hf * tf, 3)

    @staticmethod
    def to_aqi(total_emissions: float, area_km2: float) -> float:
        density = total_emissions / max(area_km2, 0.1)
        return round(min(500, 50 + density * 0.14), 1)

    @staticmethod
    def category(aqi: float) -> str:
        if aqi <= 50:  return "Good"
        if aqi <= 100: return "Satisfactory"
        if aqi <= 200: return "Moderate"
        if aqi <= 300: return "Poor"
        if aqi <= 400: return "Very Poor"
        return "Severe"


# ─────────────────────────────────────────────────────────────────────
#  MAIN SIMULATION ENGINE
# ─────────────────────────────────────────────────────────────────────

class SimulationEngine:
    def __init__(self):
        self.tf = TrafficFlow()
        self.pm = PollutionModel()
        self.rec = RecommendationEngine()
        self.graph = get_city_graph()

    # ── Public API ────────────────────────────────

    def get_base_state(self,
                       weather: Optional[dict] = None,
                       live_traffic: Optional[dict] = None,
                       live_aqi: Optional[dict] = None) -> dict:
        """Return current city state, optionally incorporating live data."""
        w = weather or _default_weather()
        roads = self._build_roads(live_traffic, w)
        zones = self._build_zones(roads, w, live_aqi)
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "weather": w,
            "zones": zones,
            "roads": roads,
            "metrics": self._metrics(zones, roads),
        }

    def run_scenario(self,
                     scenario: dict,
                     weather: Optional[dict] = None,
                     live_traffic: Optional[dict] = None,
                     live_aqi: Optional[dict] = None) -> dict:
        """Main entry — run a scenario and return full before/after result."""
        before = self.get_base_state(weather, live_traffic, live_aqi)
        after = self._apply_scenario(copy.deepcopy(before), scenario)
        impact = self._impact(before, after)
        recs = self.rec.generate(scenario, before, after, self.graph)
        return {
            "scenario": scenario,
            "before": before,
            "after": after,
            "impact": impact,
            "recommendations": recs,
        }

    # ── Build state ───────────────────────────────

    def _build_roads(self, live_traffic, weather) -> List[dict]:
        out = []
        w_factor = self.pm.weather_factor(
            weather.get("wind_speed", 8),
            weather.get("humidity", 60),
            weather.get("temperature", 28),
        )
        for rid, r in ROADS.items():
            volume = live_traffic.get(rid, r["base_volume"]) if live_traffic else r["base_volume"]
            cap = r["capacity"]
            ff_time = (r["length_km"] / r["free_flow_speed"]) * 60
            vc = self.tf.vc(volume, cap)
            spd = self.tf.effective_speed(r["free_flow_speed"], vc)
            emit = self.pm.emissions(volume, spd, r["road_type"], r["length_km"])
            out.append({
                "id": rid,
                "name": r["name"],
                "from_zone": r["from_zone"],
                "to_zone": r["to_zone"],
                "from_lat": r["from_lat"], "from_lng": r["from_lng"],
                "to_lat": r["to_lat"],   "to_lng": r["to_lng"],
                "volume": int(volume),
                "capacity": int(cap),
                "congestion_ratio": round(min(vc, 2.0), 3),
                "travel_time_min": round(self.tf.bpr(ff_time, volume, cap), 1),
                "speed_kmh": round(spd, 1),
                "los": self.tf.los(vc),
                "emissions": round(emit, 2),
                "num_lanes": r["num_lanes"],
                "road_type": r["road_type"],
                "length_km": r["length_km"],
                "free_flow_speed": r["free_flow_speed"],
                "is_closed": False,
                "is_construction": False,
                "is_flooded": False,
            })
        return out

    def _build_zones(self, roads, weather, live_aqi) -> List[dict]:
        w_factor = self.pm.weather_factor(
            weather.get("wind_speed", 8),
            weather.get("humidity", 60),
            weather.get("temperature", 28),
        )
        out = []
        for zid, z in ZONES.items():
            conn = [r for r in roads if r["from_zone"] == zid or r["to_zone"] == zid]
            n = max(len(conn), 1)
            avg_vol = sum(r["volume"] for r in conn) // n
            avg_spd = sum(r["speed_kmh"] for r in conn) / n
            avg_vc  = sum(r["congestion_ratio"] for r in conn) / n
            emit    = sum(r["emissions"] for r in conn)
            t_aqi   = self.pm.to_aqi(emit, z["area_km2"])
            base_aqi = live_aqi.get(zid, z["base_aqi"]) if live_aqi else z["base_aqi"]
            aqi     = min(500, max(20, (base_aqi * 0.35 + t_aqi * 0.65) * w_factor))
            out.append({
                "id": zid,
                "name": z["name"],
                "lat": z["lat"],  "lng": z["lng"],
                "zone_type": z["zone_type"],
                "area_km2": z["area_km2"],
                "population": z.get("population", 0),
                "traffic_volume": int(avg_vol),
                "avg_speed_kmh": round(avg_spd, 1),
                "congestion_ratio": round(avg_vc, 3),
                "aqi": round(aqi, 1),
                "aqi_category": self.pm.category(aqi),
                "los": self.tf.los(avg_vc),
                "polygon": z.get("polygon", []),
            })
        return out

    def _recalc_zones(self, state):
        w = state.get("weather", {})
        w_factor = self.pm.weather_factor(
            w.get("wind_speed", 8), w.get("humidity", 60), w.get("temperature", 28)
        )
        roads = state["roads"]
        for z in state["zones"]:
            zid = z["id"]
            conn = [r for r in roads if r["from_zone"] == zid or r["to_zone"] == zid]
            n = max(len(conn), 1)
            z["traffic_volume"] = int(sum(r["volume"] for r in conn) / n)
            z["avg_speed_kmh"]  = round(sum(r["speed_kmh"] for r in conn) / n, 1)
            avg_vc = sum(r["congestion_ratio"] for r in conn) / n
            z["congestion_ratio"] = round(avg_vc, 3)
            z["los"] = self.tf.los(avg_vc)
            emit = sum(self.pm.emissions(r["volume"], r["speed_kmh"], r["road_type"], r["length_km"]) for r in conn)
            t_aqi = self.pm.to_aqi(emit, ZONES[zid]["area_km2"])
            base  = ZONES[zid]["base_aqi"]
            aqi   = min(500, max(20, (base * 0.35 + t_aqi * 0.65) * w_factor))
            z["aqi"] = round(aqi, 1)
            z["aqi_category"] = self.pm.category(aqi)

    # ── Scenario handlers ─────────────────────────

    def _apply_scenario(self, state, scenario):
        t = scenario.get("type")
        if t == "road_closure":
            self._sc_road_closure(state, scenario)
        elif t == "traffic_surge":
            self._sc_traffic_surge(state, scenario)
        elif t == "rainfall":
            self._sc_rainfall(state, scenario)
        elif t == "event_crowd":
            self._sc_event_crowd(state, scenario)
        elif t == "signal_optimization":
            self._sc_signal_opt(state, scenario)
        elif t == "construction":
            self._sc_construction(state, scenario)
        elif t == "emission_reduction":
            self._sc_emission_reduction(state, scenario)
        self._recalc_zones(state)
        state["metrics"] = self._metrics(state["zones"], state["roads"])
        return state

    def _sc_road_closure(self, state, sc):
        rid = sc.get("road_id")
        pct = sc.get("closure_percentage", 100) / 100
        displaced = 0
        for r in state["roads"]:
            if r["id"] == rid:
                displaced = int(r["volume"] * pct)
                r["volume"]    = int(r["volume"] * (1 - pct))
                r["capacity"]  = max(100, int(r["capacity"] * (1 - pct)))
                r["is_closed"] = pct >= 1.0
                vc = self.tf.vc(r["volume"], r["capacity"])
                r["congestion_ratio"] = round(min(vc, 2.0), 3)
                r["speed_kmh"] = round(self.tf.effective_speed(r["free_flow_speed"], vc), 1)
                r["los"] = self.tf.los(vc)
                break
        if displaced > 0:
            self._redistribute(state["roads"], rid, displaced)

    def _sc_traffic_surge(self, state, sc):
        surge = sc.get("surge_percentage", 30) / 100
        zones = sc.get("affected_zones", [z["id"] for z in state["zones"]])
        for r in state["roads"]:
            if r["from_zone"] in zones or r["to_zone"] in zones:
                r["volume"] = int(r["volume"] * (1 + surge))
                vc = self.tf.vc(r["volume"], r["capacity"])
                r["congestion_ratio"] = round(min(vc, 2.0), 3)
                r["speed_kmh"] = round(self.tf.effective_speed(r["free_flow_speed"], vc), 1)
                r["los"] = self.tf.los(vc)

    def _sc_rainfall(self, state, sc):
        mm = sc.get("rainfall_mm", 20)
        if mm < 10:
            cap_red, spd_red = 0.10, 0.15
        elif mm < 30:
            cap_red, spd_red = 0.25, 0.30
        elif mm < 60:
            cap_red, spd_red = 0.40, 0.45
        else:
            cap_red, spd_red = 0.60, 0.60

        flood_prob = min(0.80, mm / 80)
        for r in state["roads"]:
            r["capacity"] = max(100, int(r["capacity"] * (1 - cap_red)))
            r["speed_kmh"] = max(5, round(r["speed_kmh"] * (1 - spd_red), 1))
            if r["road_type"] == "local" and random.random() < flood_prob:
                r["capacity"] = int(r["capacity"] * 0.30)
                r["is_flooded"] = True
            vc = self.tf.vc(r["volume"], r["capacity"])
            r["congestion_ratio"] = round(min(vc, 2.0), 3)
            r["los"] = self.tf.los(vc)
        w = state["weather"]
        w["rainfall_mm"] = mm
        w["humidity"] = min(100, w.get("humidity", 60) + mm * 0.5)
        w["wind_speed"] = max(2, w.get("wind_speed", 8) * 0.7)

    def _sc_event_crowd(self, state, sc):
        venue = sc.get("venue_zone", "cp")
        crowd = sc.get("crowd_size", 50_000)
        vehicles = int(crowd * 0.65 / 2.3)      # 35% public transport, avg 2.3 pax/vehicle
        venue_roads = [r for r in state["roads"] if r["from_zone"] == venue or r["to_zone"] == venue]
        adj = self._adjacent_zones(venue)
        adj_roads  = [r for r in state["roads"]
                      if (r["from_zone"] in adj or r["to_zone"] in adj)
                      and r["from_zone"] != venue and r["to_zone"] != venue]
        per_road = vehicles // max(len(venue_roads), 1)
        for r in venue_roads:
            r["volume"] += per_road
            vc = self.tf.vc(r["volume"], r["capacity"])
            r["congestion_ratio"] = round(min(vc, 2.0), 3)
            r["speed_kmh"] = round(self.tf.effective_speed(r["free_flow_speed"], vc), 1)
            r["los"] = self.tf.los(vc)
        spillover = int(vehicles * 0.20 / max(len(adj_roads), 1))
        for r in adj_roads:
            r["volume"] += spillover
            vc = self.tf.vc(r["volume"], r["capacity"])
            r["congestion_ratio"] = round(min(vc, 2.0), 3)
            r["speed_kmh"] = round(self.tf.effective_speed(r["free_flow_speed"], vc), 1)
            r["los"] = self.tf.los(vc)

    def _sc_signal_opt(self, state, sc):
        opt = sc.get("optimization_type", "adaptive")
        imp = {"adaptive": 0.18, "green_wave": 0.25, "ai_optimized": 0.32}.get(opt, 0.20)
        corridors = sc.get("corridors", [])
        for r in state["roads"]:
            if corridors and r["id"] not in corridors:
                continue
            r["capacity"] = int(r["capacity"] * (1 + imp * 0.6))
            r["speed_kmh"] = min(round(r["speed_kmh"] * (1 + imp * 0.5), 1), 95)
            vc = self.tf.vc(r["volume"], r["capacity"])
            r["congestion_ratio"] = round(max(0.05, vc), 3)
            r["los"] = self.tf.los(vc)

    def _sc_construction(self, state, sc):
        rid = sc.get("road_id")
        lanes = sc.get("lanes_closed", 1)
        for r in state["roads"]:
            if r["id"] == rid:
                lane_factor = lanes / max(r["num_lanes"], 1)
                r["capacity"] = max(200, int(r["capacity"] * (1 - lane_factor)))
                r["speed_kmh"] = min(r["speed_kmh"], 30)
                r["is_construction"] = True
                vc = self.tf.vc(r["volume"], r["capacity"])
                r["congestion_ratio"] = round(min(vc, 2.0), 3)
                r["los"] = self.tf.los(vc)
                break
        # Spill to nearby roads
        self._redistribute(state["roads"], rid, int(ROADS.get(rid, {}).get("base_volume", 0) * lane_factor * 0.5) if rid in ROADS else 0)

    def _sc_emission_reduction(self, state, sc):
        rtype = sc.get("reduction_type", "odd_even")
        demand_cut = {"odd_even": 0.15, "carpooling": 0.20, "ev_fleet": 0.05}.get(rtype, 0.15)
        for r in state["roads"]:
            r["volume"] = int(r["volume"] * (1 - demand_cut))
            vc = self.tf.vc(r["volume"], r["capacity"])
            r["congestion_ratio"] = round(max(0.05, vc), 3)
            r["speed_kmh"] = round(self.tf.effective_speed(r["free_flow_speed"], vc), 1)
            r["los"] = self.tf.los(vc)

    # ── Traffic redistribution ────────────────────

    def _redistribute(self, roads, closed_id, displaced: int):
        """Distribute displaced traffic to alternate roads proportionally."""
        if displaced <= 0:
            return
        closed = ROADS.get(closed_id, {})
        fz, tz = closed.get("from_zone", ""), closed.get("to_zone", "")
        alts = [r for r in roads if r["id"] != closed_id
                and (r["from_zone"] in (fz, tz) or r["to_zone"] in (fz, tz))]
        if not alts:
            return
        total_slack = sum(max(0, r["capacity"] - r["volume"]) for r in alts)
        for r in alts:
            slack = max(0, r["capacity"] - r["volume"])
            share = (slack / total_slack * displaced) if total_slack > 0 else displaced // len(alts)
            r["volume"] += int(share)
            vc = self.tf.vc(r["volume"], r["capacity"])
            r["congestion_ratio"] = round(min(vc, 2.0), 3)
            r["speed_kmh"] = round(self.tf.effective_speed(r["free_flow_speed"], vc), 1)
            r["los"] = self.tf.los(vc)

    # ── Metrics ───────────────────────────────────

    def _metrics(self, zones, roads) -> dict:
        if not zones or not roads:
            return {}
        avg_vc  = sum(z["congestion_ratio"] for z in zones) / len(zones)
        avg_aqi = sum(z["aqi"] for z in zones) / len(zones)
        avg_spd = sum(z["avg_speed_kmh"] for z in zones) / len(zones)
        total_v = sum(r["volume"] for r in roads)
        los_cnt = {k: 0 for k in "ABCDEF"}
        for r in roads:
            los_cnt[r.get("los", "C")] = los_cnt.get(r.get("los", "C"), 0) + 1
        cong_score  = max(0, 100 - avg_vc * 85)
        aqi_score   = max(0, 100 - (avg_aqi - 50) * 0.24)
        speed_score = min(100, avg_spd * 1.8)
        health = cong_score * 0.4 + aqi_score * 0.4 + speed_score * 0.2
        return {
            "avg_congestion": round(avg_vc, 3),
            "avg_aqi": round(avg_aqi, 1),
            "avg_speed_kmh": round(avg_spd, 1),
            "total_vehicles": int(total_v),
            "health_score": round(health, 1),
            "los_distribution": los_cnt,
            "critical_roads": len([r for r in roads if r["congestion_ratio"] > 0.9]),
            "closed_roads": len([r for r in roads if r.get("is_closed")]),
            "flooded_roads": len([r for r in roads if r.get("is_flooded")]),
        }

    def _impact(self, before, after) -> dict:
        bm, am = before["metrics"], after["metrics"]
        cong_chg = round((am["avg_congestion"] - bm["avg_congestion"]) /
                         max(bm["avg_congestion"], 0.01) * 100, 1)
        aqi_chg  = round(am["avg_aqi"] - bm["avg_aqi"], 1)
        spd_chg  = round(am["avg_speed_kmh"] - bm["avg_speed_kmh"], 1)
        health_chg = round(am["health_score"] - bm["health_score"], 1)
        if abs(cong_chg) > 30 or abs(aqi_chg) > 50:
            severity = "Critical"
        elif abs(cong_chg) > 15 or abs(aqi_chg) > 25:
            severity = "High"
        elif abs(cong_chg) > 5 or abs(aqi_chg) > 10:
            severity = "Moderate"
        else:
            severity = "Low"
        affected = []
        bz_map = {z["id"]: z for z in before["zones"]}
        for az in after["zones"]:
            bz = bz_map.get(az["id"], {})
            dc = az["congestion_ratio"] - bz.get("congestion_ratio", 0)
            da = az["aqi"] - bz.get("aqi", 0)
            if abs(dc) > 0.10 or abs(da) > 10:
                affected.append({
                    "id": az["id"], "name": az["name"],
                    "congestion_change": round(dc, 3),
                    "aqi_change": round(da, 1),
                })
        affected.sort(key=lambda x: abs(x["congestion_change"]), reverse=True)
        return {
            "congestion_change_pct": cong_chg,
            "aqi_change": aqi_chg,
            "speed_change_kmh": spd_chg,
            "health_score_change": health_chg,
            "severity": severity,
            "total_vehicles_change": am["total_vehicles"] - bm["total_vehicles"],
            "affected_zones": affected[:5],
        }

    def _adjacent_zones(self, zone_id: str) -> List[str]:
        adj = set()
        for r in ROADS.values():
            if r["from_zone"] == zone_id:
                adj.add(r["to_zone"])
            elif r["to_zone"] == zone_id:
                adj.add(r["from_zone"])
        return list(adj)


def _default_weather():
    from datetime import datetime
    month = datetime.now().month
    if month in [12, 1, 2]:
        return {"temperature": 14, "humidity": 68, "wind_speed": 8, "rainfall_mm": 0, "description": "Winter Haze"}
    elif month in [3, 4, 5]:
        return {"temperature": 38, "humidity": 32, "wind_speed": 12, "rainfall_mm": 0, "description": "Hot & Dry"}
    elif month in [6, 7, 8, 9]:
        return {"temperature": 30, "humidity": 82, "wind_speed": 10, "rainfall_mm": 15, "description": "Monsoon"}
    return {"temperature": 26, "humidity": 55, "wind_speed": 9, "rainfall_mm": 0, "description": "Post-Monsoon"}
