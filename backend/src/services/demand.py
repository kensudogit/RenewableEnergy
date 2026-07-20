from __future__ import annotations

from src.data.synthetic import demand_series
from src.ml.forecaster import forecast_series


def forecast_demand(region: str = "tokyo", horizon_hours: int = 48) -> dict:
    hist = demand_series(region=region, hours=168)
    result = forecast_series(hist, "mw", horizon=horizon_hours)
    return {
        "module": "demand",
        "region": region,
        "unit": "MW",
        "model": result.model_name,
        "metrics": result.metrics,
        "history": result.history,
        "forecast": result.forecast,
    }
