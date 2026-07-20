"""Synthetic time-series generators for local / demo mode."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd


def _hours(horizon: int, end: datetime | None = None) -> pd.DatetimeIndex:
    end = end or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(hours=horizon - 1)
    return pd.date_range(start=start, periods=horizon, freq="h", tz=timezone.utc)


def generation_series(
    asset_type: str = "solar",
    capacity_mw: float = 50.0,
    hours: int = 168,
) -> pd.DataFrame:
    idx = _hours(hours)
    hour = np.array([t.hour for t in idx])
    day = np.arange(len(idx))
    rng = np.random.default_rng(42)

    if asset_type == "solar":
        # Daylight bell + mild weather noise
        base = np.clip(np.sin((hour - 6) / 12 * np.pi), 0, None) * capacity_mw
        noise = rng.normal(0, capacity_mw * 0.05, size=len(idx))
        values = np.clip(base + noise, 0, capacity_mw)
    elif asset_type == "wind":
        base = capacity_mw * (0.35 + 0.25 * np.sin(day / 24 * 2 * np.pi))
        noise = rng.normal(0, capacity_mw * 0.1, size=len(idx))
        values = np.clip(base + noise, 0, capacity_mw)
    else:
        values = np.clip(rng.normal(capacity_mw * 0.4, capacity_mw * 0.05, size=len(idx)), 0, capacity_mw)

    return pd.DataFrame({"ts": idx, "mw": values})


def demand_series(region: str = "tokyo", hours: int = 168) -> pd.DataFrame:
    idx = _hours(hours)
    hour = np.array([t.hour for t in idx])
    dow = np.array([t.weekday() for t in idx])
    rng = np.random.default_rng(7)
    base_map = {"tokyo": 32000, "kansai": 14000, "chubu": 12000, "kyushu": 8000}
    base = base_map.get(region, 10000)
    profile = 0.75 + 0.25 * np.sin((hour - 8) / 24 * 2 * np.pi)
    weekend = np.where(dow >= 5, 0.92, 1.0)
    noise = rng.normal(0, base * 0.02, size=len(idx))
    values = base * profile * weekend + noise
    return pd.DataFrame({"ts": idx, "mw": values})


def market_price_series(market: str = "jepx_spot", hours: int = 168) -> pd.DataFrame:
    idx = _hours(hours)
    hour = np.array([t.hour for t in idx])
    rng = np.random.default_rng(99)
    # Yen/kWh-ish spot shape
    base = 8 + 6 * np.sin((hour - 10) / 24 * 2 * np.pi) ** 2
    spikes = np.where((hour >= 17) & (hour <= 20), 4.0, 0.0)
    noise = rng.normal(0, 1.2, size=len(idx))
    values = np.clip(base + spikes + noise, 0.5, None)
    return pd.DataFrame({"ts": idx, "yen_per_kwh": values, "market_code": market})


def fuel_price_series(commodity: str = "lng", hours: int = 168 * 4) -> pd.DataFrame:
    # Daily-ish series compressed to hourly for uniform API
    idx = _hours(hours)
    rng = np.random.default_rng(abs(hash(commodity)) % (2**32))
    anchors = {"lng": 12.5, "coal": 140.0, "oil": 78.0}
    unit = {"lng": "mmbtu", "coal": "ton", "oil": "bbl"}.get(commodity, "unit")
    base = anchors.get(commodity, 10.0)
    walk = np.cumsum(rng.normal(0, base * 0.002, size=len(idx)))
    values = np.clip(base + walk, base * 0.5, None)
    return pd.DataFrame(
        {"ts": idx, "usd_per_unit": values, "commodity": commodity, "unit": unit}
    )
