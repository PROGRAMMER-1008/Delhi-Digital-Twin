"""
Alternate Route Optimizer — Dijkstra on Weighted Graph
=======================================================
Algorithm: Dijkstra's shortest path (via NetworkX) with dynamic edge weights.

Edge weight formula:
    w(e) = travel_time(v) × penalty(vc) × (1 + emission_factor)

    travel_time(v) = (length_km / effective_speed) × 60   [minutes]
    penalty(vc)    = BPR factor = 1 + 0.15 × (v/c)⁴       [dimensionless]
    emission_factor= 0.05 for highways, 0.02 for arterials  [CO₂ awareness]

Three route objectives:
    "fastest"     — minimise travel time (ignore emissions)
    "balanced"    — minimise time + mild emission penalty
    "eco"         — penalise high-emission roads heavily (green routing)

When a road is closed or in construction, its edge weight = infinity (removed).
"""

import math
import networkx as nx
from typing import Dict, List, Optional, Tuple


# ── Weight computations ────────────────────────────────────────────────

_EMIT_FACTOR = {"expressway": 0.08, "highway": 0.06, "arterial": 0.03, "collector": 0.01}


def _travel_time_min(road: dict, state: dict = None) -> float:
    """
    Congestion-adjusted travel time using BPR model.
    If no state, use free-flow speed.
    """
    length = road.get("length_km", 1.0)
    ff_spd = road.get("free_flow_speed", 60.0)
    cap    = max(road.get("capacity", 2000), 1)

    if state:
        vc     = state.get("vc_ratio", state.get("congestion_ratio", 0.5))
        volume = state.get("volume", cap * 0.5)
    else:
        vc     = road.get("base_volume", cap * 0.5) / cap
        volume = road.get("base_volume", cap * 0.5)

    bpr_factor = 1 + 0.15 * (vc ** 4)
    eff_time   = (length / ff_spd) * 60 * bpr_factor
    return max(eff_time, 0.1)


def _edge_weight(road: dict, state: dict = None, objective: str = "balanced") -> float:
    """
    Compute edge weight for a road segment given routing objective.
    Returns math.inf if road is closed/flooded.
    """
    if state:
        if state.get("is_closed") or state.get("is_flooded"):
            return math.inf
    if road.get("is_closed") or road.get("is_flooded"):
        return math.inf

    tt    = _travel_time_min(road, state)
    rtype = road.get("road_type", "arterial")
    emit  = _EMIT_FACTOR.get(rtype, 0.03)

    if objective == "fastest":
        return tt
    elif objective == "eco":
        return tt * (1 + emit * 4)
    else:  # balanced
        return tt * (1 + emit)


# ── Graph building ─────────────────────────────────────────────────────

def build_weighted_graph(roads_def: dict, road_states: list = None,
                          objective: str = "balanced") -> nx.DiGraph:
    """
    Build a weighted directed graph from road definitions + current states.

    Nodes = zone IDs
    Edges = road segments (bidirectional: one edge each direction)
    """
    G        = nx.DiGraph()
    state_map = {}
    if road_states:
        for rs in road_states:
            rid = rs.get("road_id", rs.get("id", ""))
            state_map[rid] = rs

    for rid, road in roads_def.items():
        fz  = road.get("from_zone")
        tz  = road.get("to_zone")
        if not fz or not tz:
            continue

        state  = state_map.get(rid)
        weight = _edge_weight(road, state, objective)

        if weight < math.inf:
            G.add_edge(fz, tz, weight=weight, road_id=rid,
                       road_name=road.get("name", rid),
                       travel_time=_travel_time_min(road, state),
                       road_type=road.get("road_type", "arterial"),
                       length_km=road.get("length_km", 1.0),
                       vc_ratio=state.get("vc_ratio", 0.5) if state else 0.5)
            # Also add reverse edge (most Delhi roads are two-way)
            if road.get("bidirectional", True):
                G.add_edge(tz, fz, weight=weight, road_id=rid,
                           road_name=road.get("name", rid),
                           travel_time=_travel_time_min(road, state),
                           road_type=road.get("road_type", "arterial"),
                           length_km=road.get("length_km", 1.0),
                           vc_ratio=state.get("vc_ratio", 0.5) if state else 0.5)

    return G


# ── Route extraction ───────────────────────────────────────────────────

def _path_details(G: nx.DiGraph, path: list) -> dict:
    """Extract route details: total time, distance, avg VC, road sequence."""
    if not path or len(path) < 2:
        return {}
    total_time = 0.0
    total_dist = 0.0
    avg_vc     = []
    road_seq   = []

    for i in range(len(path) - 1):
        u, v    = path[i], path[i + 1]
        data    = G.get_edge_data(u, v, default={})
        total_time += data.get("travel_time", 5.0)
        total_dist += data.get("length_km", 1.0)
        avg_vc.append(data.get("vc_ratio", 0.5))
        road_seq.append({
            "road_name": data.get("road_name", f"{u}→{v}"),
            "road_type": data.get("road_type", "arterial"),
            "vc_ratio":  round(data.get("vc_ratio", 0.5), 3),
            "travel_time_min": round(data.get("travel_time", 5), 1),
        })

    return {
        "zones":           path,
        "n_zones":         len(path),
        "total_time_min":  round(total_time, 1),
        "total_dist_km":   round(total_dist, 1),
        "avg_vc":          round(sum(avg_vc) / len(avg_vc), 3) if avg_vc else 0,
        "road_sequence":   road_seq,
    }


# ── RouteOptimizer class ───────────────────────────────────────────────

