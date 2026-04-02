"""
Traffic Volume Predictor — Polynomial Regression
=================================================
Algorithm: Ridge-regularized Polynomial Regression (degree 3) trained
           on synthetically generated Delhi traffic patterns.

Features:
  x1 = hour_sin         sine encoding of hour-of-day (captures cyclical daily pattern)
  x2 = hour_cos         cosine encoding of hour-of-day
  x3 = is_peak          binary: 1 during peak hours (7-10, 17-20)
  x4 = weekday_factor   1.0 Mon-Fri, 0.75 Sat, 0.55 Sun
  x5 = temperature_norm  normalised temperature (heat reduces output speeds)
  x6 = rain_factor      0 = dry, 1 = heavy rain (reduces capacity usage)
  x7 = road_capacity    normalised road capacity (larger roads carry more)

Polynomial expansion of degree 2 gives interaction terms:
  [1, x1, x2, ..., x7, x1², x1·x2, ..., x7²]  → 36 features

Training data: synthetically generated 7-day × 24-hour Delhi traffic matrix
               with realistic rush-hour/off-peak/monsoon patterns per road type.

Prediction: next 6 hours of traffic volume for each road.
"""

import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List


# ── Constants ──────────────────────────────────────────────────────────

_PEAK_HOURS = set(range(7, 10)) | set(range(17, 20))
_DEGREE     = 2   # polynomial degree (3 overfits on sparse synthetic data)
_LAMBDA     = 0.1  # L2 regularisation (ridge penalty)


# ── Feature engineering ────────────────────────────────────────────────

def _time_features(hour: float, weekday: int) -> np.ndarray:
    """Encode time as cyclical + binary features."""
    angle      = 2 * math.pi * hour / 24
    is_peak    = 1.0 if int(hour) in _PEAK_HOURS else 0.0
    wd_factors = {0:1.0, 1:1.0, 2:1.0, 3:1.0, 4:0.95, 5:0.75, 6:0.55}
    weekday_f  = wd_factors.get(weekday % 7, 1.0)
    return np.array([math.sin(angle), math.cos(angle), is_peak, weekday_f])


def _weather_features(weather: dict) -> np.ndarray:
    temp      = weather.get("temperature", 28)
    rain_mm   = weather.get("rainfall_mm", 0)
    temp_norm  = np.clip((temp - 10) / 40, 0, 1)   # normalise 10-50°C → 0-1
    rain_factor= np.clip(rain_mm / 60, 0, 1)        # 0=dry, 1=60mm/hr flood
    return np.array([temp_norm, rain_factor])


def _road_feature(road: dict) -> np.ndarray:
    cap = road.get("capacity", 2000)
    return np.array([np.clip(cap / 8000, 0, 1)])


def _build_feature_vector(hour: float, weekday: int,
                           weather: dict, road: dict) -> np.ndarray:
    """Raw feature vector (before polynomial expansion)."""
    return np.concatenate([
        _time_features(hour, weekday),
        _weather_features(weather),
        _road_feature(road),
    ])  # shape: (7,)


def _poly_expand(x: np.ndarray, degree: int = _DEGREE) -> np.ndarray:
    """
    Polynomial feature expansion with bias term.
    degree=2: [1, x1..xn, x1², x1·x2, ..., xn²]
    """
    n = len(x)
    features = [1.0]           # bias
    features.extend(x.tolist())  # degree 1

    if degree >= 2:
        for i in range(n):
            for j in range(i, n):
                features.append(x[i] * x[j])

    if degree >= 3:
        for i in range(n):
            for j in range(i, n):
                for k in range(j, n):
                    features.append(x[i] * x[j] * x[k])

    return np.array(features)


# ── Synthetic training data ────────────────────────────────────────────

