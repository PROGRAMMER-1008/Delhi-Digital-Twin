"""
Delhi City Network Data
Contains all zone definitions, road network, and graph construction.
Data sourced from real Delhi geography and road capacities.
"""

import networkx as nx


def _poly(lat, lng, w=0.022, h=0.018):
    """Create approximate rectangular polygon around a lat/lng point."""
    return [
        [lat + h, lng - w],
        [lat + h, lng + w],
        [lat - h, lng + w],
        [lat - h, lng - w],
        [lat + h, lng - w],
    ]


# ─────────────────────────────────────────────────
#  ZONES  (12 major Delhi zones)
# ─────────────────────────────────────────────────
ZONES = {
    "cp": {
        "id": "cp", "name": "Connaught Place",
        "lat": 28.6304, "lng": 77.2177,
        "zone_type": "commercial", "area_km2": 4.5, "population": 500_000,
        "base_traffic": 880, "base_aqi": 168,
        "polygon": _poly(28.6304, 77.2177, 0.018, 0.015),
    },
    "old_delhi": {
        "id": "old_delhi", "name": "Old Delhi",
        "lat": 28.6562, "lng": 77.2310,
        "zone_type": "mixed", "area_km2": 7.2, "population": 800_000,
        "base_traffic": 760, "base_aqi": 195,
        "polygon": _poly(28.6562, 77.2310, 0.025, 0.020),
    },
    "dwarka": {
        "id": "dwarka", "name": "Dwarka",
        "lat": 28.5921, "lng": 77.0460,
        "zone_type": "residential", "area_km2": 55.0, "population": 1_200_000,
        "base_traffic": 520, "base_aqi": 148,
        "polygon": _poly(28.5921, 77.0460, 0.042, 0.035),
    },
    "rohini": {
        "id": "rohini", "name": "Rohini",
        "lat": 28.7495, "lng": 77.0696,
        "zone_type": "residential", "area_km2": 35.0, "population": 900_000,
        "base_traffic": 485, "base_aqi": 155,
        "polygon": _poly(28.7495, 77.0696, 0.038, 0.030),
    },
    "noida_border": {
        "id": "noida_border", "name": "Noida Border",
        "lat": 28.5677, "lng": 77.3419,
        "zone_type": "commercial", "area_km2": 12.0, "population": 300_000,
        "base_traffic": 920, "base_aqi": 172,
        "polygon": _poly(28.5677, 77.3419, 0.025, 0.020),
    },
    "gurugram_border": {
        "id": "gurugram_border", "name": "Gurugram Border",
        "lat": 28.5013, "lng": 77.0894,
        "zone_type": "commercial", "area_km2": 8.0, "population": 200_000,
        "base_traffic": 1050, "base_aqi": 162,
        "polygon": _poly(28.5013, 77.0894, 0.025, 0.020),
    },
    "south_delhi": {
        "id": "south_delhi", "name": "South Delhi",
        "lat": 28.5494, "lng": 77.2001,
        "zone_type": "residential", "area_km2": 40.0, "population": 700_000,
        "base_traffic": 620, "base_aqi": 152,
        "polygon": _poly(28.5494, 77.2001, 0.040, 0.032),
    },
    "east_delhi": {
        "id": "east_delhi", "name": "East Delhi",
        "lat": 28.6280, "lng": 77.3150,
        "zone_type": "mixed", "area_km2": 45.0, "population": 1_100_000,
        "base_traffic": 695, "base_aqi": 178,
        "polygon": _poly(28.6280, 77.3150, 0.042, 0.035),
    },
    "north_delhi": {
        "id": "north_delhi", "name": "North Delhi",
        "lat": 28.7041, "lng": 77.1025,
        "zone_type": "mixed", "area_km2": 30.0, "population": 600_000,
        "base_traffic": 545, "base_aqi": 160,
        "polygon": _poly(28.7041, 77.1025, 0.035, 0.028),
    },
    "janakpuri": {
        "id": "janakpuri", "name": "Janakpuri",
        "lat": 28.6219, "lng": 77.0822,
        "zone_type": "residential", "area_km2": 20.0, "population": 450_000,
        "base_traffic": 430, "base_aqi": 142,
        "polygon": _poly(28.6219, 77.0822, 0.025, 0.020),
    },
    "lajpat_nagar": {
        "id": "lajpat_nagar", "name": "Lajpat Nagar",
        "lat": 28.5693, "lng": 77.2439,
        "zone_type": "commercial", "area_km2": 8.5, "population": 250_000,
        "base_traffic": 710, "base_aqi": 163,
        "polygon": _poly(28.5693, 77.2439, 0.018, 0.015),
    },
    "nehru_place": {
        "id": "nehru_place", "name": "Nehru Place",
        "lat": 28.5491, "lng": 77.2521,
        "zone_type": "commercial", "area_km2": 5.0, "population": 100_000,
        "base_traffic": 780, "base_aqi": 158,
        "polygon": _poly(28.5491, 77.2521, 0.015, 0.012),
    },
}


