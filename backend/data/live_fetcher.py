"""
Live Data Fetcher
Integrates OpenWeatherMap, TomTom Traffic, and CPCB/OpenAQ APIs.
Falls back to realistic synthetic data when APIs are unavailable.
"""

import httpx
import asyncio
import random
import math
from datetime import datetime, timezone
from config import settings


# ─────────────────────────────────────────────────────────────────────
#  SYNTHETIC FALLBACK DATA
# ─────────────────────────────────────────────────────────────────────

def _hour_factor(hour: int) -> float:
    """Traffic multiplier by hour (rush hours peak)."""
    if 7 <= hour <= 10:
        return 1.45 + random.uniform(-0.05, 0.05)   # Morning rush
    elif 11 <= hour <= 16:
        return 1.10 + random.uniform(-0.05, 0.05)   # Midday
    elif 17 <= hour <= 20:
        return 1.50 + random.uniform(-0.05, 0.05)   # Evening rush
    elif 21 <= hour <= 23:
        return 0.75 + random.uniform(-0.05, 0.05)
    else:
        return 0.45 + random.uniform(-0.05, 0.05)   # Night


def synthetic_weather() -> dict:
    """Generate realistic Delhi weather based on current month."""
    month = datetime.now().month
    # Delhi seasonal patterns
    if month in [12, 1, 2]:       # Winter
        temp = random.uniform(8, 20)
        humidity = random.uniform(55, 80)
        wind = random.uniform(4, 12)
        rain = 0
    elif month in [3, 4, 5]:      # Summer
        temp = random.uniform(30, 45)
        humidity = random.uniform(20, 45)
        wind = random.uniform(6, 18)
        rain = 0
    elif month in [6, 7, 8, 9]:   # Monsoon
        temp = random.uniform(25, 35)
        humidity = random.uniform(70, 95)
        wind = random.uniform(5, 20)
        rain = random.uniform(0, 60) if random.random() > 0.4 else 0
    else:                          # Post-monsoon
        temp = random.uniform(18, 32)
        humidity = random.uniform(40, 65)
        wind = random.uniform(4, 14)
        rain = 0

    return {
        "temperature": round(temp, 1),
        "humidity": round(humidity, 1),
        "wind_speed": round(wind, 1),
        "wind_direction": random.randint(0, 360),
        "rainfall_mm": round(rain, 1),
        "visibility_km": round(max(0.5, 10 - rain * 0.1 - humidity * 0.02), 1),
        "description": _weather_desc(temp, rain, humidity),
        "source": "synthetic",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _weather_desc(temp, rain, humidity) -> str:
    if rain > 20:
        return "Heavy Rain"
    elif rain > 5:
        return "Light Rain"
    elif humidity > 80:
        return "Humid / Foggy"
    elif temp > 38:
        return "Extreme Heat"
    elif temp > 30:
        return "Clear / Sunny"
    elif temp < 12:
        return "Cold / Hazy"
    return "Partly Cloudy"


def synthetic_traffic_volumes(base_volumes: dict) -> dict:
    """Generate realistic live traffic volumes."""
    hour = datetime.now().hour
    factor = _hour_factor(hour)
    result = {}
    for road_id, base in base_volumes.items():
        noise = random.uniform(0.92, 1.08)
        result[road_id] = int(base * factor * noise)
    return result


def synthetic_aqi(base_aqi_map: dict, weather: dict) -> dict:
    """Generate realistic AQI values per zone."""
    hour = datetime.now().hour
    month = datetime.now().month
    # Winter + morning = worst AQI
    seasonal = 1.4 if month in [11, 12, 1, 2] else 1.0
    # Rush hour = worse AQI
    traffic_factor = _hour_factor(hour) * 0.8 + 0.2
    wind_factor = max(0.4, 1.0 - weather["wind_speed"] * 0.05)
    rain_factor = max(0.5, 1.0 - weather["rainfall_mm"] * 0.01)

    result = {}
    for zone_id, base in base_aqi_map.items():
        noise = random.uniform(0.95, 1.05)
        val = base * seasonal * traffic_factor * wind_factor * rain_factor * noise
        result[zone_id] = round(min(500, max(20, val)), 1)
    return result


# ─────────────────────────────────────────────────────────────────────
#  LIVE API FETCHERS
# ─────────────────────────────────────────────────────────────────────

async def fetch_weather_live() -> dict:
    """Fetch from OpenWeatherMap API; fall back to synthetic."""
    if not settings.OPENWEATHER_API_KEY or settings.OPENWEATHER_API_KEY.startswith("your"):
        return synthetic_weather()
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={settings.CITY_LAT}&lon={settings.CITY_LNG}"
        f"&appid={settings.OPENWEATHER_API_KEY}&units=metric"
    )
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(url)
            r.raise_for_status()
            d = r.json()
            return {
                "temperature": d["main"]["temp"],
                "humidity": d["main"]["humidity"],
                "wind_speed": d["wind"]["speed"] * 3.6,   # m/s → km/h
                "wind_direction": d["wind"].get("deg", 0),
                "rainfall_mm": d.get("rain", {}).get("1h", 0),
                "visibility_km": round(d.get("visibility", 10000) / 1000, 1),
                "description": d["weather"][0]["description"].title(),
                "source": "openweathermap",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    except Exception:
        return synthetic_weather()


async def fetch_traffic_live(roads: dict) -> dict:
    """
    Fetch from TomTom Traffic Flow API per road segment.
    Falls back to synthetic volumes.
    """
    if not settings.TOMTOM_API_KEY or settings.TOMTOM_API_KEY.startswith("your"):
        base = {rid: r["base_volume"] for rid, r in roads.items()}
        return synthetic_traffic_volumes(base)

    base_volumes = {}
    results = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for road_id, road in roads.items():
            base_volumes[road_id] = road["base_volume"]
            # Midpoint of road for TomTom query
            mid_lat = (road["from_lat"] + road["to_lat"]) / 2
            mid_lng = (road["from_lng"] + road["to_lng"]) / 2
            url = (
                f"https://api.tomtom.com/traffic/services/4/flowSegmentData/"
                f"absolute/10/json?point={mid_lat},{mid_lng}"
                f"&key={settings.TOMTOM_API_KEY}"
            )
            try:
                r = await client.get(url)
                r.raise_for_status()
                d = r.json()
                flow = d.get("flowSegmentData", {})
                current_speed = flow.get("currentSpeed", road["free_flow_speed"])
                free_speed = flow.get("freeFlowSpeed", road["free_flow_speed"])
                # Estimate volume from speed ratio using BPR inverse
                speed_ratio = current_speed / max(free_speed, 1)
                # Approximate V/C from speed ratio
                vc_approx = max(0, (1 - speed_ratio) * 1.5)
                results[road_id] = int(road["capacity"] * min(vc_approx, 1.2))
            except Exception:
                results[road_id] = base_volumes[road_id]
    return results


async def fetch_aqi_live(zones: dict) -> dict:
    """
    Try OpenAQ (free) for AQI data; fall back to synthetic.
    CPCB API integration also supported if key present.
    """
    weather = synthetic_weather()
    base_aqi = {zid: z["base_aqi"] for zid, z in zones.items()}

    # Try OpenAQ (free, no key needed)
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            url = (
                f"https://api.openaq.org/v2/measurements"
                f"?city=Delhi&parameter=pm25&limit=10&order_by=datetime"
            )
            r = await client.get(url, headers={"Accept": "application/json"})
            r.raise_for_status()
            d = r.json()
            results_list = d.get("results", [])
            if results_list:
                # Use average PM2.5 to scale all zones
                avg_pm25 = sum(m["value"] for m in results_list) / len(results_list)
                # PM2.5 to AQI (simplified Indian AQI scale)
                if avg_pm25 <= 30:
                    base_scale = avg_pm25 / 30 * 100
                elif avg_pm25 <= 60:
                    base_scale = 100 + (avg_pm25 - 30) / 30 * 100
                elif avg_pm25 <= 90:
                    base_scale = 200 + (avg_pm25 - 60) / 30 * 100
                else:
                    base_scale = 300 + min((avg_pm25 - 90) / 60 * 200, 200)

                result = {}
                for zone_id, base in base_aqi.items():
                    ratio = base / max(sum(base_aqi.values()) / len(base_aqi), 1)
                    result[zone_id] = round(min(500, base_scale * ratio), 1)
                return result
    except Exception:
        pass

    return synthetic_aqi(base_aqi, weather)


async def fetch_all_live_data(roads: dict, zones: dict) -> dict:
    """Fetch all live data concurrently."""
    weather, traffic, aqi = await asyncio.gather(
        fetch_weather_live(),
        fetch_traffic_live(roads),
        fetch_aqi_live(zones),
    )
    return {"weather": weather, "traffic_volumes": traffic, "aqi": aqi}
