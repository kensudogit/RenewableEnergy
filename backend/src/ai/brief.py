from __future__ import annotations

from src.ai.client import chat_json
from src.services.demand import forecast_demand
from src.services.fuel_price import forecast_fuel_price
from src.services.generation import forecast_generation
from src.services.market_price import forecast_market_price
from src.services.risk import analyze_risk


def market_brief(region: str = "tokyo", asset_code: str = "solar_tokyo_1") -> dict:
    gen = forecast_generation(asset_code=asset_code, horizon_hours=24)
    dem = forecast_demand(region=region, horizon_hours=24)
    price = forecast_market_price(horizon_hours=24)
    fuel = forecast_fuel_price(commodity="lng", horizon_hours=24)
    risk = analyze_risk(asset_code=asset_code)

    context = {
        "generation_avg_mw": sum(x["value"] for x in gen["forecast"]) / len(gen["forecast"]),
        "demand_avg_mw": sum(x["value"] for x in dem["forecast"]) / len(dem["forecast"]),
        "price_avg": sum(x["value"] for x in price["forecast"]) / len(price["forecast"]),
        "lng_avg": sum(x["value"] for x in fuel["forecast"]) / len(fuel["forecast"]),
        "risk_score": risk["metrics"]["risk_score"],
    }

    ai = chat_json(
        system=(
            "You are an energy market analyst for Japanese renewable assets. "
            'Return JSON: {"summary": str, "insights": [str], "actions": [str]}'
        ),
        user=f"次の指標から市場ブリーフを作成: {context}",
    )
    return {"module": "market_brief", "context": context, "ai": ai}