# ─────────────────────────────────────────────────
#  ROADS  (20 major road segments)
#  capacity = PCU/hour (Passenger Car Units per direction)
# ─────────────────────────────────────────────────
ROADS = {
    # ── Ring Road ────────────────────────────────
    "ring_cp_old": {
        "id": "ring_cp_old", "name": "Ring Road (CP–Old Delhi)",
        "from_zone": "cp", "to_zone": "old_delhi",
        "from_lat": 28.6304, "from_lng": 77.2177,
        "to_lat": 28.6562, "to_lng": 77.2310,
        "length_km": 3.8, "capacity": 3200, "free_flow_speed": 55,
        "num_lanes": 6, "road_type": "arterial", "base_volume": 2600,
    },
    "ring_old_north": {
        "id": "ring_old_north", "name": "Ring Road (Old Delhi–North)",
        "from_zone": "old_delhi", "to_zone": "north_delhi",
        "from_lat": 28.6562, "from_lng": 77.2310,
        "to_lat": 28.7041, "to_lng": 77.1025,
        "length_km": 9.2, "capacity": 2800, "free_flow_speed": 60,
        "num_lanes": 4, "road_type": "arterial", "base_volume": 2100,
    },
    "ring_north_rohini": {
        "id": "ring_north_rohini", "name": "Ring Road (North–Rohini)",
        "from_zone": "north_delhi", "to_zone": "rohini",
        "from_lat": 28.7041, "from_lng": 77.1025,
        "to_lat": 28.7495, "to_lng": 77.0696,
        "length_km": 7.1, "capacity": 2400, "free_flow_speed": 60,
        "num_lanes": 4, "road_type": "arterial", "base_volume": 1800,
    },
    # ── NH-48 (Delhi–Gurugram) ───────────────────
    "nh48_cp_south": {
        "id": "nh48_cp_south", "name": "NH-48 (CP–South Delhi)",
        "from_zone": "cp", "to_zone": "south_delhi",
        "from_lat": 28.6304, "from_lng": 77.2177,
        "to_lat": 28.5494, "to_lng": 77.2001,
        "length_km": 9.5, "capacity": 4800, "free_flow_speed": 80,
        "num_lanes": 8, "road_type": "highway", "base_volume": 4200,
    },
    "nh48_south_gurugram": {
        "id": "nh48_south_gurugram", "name": "NH-48 (South Delhi–Gurugram)",
        "from_zone": "south_delhi", "to_zone": "gurugram_border",
        "from_lat": 28.5494, "from_lng": 77.2001,
        "to_lat": 28.5013, "to_lng": 77.0894,
        "length_km": 12.3, "capacity": 5600, "free_flow_speed": 100,
        "num_lanes": 8, "road_type": "highway", "base_volume": 4900,
    },
    # ── NH-24 (Delhi–Noida) ──────────────────────
    "nh24_cp_east": {
        "id": "nh24_cp_east", "name": "NH-24 (CP–East Delhi)",
        "from_zone": "cp", "to_zone": "east_delhi",
        "from_lat": 28.6304, "from_lng": 77.2177,
        "to_lat": 28.6280, "to_lng": 77.3150,
        "length_km": 8.7, "capacity": 3600, "free_flow_speed": 70,
        "num_lanes": 6, "road_type": "highway", "base_volume": 3100,
    },
    "nh24_east_noida": {
        "id": "nh24_east_noida", "name": "NH-24 (East Delhi–Noida)",
        "from_zone": "east_delhi", "to_zone": "noida_border",
        "from_lat": 28.6280, "from_lng": 77.3150,
        "to_lat": 28.5677, "to_lng": 77.3419,
        "length_km": 7.4, "capacity": 4000, "free_flow_speed": 80,
        "num_lanes": 6, "road_type": "highway", "base_volume": 3600,
    },
    # ── Mathura Road ─────────────────────────────
    "mathura_cp_lajpat": {
        "id": "mathura_cp_lajpat", "name": "Mathura Road (CP–Lajpat Nagar)",
        "from_zone": "cp", "to_zone": "lajpat_nagar",
        "from_lat": 28.6304, "from_lng": 77.2177,
        "to_lat": 28.5693, "to_lng": 77.2439,
        "length_km": 7.2, "capacity": 2400, "free_flow_speed": 50,
        "num_lanes": 4, "road_type": "arterial", "base_volume": 1950,
    },
    "mathura_lajpat_nehru": {
        "id": "mathura_lajpat_nehru", "name": "Mathura Road (Lajpat–Nehru Place)",
        "from_zone": "lajpat_nagar", "to_zone": "nehru_place",
        "from_lat": 28.5693, "from_lng": 77.2439,
        "to_lat": 28.5491, "to_lng": 77.2521,
        "length_km": 2.6, "capacity": 2000, "free_flow_speed": 40,
        "num_lanes": 4, "road_type": "arterial", "base_volume": 1700,
    },
    # ── Outer Ring Road ──────────────────────────
    "orr_dwarka_jan": {
        "id": "orr_dwarka_jan", "name": "Outer Ring Road (Dwarka–Janakpuri)",
        "from_zone": "dwarka", "to_zone": "janakpuri",
        "from_lat": 28.5921, "from_lng": 77.0460,
        "to_lat": 28.6219, "to_lng": 77.0822,
        "length_km": 5.8, "capacity": 3200, "free_flow_speed": 65,
        "num_lanes": 6, "road_type": "arterial", "base_volume": 2400,
    },
    "orr_jan_cp": {
        "id": "orr_jan_cp", "name": "Outer Ring Road (Janakpuri–CP)",
        "from_zone": "janakpuri", "to_zone": "cp",
        "from_lat": 28.6219, "from_lng": 77.0822,
        "to_lat": 28.6304, "to_lng": 77.2177,
        "length_km": 11.4, "capacity": 3600, "free_flow_speed": 65,
        "num_lanes": 6, "road_type": "arterial", "base_volume": 2900,
    },
    "orr_south_nehru": {
        "id": "orr_south_nehru", "name": "Outer Ring Road (South–Nehru Place)",
        "from_zone": "south_delhi", "to_zone": "nehru_place",
        "from_lat": 28.5494, "from_lng": 77.2001,
        "to_lat": 28.5491, "to_lng": 77.2521,
        "length_km": 4.7, "capacity": 2800, "free_flow_speed": 55,
        "num_lanes": 4, "road_type": "arterial", "base_volume": 2300,
    },
    # ── GT Road ──────────────────────────────────
    "gt_road_north": {
        "id": "gt_road_north", "name": "GT Road (North Corridor)",
        "from_zone": "old_delhi", "to_zone": "north_delhi",
        "from_lat": 28.6562, "from_lng": 77.2310,
        "to_lat": 28.7041, "to_lng": 77.1025,
        "length_km": 10.5, "capacity": 2000, "free_flow_speed": 45,
        "num_lanes": 4, "road_type": "arterial", "base_volume": 1600,
    },
    # ── Dwarka Expressway ────────────────────────
    "dwarka_exp": {
        "id": "dwarka_exp", "name": "Dwarka Expressway",
        "from_zone": "dwarka", "to_zone": "gurugram_border",
        "from_lat": 28.5921, "from_lng": 77.0460,
        "to_lat": 28.5013, "to_lng": 77.0894,
        "length_km": 16.2, "capacity": 4800, "free_flow_speed": 100,
        "num_lanes": 8, "road_type": "highway", "base_volume": 3200,
    },
    # ── Connectors ───────────────────────────────
    "rohini_jan": {
        "id": "rohini_jan", "name": "Rohini–Janakpuri Connector",
        "from_zone": "rohini", "to_zone": "janakpuri",
        "from_lat": 28.7495, "from_lng": 77.0696,
        "to_lat": 28.6219, "to_lng": 77.0822,
        "length_km": 14.2, "capacity": 2400, "free_flow_speed": 50,
        "num_lanes": 4, "road_type": "arterial", "base_volume": 1850,
    },
    "noida_south": {
        "id": "noida_south", "name": "Noida–South Delhi Link",
        "from_zone": "noida_border", "to_zone": "south_delhi",
        "from_lat": 28.5677, "from_lng": 77.3419,
        "to_lat": 28.5494, "to_lng": 77.2001,
        "length_km": 13.5, "capacity": 2800, "free_flow_speed": 55,
        "num_lanes": 4, "road_type": "arterial", "base_volume": 2200,
    },
    "cp_north_link": {
        "id": "cp_north_link", "name": "CP–North Delhi Link",
        "from_zone": "cp", "to_zone": "north_delhi",
        "from_lat": 28.6304, "from_lng": 77.2177,
        "to_lat": 28.7041, "to_lng": 77.1025,
        "length_km": 10.1, "capacity": 2400, "free_flow_speed": 50,
        "num_lanes": 4, "road_type": "arterial", "base_volume": 1900,
    },
    "east_lajpat": {
        "id": "east_lajpat", "name": "East Delhi–Lajpat Nagar",
        "from_zone": "east_delhi", "to_zone": "lajpat_nagar",
        "from_lat": 28.6280, "from_lng": 77.3150,
        "to_lat": 28.5693, "to_lng": 77.2439,
        "length_km": 9.3, "capacity": 2000, "free_flow_speed": 45,
        "num_lanes": 4, "road_type": "collector", "base_volume": 1600,
    },
    "south_lajpat": {
        "id": "south_lajpat", "name": "South Delhi Local Streets",
        "from_zone": "south_delhi", "to_zone": "lajpat_nagar",
        "from_lat": 28.5494, "from_lng": 77.2001,
        "to_lat": 28.5693, "to_lng": 77.2439,
        "length_km": 4.1, "capacity": 1200, "free_flow_speed": 30,
        "num_lanes": 2, "road_type": "local", "base_volume": 980,
    },
    "north_rohini_local": {
        "id": "north_rohini_local", "name": "North–Rohini Local Road",
        "from_zone": "north_delhi", "to_zone": "rohini",
        "from_lat": 28.7041, "from_lng": 77.1025,
        "to_lat": 28.7495, "to_lng": 77.0696,
        "length_km": 6.2, "capacity": 1600, "free_flow_speed": 35,
        "num_lanes": 2, "road_type": "local", "base_volume": 1200,
    },
}


