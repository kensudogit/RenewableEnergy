from fastapi import APIRouter, Query

from src.services.demand import forecast_demand
from src.services.dr import plan_demand_response
from src.services.fuel_price import forecast_fuel_price
from src.services.generation import forecast_generation
from src.services.market_price import forecast_market_price
from src.services.optimize import optimize_battery_dispatch
from src.services.revenue import simulate_revenue
from src.services.risk import analyze_risk
from src.services.vpp import aggregate_vpp

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def dashboard(
    region: str = Query("tokyo"),
    asset_code: str = Query("solar_tokyo_1"),
    market: str = Query("jepx_spot"),
    commodity: str = Query("lng"),
):
    gen = forecast_generation(asset_code=asset_code, horizon_hours=48)
    dem = forecast_demand(region=region, horizon_hours=48)
    price = forecast_market_price(market=market, horizon_hours=48)
    fuel = forecast_fuel_price(commodity=commodity, horizon_hours=48)
    risk = analyze_risk(asset_code=asset_code, market=market)
    rev = simulate_revenue(asset_code=asset_code, market=market, region=region)
    opt = optimize_battery_dispatch(asset_code=asset_code, market=market, horizon_hours=24)
    vpp = aggregate_vpp(region=region, horizon_hours=24)
    dr = plan_demand_response(region=region, horizon_hours=24)

    return {
        "region": region,
        "asset_code": asset_code,
        "modules": {
            "generation": {
                "unit": gen["unit"],
                "model": gen["model"],
                "metrics": gen["metrics"],
                "next_24h_avg": round(
                    sum(x["value"] for x in gen["forecast"][:24]) / 24, 3
                ),
                "forecast": gen["forecast"][:24],
            },
            "demand": {
                "unit": dem["unit"],
                "metrics": dem["metrics"],
                "next_24h_avg": round(
                    sum(x["value"] for x in dem["forecast"][:24]) / 24, 1
                ),
                "forecast": dem["forecast"][:24],
            },
            "market_price": {
                "unit": price["unit"],
                "metrics": price["metrics"],
                "next_24h_avg": round(
                    sum(x["value"] for x in price["forecast"][:24]) / 24, 3
                ),
                "forecast": price["forecast"][:24],
            },
            "fuel_price": {
                "unit": fuel["unit"],
                "commodity": commodity,
                "metrics": fuel["metrics"],
                "next_24h_avg": round(
                    sum(x["value"] for x in fuel["forecast"][:24]) / 24, 3
                ),
                "forecast": fuel["forecast"][:24],
            },
            "risk": risk["metrics"],
            "revenue": rev["summary"],
            "battery_optimize": opt["summary"],
            "vpp": vpp["summary"],
            "demand_response": dr["summary"],
        },
    }
