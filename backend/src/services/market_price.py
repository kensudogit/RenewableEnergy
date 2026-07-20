from __future__ import annotations

from src.data.synthetic import market_price_series
from src.ml.forecaster import forecast_series


def forecast_market_price(market: str = "jepx_spot", horizon_hours: int = 48) -> dict:
    hist = market_price_series(market=market, hours=168)
    result = forecast_series(hist, "yen_per_kwh", horizon=horizon_hours)
    for row in result.forecast:
        row["value"] = max(0.0, row["value"])
        row["p10"] = max(0.0, row["p10"])
        row["p90"] = max(0.0, row["p90"])
    return {
        "module": "market_price",
        "market": market,
        "unit": "JPY/kWh",
        "model": result.model_name,
        "metrics": result.metrics,
        "history": result.history,
        "forecast": result.forecast,
    }