def get_city_graph() -> nx.DiGraph:
    """Build NetworkX directed graph for shortest-path calculations."""
    G = nx.DiGraph()
    for zid, z in ZONES.items():
        G.add_node(zid, name=z["name"], lat=z["lat"], lng=z["lng"])
    for rid, r in ROADS.items():
        G.add_edge(r["from_zone"], r["to_zone"], id=rid,
                   weight=r["length_km"], capacity=r["capacity"],
                   speed=r["free_flow_speed"])
        G.add_edge(r["to_zone"], r["from_zone"], id=rid + "_rev",
                   weight=r["length_km"], capacity=r["capacity"],
                   speed=r["free_flow_speed"])
    return G


def get_scenario_presets():
    return {
        "rush_hour": {
            "name": "Morning Rush Hour",
            "type": "traffic_surge",
            "surge_percentage": 45,
            "affected_zones": list(ZONES.keys()),
            "description": "Peak morning traffic surge across all Delhi zones",
            "icon": "🕗",
        },
        "nh48_closure": {
            "name": "NH-48 Emergency Closure",
            "type": "road_closure",
            "road_id": "nh48_south_gurugram",
            "closure_percentage": 100,
            "description": "Full closure of NH-48 between South Delhi and Gurugram",
            "icon": "🚧",
        },
        "heavy_rain": {
            "name": "Heavy Monsoon Rain",
            "type": "rainfall",
            "rainfall_mm": 45,
            "description": "Severe waterlogging and reduced road capacity city-wide",
            "icon": "🌧️",
        },
        "republic_day": {
            "name": "Republic Day Parade",
            "type": "event_crowd",
            "venue_zone": "cp",
            "crowd_size": 150000,
            "event_hours": 4,
            "description": "Rajpath parade — 1.5 lakh attendees near Connaught Place",
            "icon": "🎪",
        },
        "adaptive_signals": {
            "name": "AI Signal Optimization",
            "type": "signal_optimization",
            "optimization_type": "ai_optimized",
            "corridors": [],
            "description": "Deploy AI adaptive signal control city-wide",
            "icon": "🤖",
        },
        "construction_ring": {
            "name": "Ring Road Construction",
            "type": "construction",
            "road_id": "ring_cp_old",
            "lanes_closed": 2,
            "description": "Metro construction narrows Ring Road near CP",
            "icon": "🏗️",
        },
        "odd_even": {
            "name": "Odd-Even Restriction",
            "type": "emission_reduction",
            "reduction_type": "odd_even",
            "description": "Emergency odd-even vehicle restriction to cut pollution",
            "icon": "📋",
        },
    }
