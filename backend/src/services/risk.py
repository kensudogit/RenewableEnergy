from __future__ import annotations

import math

import numpy as np

from src.services.generation import forecast_generation
from src.services.market_price import forecast_market_price


def analyze_risk(
    asset_code: str = "solar_tokyo_1",
    market: str = "jepx_spot",
    confidence: float = 0.95,
) -> dict:
    gen = forecast_generation(asset_code=asset_code, horizon_hours=48)
    price = forecast_market_price(market=market, horizon_hours=48)

    gen_vals = np.array([r["value"] for r in gen["forecast"]], dtype=float)
    price_vals = np.array([r["value"] for r in price["forecast"]], dtype=float)

    # Hourly revenue proxy: MW * price(JPY/kWh) * 1000 = JPY/h
    revenue = gen_vals * price_vals * 1000.0
    mean_rev = float(np.mean(revenue))
    std_rev = float(np.std(revenue))
    z = 1.645 if confidence >= 0.95 else 1.28
    var = mean_rev - z * std_rev
    cvar = float(np.mean(revenue[revenue <= np.quantile(revenue, 1 - confidence)])) if len(revenue) else var

    # Simple volume risk from generation band width
    bands = np.array([r["p90"] - r["p10"] for r in gen["forecast"]], dtype=float)
    volume_risk = float(np.mean(bands) / max(gen["capacity_mw"], 1e-6))

    price_vol = float(np.std(price_vals) / max(np.mean(price_vals), 1e-6))

    score = min(100.0, max(0.0, 100 - (volume_risk * 40 + price_vol * 40 + abs(min(var, 0)) / max(mean_rev, 1) * 20)))

    return {
        "module": "risk",
        "asset_code": asset_code,
        "market": market,
        "confidence": confidence,
        "metrics": {
            "expected_hourly_revenue_jpy": round(mean_rev, 2),
            "revenue_std_jpy": round(std_rev, 2),
            "var_jpy": round(var, 2),
            "cvar_jpy": round(cvar, 2),
            "volume_risk_index": round(volume_risk, 4),
            "price_volatility": round(price_vol, 4),
            "risk_score": round(score, 1),
        },
        "series": [
            {
                "ts": gen["forecast"][i]["ts"],
                "revenue_jpy": round(float(revenue[i]), 2),
                "generation_mw": round(float(gen_vals[i]), 3),
                "price_yen_per_kwh": round(float(price_vals[i]), 3),
            }
            for i in range(len(revenue))
        ],
        "notes": [
            "VaR/CVaR は発電量×市場価格の時間収益分布から算出した簡易指標です。",
            "実運用では相対契約・インバランスペナルティ・蓄電池制約を追加してください。",
        ],
    }
