"""
Road Congestion Clustering — K-Means (pure NumPy)
==================================================
Algorithm: K-Means++ initialisation + Lloyd's algorithm

Purpose:
  Groups Delhi's 20 road segments into K congestion clusters based on:
    - current VC ratio (volume / capacity)
    - road type weight (highway vs arterial vs collector)
    - time-of-day sensitivity (peak vs off-peak loading)
    - emissions index

Clusters are used by the RecommendationEngine to:
  1. Identify which roads belong to the same "congestion hotspot"
  2. Prioritise interventions affecting the largest cluster
  3. Detect when a single scenario will cascade across a cluster

Cluster labels:
  0 → Free Flow     (VC < 0.6)
  1 → Moderate      (VC 0.6–0.85)
  2 → Congested     (VC 0.85–1.0)
  3 → Breakdown     (VC > 1.0)
  (actual cluster count K is tuned automatically via elbow method)
"""

import numpy as np
from typing import List, Dict, Tuple, Optional


# ── Feature extraction ─────────────────────────────────────────────────

_ROAD_TYPE_WEIGHT = {"expressway": 1.0, "highway": 0.85, "arterial": 0.65, "collector": 0.45}


def _road_features(road_state: dict, road_def: dict = None) -> np.ndarray:
    """
    Build a feature vector for one road:
      f0 = vc_ratio            (congestion level)
      f1 = norm_volume         (actual traffic load normalised by max capacity seen)
      f2 = road_type_weight    (importance of road)
      f3 = speed_drop_ratio    (1 - effective_speed/free_flow_speed)
      f4 = emission_index      (emissions/length, normalised)
      f5 = is_freeway          (binary: expressway or highway)
    """
    vc          = road_state.get("vc_ratio", road_state.get("congestion_ratio", 0.5))
    volume      = road_state.get("volume", 0)
    capacity    = max(road_state.get("capacity", 2000), 1)
    eff_speed   = road_state.get("effective_speed", road_state.get("speed_kmh", 40))
    road_type   = road_state.get("road_type", "arterial")
    emissions   = road_state.get("emissions", 0)
    length_km   = road_state.get("length_km", 1)

    ff_speed = 60.0  # free-flow default
    if road_def:
        ff_speed = road_def.get("free_flow_speed", 60)

    speed_drop = 1.0 - min(eff_speed / max(ff_speed, 1), 1.0)
    type_weight = _ROAD_TYPE_WEIGHT.get(road_type, 0.65)
    emit_idx    = emissions / max(length_km, 0.1) / 100   # normalise

    return np.array([
        np.clip(vc,          0.0, 2.0),
        np.clip(volume / max(capacity * 1.5, 1), 0.0, 1.0),
        type_weight,
        np.clip(speed_drop,  0.0, 1.0),
        np.clip(emit_idx,    0.0, 1.0),
        1.0 if road_type in ("expressway", "highway") else 0.0,
    ], dtype=np.float64)


def _build_feature_matrix(road_states: list, road_defs: dict = None) -> np.ndarray:
    """Stack feature vectors into (n_roads × n_features) matrix."""
    rows = []
    for rs in road_states:
        rid  = rs.get("road_id", rs.get("id", ""))
        rdef = (road_defs or {}).get(rid)
        rows.append(_road_features(rs, rdef))
    return np.array(rows, dtype=np.float64)   # shape: (n, 6)


