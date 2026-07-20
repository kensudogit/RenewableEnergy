from fastapi import APIRouter, Query

from src.services.demand import forecast_demand
from src.services.fuel_price import forecast_fuel_price
from src.services.generation import forecast_generation
from src.services.market_price import forecast_market_price

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("/generation")
def generation(
    asset_code: str = Query("solar_tokyo_1"),
    horizon_hours: int = Query(48, ge=1, le=168),
):
    return forecast_generation(asset_code=asset_code, horizon_hours=horizon_hours)


@router.get("/demand")
def demand(
    region: str = Query("tokyo"),
    horizon_hours: int = Query(48, ge=1, le=168),
):
    return forecast_demand(region=region, horizon_hours=horizon_hours)


@router.get("/market-price")
def market_price(
    market: str = Query("jepx_spot"),
    horizon_hours: int = Query(48, ge=1, le=168),
):
    return forecast_market_price(market=market, horizon_hours=horizon_hours)


@router.get("/fuel-price")
def fuel_price(
    commodity: str = Query("lng"),
    horizon_hours: int = Query(48, ge=1, le=168),
):
    return forecast_fuel_price(commodity=commodity, horizon_hours=horizon_hours)