class RouteOptimizer:
    """
    Dijkstra-based alternate route finder for the Delhi road network.

    Usage:
        optimizer = RouteOptimizer(roads_def)
        routes    = optimizer.find_routes("cp", "noida_border", road_states)
        # returns: { primary, alternatives, closed_roads, analysis }
    """

    def __init__(self, roads_def: dict):
        self.roads_def = roads_def

    def find_routes(self, origin: str, destination: str,
                    road_states: list = None,
                    n_alternatives: int = 3) -> dict:
        """
        Find primary + alternative routes from origin to destination zone.
        Runs Dijkstra 3 times with different objectives.
        """
        results  = {}
        routes   = []

        for obj in ["fastest", "balanced", "eco"]:
            G = build_weighted_graph(self.roads_def, road_states, objective=obj)

            if origin not in G.nodes or destination not in G.nodes:
                results[obj] = {"error": f"Zone '{origin}' or '{destination}' not in graph"}
                continue

            try:
                path   = nx.dijkstra_path(G, origin, destination, weight="weight")
                cost   = nx.dijkstra_path_length(G, origin, destination, weight="weight")
                detail = _path_details(G, path)
                route  = {
                    "objective":   obj,
                    "cost":        round(cost, 2),
                    "label":       {"fastest": "⚡ Fastest Route",
                                    "balanced":"⚖️ Balanced Route",
                                    "eco":     "🌿 Eco Route"}[obj],
                    **detail,
                }
                routes.append(route)
            except nx.NetworkXNoPath:
                routes.append({"objective": obj, "error": "No path found"})

        # Find closed roads on the network
        closed = self._closed_roads(road_states)

        # Cascade analysis: if a road is closed, what zones are cut off?
        cascade = self._cascade_analysis(road_states)

        return {
            "origin":      origin,
            "destination": destination,
            "routes":      routes,
            "closed_roads":closed,
            "cascade":     cascade,
            "algorithm":   "Dijkstra shortest path (NetworkX)",
        }

    def network_summary(self, road_states: list = None) -> dict:
        """
        Full network reachability analysis:
        - How many zone-pairs are still connected?
        - What is the average shortest path (in time)?
        - Which zones are most central (highest betweenness centrality)?
        """
        G = build_weighted_graph(self.roads_def, road_states, objective="balanced")

        # Betweenness centrality (how often a zone lies on optimal paths)
        try:
            bc = nx.betweenness_centrality(G, weight="weight", normalized=True)
        except Exception:
            bc = {n: 0.0 for n in G.nodes}

        # All-pairs shortest path lengths
        try:
            avg_path_lens = []
            for u in G.nodes:
                lengths = nx.single_source_dijkstra_path_length(G, u, weight="weight")
                vals = [v for k, v in lengths.items() if k != u and v < math.inf]
                if vals:
                    avg_path_lens.extend(vals)
            avg_travel_time = round(sum(avg_path_lens) / len(avg_path_lens), 1) if avg_path_lens else 0
        except Exception:
            avg_travel_time = 0

        # Connectivity: strongly connected components
        sccs = list(nx.strongly_connected_components(G))
        main_component_size = max(len(c) for c in sccs) if sccs else 0

        centrality_ranked = sorted(bc.items(), key=lambda x: x[1], reverse=True)

        return {
            "n_nodes":              G.number_of_nodes(),
            "n_edges":              G.number_of_edges(),
            "avg_travel_time_min":  avg_travel_time,
            "connectivity_pct":     round(main_component_size / max(G.number_of_nodes(), 1) * 100, 1),
            "top_central_zones":    [{"zone": z, "centrality": round(c, 3)}
                                     for z, c in centrality_ranked[:5]],
            "strongly_connected_components": len(sccs),
            "algorithm":            "Dijkstra + Betweenness Centrality (NetworkX)",
        }

    def alternate_when_closed(self, closed_road_id: str,
                               road_states: list = None) -> List[dict]:
        """
        Given a road closure, find the best alternate for every zone-pair
        that used to route through that road.
        """
        closed_road = self.roads_def.get(closed_road_id)
        if not closed_road:
            return []

        fz  = closed_road.get("from_zone")
        tz  = closed_road.get("to_zone")
        if not fz or not tz:
            return []

        # Build a modified state with the road marked closed
        mod_states = list(road_states or [])
        mod_states = [
            {**rs, "is_closed": True} if rs.get("road_id", rs.get("id")) == closed_road_id
            else rs
            for rs in mod_states
        ]

        result = self.find_routes(fz, tz, mod_states)
        result["closed_road"] = closed_road_id
        result["original_road"] = {
            "name": closed_road.get("name", closed_road_id),
            "from_zone": fz, "to_zone": tz,
        }
        return [result]

    def _closed_roads(self, road_states: list) -> List[dict]:
        if not road_states:
            return []
        return [
            {"road_id": rs.get("road_id", rs.get("id", "")),
             "road_name": rs.get("road_name", rs.get("name", "")),
             "reason": "Closed" if rs.get("is_closed") else "Flooded" if rs.get("is_flooded") else "Construction"}
            for rs in road_states
            if rs.get("is_closed") or rs.get("is_flooded") or rs.get("is_construction")
        ]

    def _cascade_analysis(self, road_states: list) -> dict:
        """Check if any closed road creates isolated zones (unreachable pairs)."""
        G      = build_weighted_graph(self.roads_def, road_states, "balanced")
        sccs   = list(nx.strongly_connected_components(G))
        if len(sccs) <= 1:
            return {"isolated_zones": [], "network_intact": True}

        main  = max(sccs, key=len)
        isol  = [list(c) for c in sccs if c != main]
        return {"isolated_zones": isol, "network_intact": len(isol) == 0}