def _normalize(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Z-score normalisation. Returns (X_norm, mean, std)."""
    mu  = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0   # avoid division by zero for constant features
    return (X - mu) / std, mu, std


# ── K-Means++ ─────────────────────────────────────────────────────────

def _kmeans_plus_plus_init(X: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """
    K-Means++ initialisation: choose centres proportional to D² distance.
    Guarantees O(log k) approximation vs random init.
    """
    n = X.shape[0]
    centres = [X[rng.integers(n)]]   # first centre: random point

    for _ in range(1, k):
        # Squared distances from each point to nearest centre
        dists = np.array([min(np.sum((x - c) ** 2) for c in centres) for x in X])
        probs = dists / dists.sum()
        idx   = rng.choice(n, p=probs)
        centres.append(X[idx])

    return np.array(centres)   # shape: (k, n_features)


def _lloyd_iteration(X: np.ndarray, centres: np.ndarray,
                     max_iter: int = 100, tol: float = 1e-6) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Lloyd's algorithm: alternate assignment + centroid update until convergence.
    Returns (labels, final_centres, inertia).
    """
    k = centres.shape[0]

    for iteration in range(max_iter):
        # Assignment step: assign each point to nearest centre
        diffs   = X[:, None, :] - centres[None, :, :]  # (n, k, d)
        dists_sq = np.sum(diffs ** 2, axis=2)           # (n, k)
        labels  = np.argmin(dists_sq, axis=1)            # (n,)

        # Update step: recompute centroids
        new_centres = np.zeros_like(centres)
        for c in range(k):
            mask = labels == c
            if mask.sum() > 0:
                new_centres[c] = X[mask].mean(axis=0)
            else:
                # Empty cluster → reinitialise to a random point
                new_centres[c] = X[np.random.randint(len(X))]

        shift = np.sqrt(np.sum((new_centres - centres) ** 2))
        centres = new_centres

        if shift < tol:
            break

    inertia = float(np.sum(np.min(np.sum((X[:, None, :] - centres[None, :, :]) ** 2, axis=2), axis=1)))
    return labels, centres, inertia


def _elbow_k(inertias: List[float]) -> int:
    """
    Elbow method: find K where adding another cluster gives diminishing returns.
    Uses the 'knee point' via maximum distance from the line joining first and last.
    """
    if len(inertias) <= 2:
        return len(inertias)
    n = len(inertias)
    coords = np.array([[i, inertias[i]] for i in range(n)], dtype=float)
    # Normalise so both axes are comparable
    coords[:, 0] /= (n - 1)
    coords[:, 1] /= (inertias[0] + 1e-9)
    # Vector from first to last point
    d = coords[-1] - coords[0]
    d_unit = d / (np.linalg.norm(d) + 1e-12)
    # Distance from line for each point
    dists = np.abs(np.cross(d_unit, coords - coords[0]))
    return int(np.argmax(dists))


# ── Main clustering class ──────────────────────────────────────────────

class RoadCongestionClusterer:
    """
    K-Means++ clustering of road segments by congestion profile.

    Usage:
        clusterer = RoadCongestionClusterer()
        result    = clusterer.fit(road_states, road_defs)
        # result → { clusters, labels, centroids, k, silhouette, summary }
    """

    def __init__(self, k_range: Tuple[int, int] = (2, 5), seed: int = 0):
        self.k_min, self.k_max = k_range
        self.rng    = np.random.default_rng(seed)
        self.labels_    = None
        self.centroids_ = None
        self.k_         = None
        self._X_norm    = None
        self._mu        = None
        self._std       = None
        self._road_ids  = None

    def fit(self, road_states: list, road_defs: dict = None) -> dict:
        """
        Fit K-Means++ on road_states. Automatically selects best K via elbow.
        Returns full clustering result dict.
        """
        if len(road_states) < 2:
            return {"error": "Need at least 2 roads"}

        # Build and normalise feature matrix
        X              = _build_feature_matrix(road_states, road_defs)
        X_norm, mu, std = _normalize(X)
        self._X_norm   = X_norm
        self._mu       = mu
        self._std      = std
        self._road_ids = [rs.get("road_id", rs.get("id", f"road_{i}")) for i, rs in enumerate(road_states)]

        # Try each k and record inertia
        k_max     = min(self.k_max, len(road_states) - 1)
        inertias  = []
        solutions = []

        for k in range(self.k_min, k_max + 1):
            centres  = _kmeans_plus_plus_init(X_norm, k, self.rng)
            labels, centres, inertia = _lloyd_iteration(X_norm, centres)
            inertias.append(inertia)
            solutions.append((k, labels, centres, inertia))

        # Elbow: best k
        best_idx   = _elbow_k(inertias)
        best_idx   = min(best_idx, len(solutions) - 1)
        k, labels, centres, inertia = solutions[best_idx]

        self.k_         = k
        self.labels_    = labels
        self.centroids_ = centres

        # Silhouette score (simplified: mean of (b-a)/max(a,b) per point)
        sil = self._silhouette(X_norm, labels, k)

        # Build human-readable cluster summaries
        clusters = self._summarise(road_states, labels, X, k)

        return {
            "k":              k,
            "algorithm":      "K-Means++ (Lloyd's algorithm, elbow K selection)",
            "inertia":        round(inertia, 3),
            "silhouette":     round(sil, 3),
            "n_roads":        len(road_states),
            "clusters":       clusters,
            "road_labels":    {rid: int(lbl) for rid, lbl in zip(self._road_ids, labels)},
            "hotspot_cluster":self._hotspot_cluster(clusters),
        }

    def _silhouette(self, X: np.ndarray, labels: np.ndarray, k: int) -> float:
        """Simplified silhouette: mean (b - a) / max(a, b) for each point."""
        n = len(X)
        if n < 2 or k < 2:
            return 0.0
        scores = []
        for i in range(n):
            same   = X[labels == labels[i]]
            if len(same) > 1:
                a = float(np.mean(np.sqrt(np.sum((same - X[i]) ** 2, axis=1))))
            else:
                a = 0.0
            bs = []
            for c in range(k):
                if c == labels[i]:
                    continue
                other = X[labels == c]
                if len(other) > 0:
                    bs.append(float(np.mean(np.sqrt(np.sum((other - X[i]) ** 2, axis=1)))))
            b = min(bs) if bs else 0.0
            mx = max(a, b)
            scores.append((b - a) / mx if mx > 0 else 0.0)
        return float(np.mean(scores))

    def _summarise(self, road_states: list, labels: np.ndarray,
                   X_raw: np.ndarray, k: int) -> List[dict]:
        """Summarise each cluster with aggregate stats and road list."""
        LEVEL_NAMES = ["Free Flow", "Moderate", "Congested", "Breakdown", "Severe"]
        clusters = []
        for c in range(k):
            mask = labels == c
            idxs = np.where(mask)[0]
            if len(idxs) == 0:
                continue
            c_roads   = [road_states[i] for i in idxs]
            c_X       = X_raw[mask]
            avg_vc    = float(np.mean(c_X[:, 0]))
            avg_speed = float(np.mean([r.get("effective_speed", r.get("speed_kmh", 40)) for r in c_roads]))
            avg_emit  = float(np.mean([r.get("emissions", 0) for r in c_roads]))

            if avg_vc < 0.60:   level, color = "Free Flow",  "#00e400"
            elif avg_vc < 0.85: level, color = "Moderate",   "#e6e600"
            elif avg_vc < 1.00: level, color = "Congested",  "#ff7e00"
            else:               level, color = "Breakdown",  "#8f3f97"

            clusters.append({
                "cluster_id":   c,
                "level":        level,
                "color":        color,
                "n_roads":      int(len(idxs)),
                "avg_vc":       round(avg_vc, 3),
                "avg_speed_kmh":round(avg_speed, 1),
                "avg_emissions":round(avg_emit, 2),
                "road_ids":     [road_states[i].get("road_id", road_states[i].get("id", "")) for i in idxs],
                "road_names":   [road_states[i].get("road_name", road_states[i].get("name", "")) for i in idxs],
            })

        clusters.sort(key=lambda c: c["avg_vc"], reverse=True)
        return clusters

    def _hotspot_cluster(self, clusters: list) -> Optional[dict]:
        """Return the worst (highest avg VC) cluster, if it's actually congested."""
        if not clusters:
            return None
        worst = clusters[0]
        if worst["avg_vc"] > 0.80:
            return {"cluster_id": worst["cluster_id"], "level": worst["level"],
                    "road_ids": worst["road_ids"], "avg_vc": worst["avg_vc"]}
        return None