def _synthetic_volume_ratio(hour: int, weekday: int,
                             rain_mm: float, temp: float) -> float:
    """
    Ground-truth volume ratio (0-1.6) for a typical Delhi road.
    Encodes:
      • Morning peak 7-10 → 1.35-1.50
      • Evening peak 17-20 → 1.40-1.55
      • Night 23-05 → 0.25-0.40
      • Rain penalty up to -35%
      • Weekend reduction -25-45%
      • Heat (>40°C) slight reduction (people avoid going out)
    """
    # Base hourly curve
    hour_curve = {
        0:0.25, 1:0.20, 2:0.18, 3:0.18, 4:0.22, 5:0.35,
        6:0.70, 7:1.30, 8:1.50, 9:1.40, 10:1.10,
        11:0.95, 12:0.90, 13:0.88, 14:0.85, 15:0.90,
        16:1.15, 17:1.40, 18:1.55, 19:1.45, 20:1.20,
        21:0.90, 22:0.65, 23:0.40,
    }
    base = hour_curve.get(hour, 0.8)

    # Weekend factor
    wf = {0:1.0,1:1.0,2:1.0,3:1.0,4:0.95,5:0.75,6:0.55}.get(weekday%7, 1.0)
    base *= wf

    # Rain penalty (20mm/hr → -35%)
    rain_pen = 1.0 - min(rain_mm / 60, 0.35)
    base *= rain_pen

    # Extreme heat (>42°C → -10%)
    if temp > 42:
        base *= 0.90

    return float(np.clip(base, 0.15, 1.6))


def _generate_training_data(roads: list, n_days: int = 14) -> tuple:
    """
    Generate (X, y) training matrices over n_days × 24 hours.
    y = actual volume for each road at that hour.
    """
    X_rows, y_rows = [], []
    now  = datetime.now()
    rng  = np.random.default_rng(42)

    for day in range(n_days):
        dt      = now - timedelta(days=day)
        weekday = dt.weekday()
        rain_mm = float(rng.uniform(0, 40) if rng.random() < 0.2 else 0)
        temp    = float(rng.uniform(15, 45))
        weather = {"temperature": temp, "rainfall_mm": rain_mm}

        for hour in range(24):
            ratio = _synthetic_volume_ratio(hour, weekday, rain_mm, temp)
            raw_x = _build_feature_vector(float(hour), weekday, weather, {})
            phi   = _poly_expand(raw_x)

            for road in roads:
                cap     = road.get("capacity", 2000)
                base    = road.get("base_volume", cap * 0.6)
                noise   = float(rng.normal(1.0, 0.05))
                volume  = base * ratio * noise
                # Road-specific feature
                road_x  = _build_feature_vector(float(hour), weekday, weather, road)
                road_phi = _poly_expand(road_x)
                X_rows.append(road_phi)
                y_rows.append(volume)

    return np.array(X_rows, dtype=np.float64), np.array(y_rows, dtype=np.float64)


# ── Ridge Regression ───────────────────────────────────────────────────

def _ridge_fit(X: np.ndarray, y: np.ndarray, lam: float = _LAMBDA) -> np.ndarray:
    """
    Closed-form ridge regression: w = (XᵀX + λI)⁻¹ Xᵀy
    More numerically stable than normal equations without regularisation.
    """
    n_features = X.shape[1]
    A = X.T @ X + lam * np.eye(n_features)
    b = X.T @ y
    return np.linalg.solve(A, b)   # shape: (n_features,)


