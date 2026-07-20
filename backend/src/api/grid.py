from fastapi import APIRouter, Query

from src.data.weather import weather_forecast
from src.services.dr import plan_demand_response
from src.services.market_engine import optimize_energy_market
from src.services.optimize import optimize_battery_dispatch
from src.services.vpp import aggregate_vpp

router = APIRouter(prefix="/api", tags=["grid"])


@router.get("/weather")
def weather(
    region: str = Query("tokyo"),
    horizon_hours: int = Query(48, ge=1, le=168),
):
    return weather_forecast(region=region, horizon_hours=horizon_hours)


@router.get("/optimize/battery")
def battery_optimize(
    asset_code: str = Query("solar_tokyo_1"),
    market: str = Query("jepx_spot"),
    horizon_hours: int = Query(48, ge=1, le=168),
    battery_mwh: float = Query(20.0, ge=0),
    max_power_mw: float = Query(5.0, gt=0),
    efficiency: float = Query(0.92, gt=0.5, le=1.0),
):
    return optimize_battery_dispatch(
        asset_code=asset_code,
        market=market,
        horizon_hours=horizon_hours,
        battery_mwh=battery_mwh,
        max_power_mw=max_power_mw,
        efficiency=efficiency,
    )


@router.get("/vpp")
def vpp(
    region: str = Query("tokyo"),
    horizon_hours: int = Query(24, ge=1, le=168),
    battery_mwh: float = Query(20.0, ge=0),
):
    return aggregate_vpp(
        region=region,
        horizon_hours=horizon_hours,
        battery_mwh=battery_mwh,
    )


@router.get("/dr")
def demand_response(
    region: str = Query("tokyo"),
    horizon_hours: int = Query(24, ge=1, le=168),
    curtail_pct: float = Query(0.08, ge=0, le=0.5),
    incentive_yen_per_kwh: float = Query(25.0, ge=0),
    price_trigger_yen: float = Query(12.0, ge=0),
):
    return plan_demand_response(
        region=region,
        horizon_hours=horizon_hours,
        curtail_pct=curtail_pct,
        incentive_yen_per_kwh=incentive_yen_per_kwh,
        price_trigger_yen=price_trigger_yen,
    )


@router.get("/optimize/market")
def market_optimize(
    region: str = Query("tokyo"),
    market: str = Query("jepx_spot"),
    horizon_hours: int = Query(24, ge=1, le=72),
    battery_mwh: float = Query(40.0, ge=0),
    max_power_mw: float = Query(10.0, gt=0),
    use_ai: bool = Query(True, description="Railway OPENAI_API_KEY で AI 戦略を生成"),
):
    """太陽光・風力変動 / 需給 / 価格を一体最適化し、市場取引計画を返す。"""
    return optimize_energy_market(
        region=region,
        market=market,
        horizon_hours=horizon_hours,
        battery_mwh=battery_mwh,
        max_power_mw=max_power_mw,
        use_ai=use_ai,
    )
