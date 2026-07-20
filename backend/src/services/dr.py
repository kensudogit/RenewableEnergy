"""Demand Response event planner (peak shaving / shift)."""
from __future__ import annotations

from typing import Any

import numpy as np

from src.services.demand import forecast_demand
from src.services.market_price import forecast_market_price
from src.services.vpp import aggregate_vpp


def plan_demand_response(
    region: str = "tokyo",
    horizon_hours: int = 24,
    curtail_pct: float = 0.08,
    incentive_yen_per_kwh: float = 25.0,
    price_trigger_yen: float = 12.0,
) -> dict[str, Any]:
    dem = forecast_demand(region=region, horizon_hours=horizon_hours)
    price = forecast_market_price(horizon_hours=horizon_hours)
    vpp = aggregate_vpp(region=region, horizon_hours=horizon_hours)

    demand = np.array([r["value"] for r in dem["forecast"]], dtype=float)
    spot = np.array([r["value"] for r in price["forecast"]], dtype=float)
    flexible = np.array([r["flexible_mw"] for r in vpp["series"]], dtype=float)

    # Trigger DR when price high or residual tight
    residual = demand - flexible * 50  # scale demo VPP into area MW
    events = []
    shed = np.zeros_like(demand)
    for i in range(len(demand)):
        trigger = spot[i] >= price_trigger_yen or residual[i] > np.percentile(residual, 80)
        if trigger:
            shed[i] = demand[i] * curtail_pct
            events.append(
                {
                    "ts": dem["forecast"][i]["ts"],
                    "type": "peak_shave",
                    "shed_mw": round(float(shed[i]), 2),
                    "spot_yen_per_kwh": round(float(spot[i]), 3),
                    "incentive_jpy": round(float(shed[i] * 1000 * incentive_yen_per_kwh), 2),
                }
            )

    adjusted = demand - shed
    incentive_total = float(np.sum(shed) * 1000 * incentive_yen_per_kwh)
    avoided_peak = float(np.max(demand) - np.max(adjusted)) if len(demand) else 0.0

    series = []
    for i in range(len(demand)):
        series.append(
            {
                "ts": dem["forecast"][i]["ts"],
                "baseline_mw": round(float(demand[i]), 1),
                "adjusted_mw": round(float(adjusted[i]), 1),
                "shed_mw": round(float(shed[i]), 2),
                "spot_yen_per_kwh": round(float(spot[i]), 3),
                "residual_mw": round(float(residual[i]), 1),
            }
        )

    return {
        "module": "demand_response",
        "region": region,
        "params": {
            "horizon_hours": horizon_hours,
            "curtail_pct": curtail_pct,
            "incentive_yen_per_kwh": incentive_yen_per_kwh,
            "price_trigger_yen": price_trigger_yen,
        },
        "summary": {
            "event_count": len(events),
            "total_shed_mwh": round(float(np.sum(shed)), 2),
            "peak_reduction_mw": round(avoided_peak, 2),
            "incentive_cost_jpy": round(incentive_total, 2),
            "max_baseline_mw": round(float(np.max(demand)), 1),
            "max_adjusted_mw": round(float(np.max(adjusted)), 1),
        },
        "events": events,
        "series": series,
    }
