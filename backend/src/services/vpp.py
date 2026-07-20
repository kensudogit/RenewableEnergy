"""Virtual Power Plant aggregation across renewable + battery assets."""
from __future__ import annotations

from typing import Any

import numpy as np

from src.services.generation import ASSET_META, forecast_generation
from src.services.optimize import optimize_battery_dispatch


DEFAULT_PORTFOLIO = ["solar_tokyo_1", "wind_kyushu_1", "battery_tokyo_1"]


def aggregate_vpp(
    asset_codes: list[str] | None = None,
    region: str = "tokyo",
    horizon_hours: int = 24,
    battery_mwh: float = 20.0,
) -> dict[str, Any]:
    codes = asset_codes or DEFAULT_PORTFOLIO
    gen_assets = [c for c in codes if ASSET_META.get(c, {}).get("asset_type") != "battery"]
    has_battery = any(ASSET_META.get(c, {}).get("asset_type") == "battery" for c in codes)

    series_by_asset: dict[str, list[dict]] = {}
    stacked = None
    timestamps: list[str] = []

    for code in gen_assets:
        out = forecast_generation(asset_code=code, horizon_hours=horizon_hours)
        series_by_asset[code] = out["forecast"]
        vals = np.array([r["value"] for r in out["forecast"]], dtype=float)
        stacked = vals if stacked is None else stacked + vals
        if not timestamps:
            timestamps = [r["ts"] for r in out["forecast"]]

    if stacked is None:
        stacked = np.zeros(horizon_hours)
        timestamps = [f"t+{i}" for i in range(horizon_hours)]

    batt = None
    if has_battery:
        # Optimize against first generating asset as anchor
        anchor = gen_assets[0] if gen_assets else "solar_tokyo_1"
        batt = optimize_battery_dispatch(
            asset_code=anchor,
            horizon_hours=horizon_hours,
            battery_mwh=battery_mwh,
        )
        batt_mw = np.array([r["battery_mw"] for r in batt["series"]], dtype=float)
        flexible = stacked + batt_mw
    else:
        batt_mw = np.zeros_like(stacked)
        flexible = stacked

    rows = []
    for i in range(len(stacked)):
        rows.append(
            {
                "ts": timestamps[i],
                "generation_mw": round(float(stacked[i]), 3),
                "battery_mw": round(float(batt_mw[i]), 3),
                "flexible_mw": round(float(flexible[i]), 3),
                "assets": {
                    code: round(float(series_by_asset[code][i]["value"]), 3)
                    for code in series_by_asset
                },
            }
        )

    return {
        "module": "vpp",
        "region": region,
        "assets": codes,
        "summary": {
            "peak_flexible_mw": round(float(np.max(flexible)), 3),
            "avg_flexible_mw": round(float(np.mean(flexible)), 3),
            "avg_generation_mw": round(float(np.mean(stacked)), 3),
            "flexibility_mw": round(float(np.mean(np.abs(batt_mw))), 3),
            "battery_net_revenue_jpy": (batt or {}).get("summary", {}).get(
                "total_net_revenue_jpy"
            ),
        },
        "series": rows,
        "battery_optimize": batt["summary"] if batt else None,
    }
