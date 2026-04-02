"""
AI Recommendation Engine
========================
Hybrid rule-based + impact-scoring system.
Generates prioritised, actionable recommendations after each simulation.
"""

from typing import List
import networkx as nx


class RecommendationEngine:

    def generate(self, scenario: dict, before: dict, after: dict, graph: nx.DiGraph) -> List[dict]:
        recs = []
        t = scenario.get("type", "")

        # Scenario-specific recommendations
        dispatch = {
            "road_closure":       self._road_closure,
            "traffic_surge":      self._traffic_surge,
            "rainfall":           self._rainfall,
            "event_crowd":        self._event_crowd,
            "signal_optimization":self._signal_opt,
            "construction":       self._construction,
            "emission_reduction": self._emission_red,
        }
        if t in dispatch:
            recs.extend(dispatch[t](scenario, before, after))

        # Universal bottleneck recommendations
        recs.extend(self._bottleneck_recs(after))

        # Pollution emergency
        recs.extend(self._pollution_recs(after))

        # Deduplicate by id, sort by priority_score descending, cap at 8
        seen = set()
        unique = []
        for r in sorted(recs, key=lambda x: x["priority_score"], reverse=True):
            if r["id"] not in seen:
                seen.add(r["id"])
                p = r["priority_score"]
                r["priority"] = ("Critical" if p >= 85 else
                                 "High"     if p >= 70 else
                                 "Medium"   if p >= 50 else "Low")
                unique.append(r)
        return unique[:8]

    # ─── Scenario handlers ────────────────────────

    def _road_closure(self, sc, before, after):
        return [
            {
                "id": "rc1", "icon": "🔄",
                "type": "infrastructure",
                "action": "Activate contraflow on parallel corridor",
                "detail": ("Implement contraflow operations on the nearest parallel arterial road "
                           "to double inbound capacity during peak hours. Deploy traffic marshals at merge points."),
                "estimated_impact": "Reduces alternate-route congestion by 25–30%",
                "implementation_time": "30 min",
                "priority_score": 90,
                "metrics": {"congestion_delta": -28, "speed_delta": +12},
            },
            {
                "id": "rc2", "icon": "📢",
                "type": "signage",
                "action": "Activate VMS diversion boards",
                "detail": ("Switch on Variable Message Signs (VMS) 3 km before closure point. "
                           "Guide drivers to Ring Road, Outer Ring Road, and metro stations."),
                "estimated_impact": "Diverts 35% of traffic before the bottleneck",
                "implementation_time": "Immediate (remote activation)",
                "priority_score": 88,
                "metrics": {"congestion_delta": -22, "speed_delta": +8},
            },
            {
                "id": "rc3", "icon": "🚦",
                "type": "signal",
                "action": "Extend green phase on diversion corridors by 25%",
                "detail": ("Increase green time at key junctions on the diversion route to improve "
                           "throughput and reduce queuing."),
                "estimated_impact": "Junction capacity +20%; delays –8 min average",
                "implementation_time": "15 min (SCATS/UTC command)",
                "priority_score": 76,
                "metrics": {"congestion_delta": -12, "speed_delta": +6},
            },
            {
                "id": "rc4", "icon": "🚌",
                "type": "public_transport",
                "action": "Deploy additional DTC buses on parallel corridors",
                "detail": ("Press 20 extra DTC buses into service on the parallel route to absorb "
                           "stranded commuters and reduce private vehicle demand."),
                "estimated_impact": "12% modal shift from cars to buses",
                "implementation_time": "45 min",
                "priority_score": 65,
                "metrics": {"congestion_delta": -10, "speed_delta": +4},
            },
        ]

    def _traffic_surge(self, sc, before, after):
        surge = sc.get("surge_percentage", 30)
        return [
            {
                "id": "ts1", "icon": "🚦",
                "type": "signal",
                "action": "Activate coordinated green-wave signal plan",
                "detail": ("Switch all arterial corridors to green-wave coordinated timing "
                           "at 45–55 km/h progression speed. Eliminates stop-and-go cycles."),
                "estimated_impact": "Network throughput +18%; travel time –14%",
                "implementation_time": "Immediate",
                "priority_score": 93,
                "metrics": {"congestion_delta": -18, "speed_delta": +9},
            },
            {
                "id": "ts2", "icon": "⏰",
                "type": "demand_management",
                "action": "Issue staggered-hours advisory to corporate parks",
                "detail": (f"Send automated advisories to major office complexes to stagger shift times "
                           f"by ±45 min, distributing the {surge}% surge over a longer window."),
                "estimated_impact": "Peak volume –20%; spread over 90 extra minutes",
                "implementation_time": "Next business day (advance notice required)",
                "priority_score": 82,
                "metrics": {"congestion_delta": -20, "speed_delta": +7},
            },
            {
                "id": "ts3", "icon": "🛣️",
                "type": "infrastructure",
                "action": "Open emergency shoulder lanes on NH-48 and NH-24",
                "detail": ("Activate hard-shoulder running on expressways to add +25% effective "
                           "capacity on the most congested corridors."),
                "estimated_impact": "Corridor capacity +20–25%",
                "implementation_time": "20 min (highway patrol escort required)",
                "priority_score": 79,
                "metrics": {"congestion_delta": -22, "speed_delta": +15},
            },
            {
                "id": "ts4", "icon": "📱",
                "type": "technology",
                "action": "Push real-time route guidance via DIMTS app",
                "detail": ("Send push notifications to registered users with optimal routes. "
                           "Voluntary compliance spreads demand across underused roads."),
                "estimated_impact": "8–12% voluntary route diversion",
                "implementation_time": "5 min",
                "priority_score": 68,
                "metrics": {"congestion_delta": -8, "speed_delta": +3},
            },
        ]

    def _rainfall(self, sc, before, after):
        mm = sc.get("rainfall_mm", 20)
        severity = "extreme" if mm > 60 else "heavy" if mm > 30 else "moderate"
        return [
            {
                "id": "rr1", "icon": "⚠️",
                "type": "advisory",
                "action": f"Issue {severity.upper()} rainfall traffic advisory",
                "detail": (f"Broadcast advisory via Delhi Traffic Police SMS, DIMTS app, and FM radio: "
                           f"{mm}mm rainfall expected. Add 30–40% to journey time; avoid flood-prone underpasses."),
                "estimated_impact": "Accident risk –35%; voluntary demand shift –12%",
                "implementation_time": "Immediate",
                "priority_score": 95,
                "metrics": {"congestion_delta": -10, "safety_improvement": 35},
            },
            {
                "id": "rr2", "icon": "🌊",
                "type": "infrastructure",
                "action": "Pre-position drainage pumps at critical underpasses",
                "detail": ("Deploy portable pumps at Minto Road, Zakhira, Pul Prahladpur, "
                           "and ITO underpasses. Prevents waterlogging that typically closes 6 routes."),
                "estimated_impact": "Keeps 6 key underpasses operational",
                "implementation_time": "45 min",
                "priority_score": 88,
                "metrics": {"roads_saved": 6, "congestion_delta": -15},
            },
            {
                "id": "rr3", "icon": "🚦",
                "type": "signal",
                "action": "Activate wet-weather extended signal timing plan",
                "detail": ("Switch signals to 15% extended green time to accommodate longer "
                           "following distances and reduced speeds. Stored as Plan B in UTC system."),
                "estimated_impact": "Rear-end collision risk –22%",
                "implementation_time": "5 min",
                "priority_score": 80,
                "metrics": {"congestion_delta": -8, "safety_improvement": 22},
            },
            {
                "id": "rr4", "icon": "🚇",
                "type": "public_transport",
                "action": "Increase metro frequency to 2-min headways",
                "detail": ("Coordinate with DMRC to reduce headways from 4 min to 2 min on "
                           "Yellow, Blue, and Pink lines to absorb road-to-rail shift."),
                "estimated_impact": "18% shift from roads to metro",
                "implementation_time": "30 min (DMRC coordination)",
                "priority_score": 74,
                "metrics": {"congestion_delta": -16, "modal_shift_pct": 18},
            },
        ]

    def _event_crowd(self, sc, before, after):
        venue = sc.get("venue_zone", "cp")
        crowd = sc.get("crowd_size", 50_000)
        return [
            {
                "id": "ec1", "icon": "🎯",
                "type": "event_management",
                "action": f"Establish event traffic cordon (2 km radius)",
                "detail": (f"Create a managed 2 km cordon around the venue with 4 dedicated ingress/egress "
                           f"points. Assign traffic police at each. Route {crowd:,} attendees via pre-designated lanes."),
                "estimated_impact": "Contains event traffic to 4 designated corridors",
                "implementation_time": "2 hrs before event",
                "priority_score": 93,
                "metrics": {"congestion_delta": -30, "speed_delta": +10},
            },
            {
                "id": "ec2", "icon": "🚌",
                "type": "public_transport",
                "action": "Launch park-and-ride shuttle network",
                "detail": ("Run dedicated shuttles from Pragati Maidan, NSIC grounds, and JLN Stadium. "
                           "Eliminates ~40% of venue-bound private vehicles."),
                "estimated_impact": "Reduces venue-area vehicles by 40%",
                "implementation_time": "3 hrs before event",
                "priority_score": 88,
                "metrics": {"vehicles_removed": int(crowd * 0.4 / 2.5), "congestion_delta": -25},
            },
            {
                "id": "ec3", "icon": "📱",
                "type": "demand_management",
                "action": "Issue time-slotted digital entry passes",
                "detail": ("Distribute time-slotted QR entry passes via the event app — 30 min windows — "
                           "to smooth crowd arrival curves and prevent simultaneous surge."),
                "estimated_impact": "Peak arrival surge –55%",
                "implementation_time": "1 day before (advance planning)",
                "priority_score": 84,
                "metrics": {"peak_reduction_pct": 55},
            },
            {
                "id": "ec4", "icon": "🚇",
                "type": "public_transport",
                "action": "Special metro services to nearest stations",
                "detail": ("Coordinate extended metro hours and special event trains on nearest lines. "
                           "Promote metro as primary mode in all event communications."),
                "estimated_impact": "Additional 25% modal shift to metro",
                "implementation_time": "1 day before",
                "priority_score": 79,
                "metrics": {"modal_shift_pct": 25},
            },
        ]

    def _signal_opt(self, sc, before, after):
        opt = sc.get("optimization_type", "adaptive")
        return [
            {
                "id": "so1", "icon": "🤖",
                "type": "technology",
                "action": "Enable SCOOT adaptive signal control system",
                "detail": ("Activate the SCOOT (Split, Cycle, and Offset Optimization Technique) controller "
                           "at 25 key intersections. Real-time traffic loop detector data feeds into AI optimizer."),
                "estimated_impact": "Average intersection delay –23%; emissions –12%",
                "implementation_time": "Immediate (software activation)",
                "priority_score": 92,
                "metrics": {"delay_reduction_pct": 23, "emission_reduction_pct": 12},
            },
            {
                "id": "so2", "icon": "🟢",
                "type": "signal",
                "action": "Green wave on NH-48, Ring Road, and Mathura Road",
                "detail": ("Synchronise signals for 50 km/h progression on 3 key corridors. "
                           "Reduces stops per km from 4 to <1 during coordinated phases."),
                "estimated_impact": "Corridor throughput +25%; stops per km –75%",
                "implementation_time": "10 min",
                "priority_score": 86,
                "metrics": {"congestion_delta": -22, "speed_delta": +14},
            },
            {
                "id": "so3", "icon": "📊",
                "type": "technology",
                "action": "Deploy AI demand prediction for proactive timing",
                "detail": ("Use ML forecasting (trained on historical flow data) to pre-adjust signal plans "
                           "15 minutes ahead of predicted surges — before congestion builds."),
                "estimated_impact": "Queue formation reduced by 40%",
                "implementation_time": "Pilot: 1 week setup",
                "priority_score": 78,
                "metrics": {"queue_reduction_pct": 40},
            },
        ]

    def _construction(self, sc, before, after):
        return [
            {
                "id": "con1", "icon": "🚧",
                "type": "traffic_management",
                "action": "Implement construction zone traffic management plan",
                "detail": ("Deploy flag persons + temporary traffic lights at construction zone boundaries. "
                           "Activate tidal lane reversal during peak hours to maximise remaining capacity."),
                "estimated_impact": "Effective capacity maintained at 70% of normal",
                "implementation_time": "1 hour",
                "priority_score": 88,
                "metrics": {"capacity_preserved_pct": 70},
            },
            {
                "id": "con2", "icon": "📋",
                "type": "policy",
                "action": "Restrict construction heavy vehicles to off-peak hours",
                "detail": ("Permit construction material trucks only between 11pm–5am. "
                           "Eliminates heavy vehicle conflict during peak commute hours."),
                "estimated_impact": "Removes construction HV conflict during peak hours",
                "implementation_time": "Next morning",
                "priority_score": 75,
                "metrics": {"delay_reduction_pct": 15},
            },
        ]

    def _emission_red(self, sc, before, after):
        rtype = sc.get("reduction_type", "odd_even")
        return [
            {
                "id": "er1", "icon": "🌿",
                "type": "policy",
                "action": "Communicate and enforce the restriction via visible signage",
                "detail": ("Deploy 500+ cops for enforcement. Activate e-challan cameras at "
                           "50 strategic points. Issue communication via WhatsApp, radio, and newspaper."),
                "estimated_impact": "90%+ compliance rate",
                "implementation_time": "24 hours notice required",
                "priority_score": 85,
                "metrics": {"compliance_pct": 90},
            },
            {
                "id": "er2", "icon": "🚇",
                "type": "public_transport",
                "action": "Augment public transport capacity by 30%",
                "detail": ("Add 500 DTC bus trips and reduce metro headways to 2.5 min to absorb "
                           "stranded private vehicle users."),
                "estimated_impact": "Demand absorbed; no overcrowding at stops",
                "implementation_time": "Same day",
                "priority_score": 80,
                "metrics": {"extra_capacity_pct": 30},
            },
        ]

    # ─── Universal recommendations ────────────────

    def _bottleneck_recs(self, after: dict) -> List[dict]:
        recs = []
        critical = sorted(
            [r for r in after.get("roads", []) if r["congestion_ratio"] > 0.88],
            key=lambda x: x["congestion_ratio"], reverse=True
        )[:3]
        for i, r in enumerate(critical):
            recs.append({
                "id": f"bn{i+1}", "icon": "🚨",
                "type": "immediate",
                "action": f"Emergency management at {r['name']}",
                "detail": (f"V/C = {r['congestion_ratio']:.2f} → LOS {r['los']} (breakdown flow). "
                           f"Deploy 2 traffic police constables + open emergency shoulder lane immediately."),
                "estimated_impact": f"Delay reduction 15–25 min on {r['name']}",
                "implementation_time": "15 min",
                "priority_score": min(95, round(65 + r["congestion_ratio"] * 25)),
                "metrics": {"delay_reduction_min": 20},
            })
        return recs

    def _pollution_recs(self, after: dict) -> List[dict]:
        severe_zones = [z for z in after.get("zones", []) if z["aqi"] > 300]
        if not severe_zones:
            return []
        return [{
            "id": "aqi1", "icon": "💨",
            "type": "environment",
            "action": f"Issue health advisory for {len(severe_zones)} high-AQI zone(s)",
            "detail": (f"AQI > 300 (Very Poor) detected in: "
                       f"{', '.join(z['name'] for z in severe_zones[:3])}. "
                       "Restrict outdoor activities; halt construction dust sources; deploy water sprinklers."),
            "estimated_impact": "AQI improvement –30–50 points within 4 hours",
            "implementation_time": "Immediate",
            "priority_score": 87,
            "metrics": {"aqi_reduction": 40},
        }]
