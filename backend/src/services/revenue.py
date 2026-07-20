from __future__ import annotations

from typing import Any

import numpy as np

from src.services.demand import forecast_demand
from src.services.generation import forecast_generation
from src.services.market_price import forecast_market_price


def simulate_revenue(
    asset_code: str = "solar_tokyo_1",
    market: str = "jepx_spot",
    region: str = "tokyo",
    horizon_hours: int = 48,
    battery_mwh: float = 20.0,
    fit_share: float = 0.3,
    fit_price_yen: float = 10.0,
) -> dict[str, Any]:
    gen = forecast_generation(asset_code=asset_code, horizon_hours=horizon_hours)
    price = forecast_market_price(market=market, horizon_hours=horizon_hours)
    demand = forecast_demand(region=region, horizon_hours=horizon_hours)

    gen_mw = np.array([r["value"] for r in gen["forecast"]], dtype=float)
    spot = np.array([r["value"] for r in price["forecast"]], dtype=float)
    dem = np.array([r["value"] for r in demand["forecast"]], dtype=float)

    # Prefer LP battery dispatch; fall back to greedy thresholds
    from src.services.optimize import optimize_battery_dispatch

    opt = optimize_battery_dispatch(
        asset_code=asset_code,
        market=market,
        horizon_hours=horizon_hours,
        battery_mwh=battery_mwh,
    )
    batt_mw = np.array([r["battery_mw"] for r in opt["series"]], dtype=float)

    marketable = np.clip(gen_mw + batt_mw, 0, None)
    fit_mwh = marketable * fit_share
    spot_mwh = marketable * (1 - fit_share)

    fit_rev = fit_mwh * 1000 * fit_price_yen
    spot_rev = spot_mwh * 1000 * spot
    total = fit_rev + spot_rev

    # Demand residual proxy (for VPP / DR narrative)
    residual = dem - (gen_mw * 100)  # scale demo asset into area context

    rows = []
    for i in range(len(gen_mw)):
        rows.append(
            {
                "ts": gen["forecast"][i]["ts"],
                "generation_mw": round(float(gen_mw[i]), 3),
                "battery_mw": round(float(batt_mw[i]), 3),
                "spot_yen_per_kwh": round(float(spot[i]), 3),
                "fit_revenue_jpy": round(float(fit_rev[i]), 2),
                "spot_revenue_jpy": round(float(spot_rev[i]), 2),
                "total_revenue_jpy": round(float(total[i]), 2),
                "area_residual_mw": round(float(residual[i]), 1),
            }
        )

    return {
        "module": "revenue_simulation",
        "params": {
            "asset_code": asset_code,
            "market": market,
            "region": region,
            "horizon_hours": horizon_hours,
            "battery_mwh": battery_mwh,
            "fit_share": fit_share,
            "fit_price_yen": fit_price_yen,
        },
        "summary": {
            "total_revenue_jpy": round(float(np.sum(total)), 2),
            "fit_revenue_jpy": round(float(np.sum(fit_rev)), 2),
            "spot_revenue_jpy": round(float(np.sum(spot_rev)), 2),
            "avg_hourly_revenue_jpy": round(float(np.mean(total)), 2),
            "battery_cycles_proxy": round(float(np.sum(np.abs(batt_mw)) / max(battery_mwh, 1e-6) / 2), 2),
            "optimizer": opt.get("solver"),
            "battery_net_revenue_jpy": opt.get("summary", {}).get("total_net_revenue_jpy"),
        },
        "series": rows,
    }
