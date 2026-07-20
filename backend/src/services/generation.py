from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.weather import weather_series
from src.ml.forecaster import forecast_series


ASSET_META = {
    "solar_tokyo_1": {"asset_type": "solar", "capacity_mw": 50.0, "region": "tokyo"},
    "wind_kyushu_1": {"asset_type": "wind", "capacity_mw": 80.0, "region": "kyushu"},
    "battery_tokyo_1": {"asset_type": "battery", "capacity_mw": 20.0, "region": "tokyo"},
}


def _weather_driven_history(asset_type: str, capacity_mw: float, region: str, hours: int = 168) -> pd.DataFrame:
    wx = weather_series(region=region, hours=hours)
    rng = np.random.default_rng(21)
    if asset_type == "solar":
        # Temp derating above 25C
        derate = 1.0 - np.clip((wx["temp_c"] - 25.0) * 0.004, 0, 0.15)
        mw = capacity_mw * wx["ghi"] * derate
    elif asset_type == "wind":
        # Cubic-ish wind power curve proxy
        wf = np.clip(wx["wind_factor"], 0, 1.1)
        mw = capacity_mw * np.clip(wf**3 / 0.4, 0, 1.0)
    else:
        mw = np.clip(rng.normal(capacity_mw * 0.35, capacity_mw * 0.05, size=len(wx)), 0, capacity_mw)
    noise = rng.normal(0, capacity_mw * 0.02, size=len(wx))
    values = np.clip(mw + noise, 0, capacity_mw)
    return pd.DataFrame({"ts": wx["ts"], "mw": values})


def forecast_generation(asset_code: str = "solar_tokyo_1", horizon_hours: int = 48) -> dict:
    meta = ASSET_META.get(asset_code, ASSET_META["solar_tokyo_1"])
    hist = _weather_driven_history(
        asset_type=meta["asset_type"],
        capacity_mw=meta["capacity_mw"],
        region=meta["region"],
        hours=168,
    )
    result = forecast_series(hist, "mw", horizon=horizon_hours)
    cap = meta["capacity_mw"]
    for row in result.forecast:
        row["value"] = max(0.0, min(row["value"], cap))
        row["p10"] = max(0.0, min(row.get("p10", row["value"]), cap))
        row["p90"] = max(0.0, min(row.get("p90", row["value"]), cap))

    return {
        "module": "generation",
        "asset_code": asset_code,
        "asset_type": meta["asset_type"],
        "capacity_mw": cap,
        "region": meta["region"],
        "unit": "MW",
        "model": f"weather_{result.model_name}",
        "metrics": result.metrics,
        "history": result.history,
        "forecast": result.forecast,
        "drivers": ["ghi", "wind_factor", "temp_c"],
    }
