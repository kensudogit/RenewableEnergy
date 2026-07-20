from __future__ import annotations

from src.data.synthetic import fuel_price_series
from src.ml.forecaster import forecast_series


def forecast_fuel_price(commodity: str = "lng", horizon_hours: int = 48) -> dict:
    hist = fuel_price_series(commodity=commodity, hours=168 * 2)
    unit = str(hist["unit"].iloc[0])
    result = forecast_series(hist, "usd_per_unit", horizon=horizon_hours)
    return {
        "module": "fuel_price",
        "commodity": commodity,
        "unit": f"USD/{unit}",
        "model": result.model_name,
        "metrics": result.metrics,
        "history": result.history,
        "forecast": result.forecast,
    }
