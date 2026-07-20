"""Synthetic weather drivers for generation / demand coupling."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd


REGION_CLIMATE = {
    "tokyo": {"lat": 35.68, "irradiance_peak": 0.92, "wind_mean": 0.35, "temp_mean": 18.0},
    "kansai": {"lat": 34.69, "irradiance_peak": 0.90, "wind_mean": 0.32, "temp_mean": 17.5},
    "chubu": {"lat": 35.18, "irradiance_peak": 0.88, "wind_mean": 0.40, "temp_mean": 16.0},
    "kyushu": {"lat": 33.59, "irradiance_peak": 0.95, "wind_mean": 0.55, "temp_mean": 19.0},
}


def weather_series(region: str = "tokyo", hours: int = 168) -> pd.DataFrame:
    climate = REGION_CLIMATE.get(region, REGION_CLIMATE["tokyo"])
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    idx = pd.date_range(end=end, periods=hours, freq="h", tz=timezone.utc)
    hour = np.array([t.hour for t in idx])
    day = np.arange(len(idx))
    rng = np.random.default_rng(abs(hash(region)) % (2**32))

    solar_angle = np.clip(np.sin((hour - 6) / 12 * np.pi), 0, None)
    cloud = 0.55 + 0.35 * np.sin(day / 36 * 2 * np.pi) + rng.normal(0, 0.08, size=len(idx))
    cloud = np.clip(cloud, 0.15, 1.0)
    ghi = climate["irradiance_peak"] * solar_angle * cloud  # 0-1 proxy
    wind = climate["wind_mean"] + 0.25 * np.sin(day / 18 * 2 * np.pi) + rng.normal(0, 0.07, size=len(idx))
    wind = np.clip(wind, 0.05, 1.2)
    temp = climate["temp_mean"] + 6 * np.sin((hour - 14) / 24 * 2 * np.pi) + rng.normal(0, 0.8, size=len(idx))

    return pd.DataFrame(
        {
            "ts": idx,
            "ghi": ghi,
            "wind_factor": wind,
            "temp_c": temp,
            "cloud_factor": cloud,
            "region": region,
        }
    )


def weather_forecast(region: str = "tokyo", horizon_hours: int = 48) -> dict:
    hist = weather_series(region=region, hours=168)
    # Naive persistence of diurnal pattern for next horizon
    pattern = hist.tail(24)
    rows = []
    last_ts = pd.Timestamp(hist["ts"].iloc[-1])
    for i in range(horizon_hours):
        src = pattern.iloc[i % 24]
        rows.append(
            {
                "ts": (last_ts + timedelta(hours=i + 1)).isoformat(),
                "ghi": round(float(src["ghi"]), 4),
                "wind_factor": round(float(src["wind_factor"]), 4),
                "temp_c": round(float(src["temp_c"]), 2),
                "cloud_factor": round(float(src["cloud_factor"]), 4),
            }
        )
    return {
        "module": "weather",
        "region": region,
        "history": [
            {
                "ts": pd.Timestamp(r.ts).isoformat(),
                "ghi": round(float(r.ghi), 4),
                "wind_factor": round(float(r.wind_factor), 4),
                "temp_c": round(float(r.temp_c), 2),
            }
            for r in hist.tail(72).itertuples(index=False)
        ],
        "forecast": rows,
    }