def _ridge_predict(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    return X @ w


# ── TrafficPredictor class ─────────────────────────────────────────────

class TrafficPredictor:
    """
    Ridge-regularised Polynomial Regression for per-road traffic forecasting.

    Usage:
        predictor = TrafficPredictor(roads)
        predictor.train()
        forecast = predictor.predict_next_hours(6, weather)
        # → { road_id: [vol_h+1, vol_h+2, ..., vol_h+6] }
    """

    def __init__(self, roads: list):
        self.roads     = roads
        self._road_map = {r["id"]: r for r in roads}
        self._weights  = {}   # road_id → weight vector (shared model per road type)
        self._trained  = False
        self._feature_dim = None

    def train(self) -> dict:
        """
        Train one shared model + per-road bias correction.
        Returns training summary stats.
        """
        if not self.roads:
            return {}

        X, y = _generate_training_data(self.roads)
        self._feature_dim = X.shape[1]

        # Single global model (roads share time/weather response)
        self._global_w = _ridge_fit(X, y)

        # Per-road bias: correct residuals road-by-road
        self._road_bias = {}
        n_roads = len(self.roads)
        for i, road in enumerate(self.roads):
            rid     = road["id"]
            # indices for this road across all (day,hour) samples
            indices = list(range(i, len(y), n_roads))
            if not indices:
                self._road_bias[rid] = 0.0
                continue
            y_sub    = y[indices]
            X_sub    = X[indices]
            y_pred   = _ridge_predict(X_sub, self._global_w)
            residual = y_sub - y_pred
            self._road_bias[rid] = float(np.mean(residual))

        # Compute training RMSE
        y_pred_all = _ridge_predict(X, self._global_w)
        rmse       = float(np.sqrt(np.mean((y - y_pred_all) ** 2)))
        r2         = float(1 - np.sum((y - y_pred_all)**2) / np.sum((y - np.mean(y))**2))

        self._trained = True
        return {"rmse": round(rmse, 1), "r2": round(r2, 4), "n_samples": len(y),
                "n_features": self._feature_dim, "algorithm": "Ridge Polynomial Regression (degree=2)"}

    def predict_next_hours(self, n_hours: int = 6,
                            weather: dict = None) -> Dict[str, List[dict]]:
        """
        Predict traffic volume for each road for the next n_hours.
        Returns dict: road_id → list of { hour, volume, congestion_ratio, los }
        """
        if not self._trained:
            self.train()

        weather  = weather or {}
        now      = datetime.now()
        weekday  = now.weekday()
        result   = {}

        for road in self.roads:
            rid    = road["id"]
            cap    = road.get("capacity", 2000)
            preds  = []

            for h in range(1, n_hours + 1):
                future_dt  = now + timedelta(hours=h)
                future_hour= future_dt.hour + future_dt.minute / 60
                future_wd  = future_dt.weekday()

                x    = _build_feature_vector(future_hour, future_wd, weather, road)
                phi  = _poly_expand(x)
                vol  = float(_ridge_predict(phi.reshape(1, -1), self._global_w)[0])
                vol += self._road_bias.get(rid, 0.0)
                vol  = max(0.0, vol)

                vc   = vol / max(cap, 1)
                los  = _vc_to_los(vc)
                preds.append({
                    "hour":             future_dt.strftime("%H:%M"),
                    "hour_label":       f"+{h}h",
                    "predicted_volume": int(round(vol)),
                    "predicted_vc":     round(min(vc, 2.0), 3),
                    "predicted_los":    los,
                    "congestion_pct":   round(min(vc * 100, 200), 1),
                })

            result[rid] = preds

        return result

    def peak_risk_assessment(self, weather: dict = None) -> List[dict]:
        """
        For each road, assess next-6hr peak congestion risk.
        Returns roads sorted by max predicted VC ratio (highest risk first).
        """
        forecast = self.predict_next_hours(6, weather)
        risks    = []
        for road in self.roads:
            rid    = road["id"]
            preds  = forecast.get(rid, [])
            if not preds:
                continue
            max_vc = max(p["predicted_vc"] for p in preds)
            peak_h = max(preds, key=lambda p: p["predicted_vc"])
            risks.append({
                "road_id":      rid,
                "road_name":    road.get("name", rid),
                "peak_vc":      max_vc,
                "peak_at":      peak_h["hour"],
                "peak_los":     peak_h["predicted_los"],
                "risk_level":   _risk_level(max_vc),
                "forecast":     preds,
            })

        risks.sort(key=lambda r: r["peak_vc"], reverse=True)
        return risks


# ── Helpers ────────────────────────────────────────────────────────────

def _vc_to_los(vc: float) -> str:
    if vc < 0.60: return "A"
    if vc < 0.70: return "B"
    if vc < 0.80: return "C"
    if vc < 0.90: return "D"
    if vc < 1.00: return "E"
    return "F"


def _risk_level(vc: float) -> str:
    if vc < 0.70: return "Low"
    if vc < 0.85: return "Moderate"
    if vc < 1.00: return "High"
    return "Critical"
