from fastapi import APIRouter, Query

from src.ai.brief import market_brief
from src.services.revenue import simulate_revenue
from src.services.risk import analyze_risk

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/risk")
def risk(
    asset_code: str = Query("solar_tokyo_1"),
    market: str = Query("jepx_spot"),
    confidence: float = Query(0.95, ge=0.8, le=0.99),
):
    return analyze_risk(asset_code=asset_code, market=market, confidence=confidence)


@router.get("/simulate/revenue")
def revenue(
    asset_code: str = Query("solar_tokyo_1"),
    market: str = Query("jepx_spot"),
    region: str = Query("tokyo"),
    horizon_hours: int = Query(48, ge=1, le=168),
    battery_mwh: float = Query(20.0, ge=0),
    fit_share: float = Query(0.3, ge=0, le=1),
    fit_price_yen: float = Query(10.0, ge=0),
):
    return simulate_revenue(
        asset_code=asset_code,
        market=market,
        region=region,
        horizon_hours=horizon_hours,
        battery_mwh=battery_mwh,
        fit_share=fit_share,
        fit_price_yen=fit_price_yen,
    )


@router.get("/ai/brief")
def brief(
    region: str = Query("tokyo"),
    asset_code: str = Query("solar_tokyo_1"),
):
    return market_brief(region=region, asset_code=asset_code)
