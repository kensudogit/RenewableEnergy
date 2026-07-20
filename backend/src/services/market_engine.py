"""
Unified market optimization engine.

Optimizes together:
1. Solar output volatility
2. Wind output volatility
3. Supply–demand balance
4. Electricity price volatility

via IT (forecasts + LP) + AI (OpenAI / Railway OPENAI_API_KEY) + market trading.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import linprog

from src.ai.trading import advise_market_trading
from src.services.demand import forecast_demand
from src.services.generation import forecast_generation
from src.services.market_price import forecast_market_price


def _volatility(values: np.ndarray) -> float:
    mean = float(np.mean(values)) if len(values) else 0.0
    if abs(mean) < 1e-9:
        return float(np.std(values))
    return float(np.std(values) / abs(mean))


def optimize_energy_market(
    region: str = "tokyo",
    market: str = "jepx_spot",
    horizon_hours: int = 24,
    solar_asset: str = "solar_tokyo_1",
    wind_asset: str = "wind_kyushu_1",
    battery_mwh: float = 40.0,
    max_power_mw: float = 10.0,
    efficiency: float = 0.92,
    imbalance_penalty_yen: float = 35.0,
    use_ai: bool = True,
) -> dict[str, Any]:
    solar = forecast_generation(asset_code=solar_asset, horizon_hours=horizon_hours)
    wind = forecast_generation(asset_code=wind_asset, horizon_hours=horizon_hours)
    demand = forecast_demand(region=region, horizon_hours=horizon_hours)
    price = forecast_market_price(market=market, horizon_hours=horizon_hours)

    solar_mw = np.array([r["value"] for r in solar["forecast"]], dtype=float)
    wind_mw = np.array([r["value"] for r in wind["forecast"]], dtype=float)
    gen_mw = solar_mw + wind_mw
    dem_mw = np.array([r["value"] for r in demand["forecast"]], dtype=float)
    spot = np.array([r["value"] for r in price["forecast"]], dtype=float)
    n = len(spot)
    timestamps = [r["ts"] for r in price["forecast"]]

    # Area balance (IT KPI): scale portfolio into area MW for illustration
    area_re = gen_mw * 120.0
    area_residual = dem_mw - area_re

    # Portfolio commitment = smooth schedule (reduces RE volatility impact)
    commitment = np.convolve(gen_mw, np.ones(3) / 3, mode="same")
    if n >= 3:
        commitment[0] = gen_mw[0]
        commitment[-1] = gen_mw[-1]

    eta = max(min(efficiency, 0.99), 0.5)
    soc0 = battery_mwh * 0.5

    # Decision vars per t: charge, discharge, sell, buy, soc, deficit, surplus_dump
    # Energy identity:
    #   gen + discharge + buy = commitment_served + charge + sell + dump
    # We serve commitment via: gen + discharge + buy - charge - sell - dump
    # deficit = max(0, commitment - served) handled as:
    #   gen + discharge + buy - charge - sell = commitment - deficit
    #   => discharge + buy - charge - sell + deficit = commitment - gen
    nc = 6
    c = np.zeros(nc * n)
    for t in range(n):
        c[0 * n + t] = spot[t] * 1000.0  # charge (cost / opportunity)
        c[1 * n + t] = -spot[t] * 1000.0 * eta  # discharge revenue
        c[2 * n + t] = -spot[t] * 1000.0  # market sell
        c[3 * n + t] = spot[t] * 1000.0  # market buy
        c[4 * n + t] = 0.0  # soc
        c[5 * n + t] = imbalance_penalty_yen * 1000.0  # commitment deficit penalty

    bounds = (
        [(0.0, max_power_mw)] * n
        + [(0.0, max_power_mw)] * n
        + [(0.0, float(np.max(gen_mw) + max_power_mw) * 2)] * n  # sell
        + [(0.0, float(np.max(commitment) + max_power_mw) * 2)] * n  # buy
        + [(0.0, battery_mwh)] * n
        + [(0.0, float(np.max(commitment)) * 2)] * n  # deficit
    )

    A_eq: list[np.ndarray] = []
    b_eq: list[float] = []

    for t in range(n):
        # SOC: soc[t] - soc[t-1] - eta*charge + discharge/eta = 0
        row = np.zeros(nc * n)
        row[0 * n + t] = -eta
        row[1 * n + t] = 1.0 / eta
        row[4 * n + t] = 1.0
        if t == 0:
            b_eq.append(soc0)
        else:
            row[4 * n + t - 1] = -1.0
            b_eq.append(0.0)
        A_eq.append(row)

    for t in range(n):
        # Balance vs commitment:
        # discharge + buy - charge - sell + deficit = commitment - gen
        row = np.zeros(nc * n)
        row[1 * n + t] = 1.0
        row[3 * n + t] = 1.0
        row[0 * n + t] = -1.0
        row[2 * n + t] = -1.0
        row[5 * n + t] = 1.0
        A_eq.append(row)
        b_eq.append(float(commitment[t] - gen_mw[t]))

    res = linprog(
        c=c,
        A_eq=np.asarray(A_eq),
        b_eq=np.asarray(b_eq),
        bounds=bounds,
        method="highs",
    )

    if res.success:
        x = res.x
        charge = x[0 * n : 1 * n]
        discharge = x[1 * n : 2 * n]
        sell = x[2 * n : 3 * n]
        buy = x[3 * n : 4 * n]
        soc = x[4 * n : 5 * n]
        deficit = x[5 * n : 6 * n]
        solver = "scipy_highs"
        status = "optimal"
    else:
        charge = np.zeros(n)
        discharge = np.zeros(n)
        sell = np.maximum(gen_mw - commitment, 0)
        buy = np.maximum(commitment - gen_mw, 0)
        deficit = np.zeros(n)
        soc = np.full(n, soc0)
        soc_t = soc0
        median = float(np.median(spot))
        for t in range(n):
            if spot[t] < median * 0.9 and soc_t < battery_mwh and gen_mw[t] > 0:
                ch = min(max_power_mw, battery_mwh - soc_t, gen_mw[t] * 0.3)
                charge[t] = ch
                soc_t += ch * eta
                sell[t] = max(gen_mw[t] - ch - max(commitment[t] - buy[t], 0), 0)
            elif spot[t] > median * 1.1 and soc_t > 0:
                dh = min(max_power_mw, soc_t * eta)
                discharge[t] = dh
                soc_t -= dh / eta
            soc[t] = soc_t
        solver = "greedy_fallback"
        status = res.message

    market_pnl = (sell - buy) * spot * 1000.0
    batt_pnl = discharge * spot * 1000.0 * eta - charge * spot * 1000.0
    penalty = deficit * imbalance_penalty_yen * 1000.0
    net_pnl = market_pnl + batt_pnl - penalty

    # Volatility reduction: commitment tracking vs raw gen
    raw_dev = float(np.std(gen_mw - commitment))
    opt_served = gen_mw + discharge - charge + buy - sell
    opt_dev = float(np.std(opt_served - commitment))

    series = []
    trades = []
    for t in range(n):
        side = "hold"
        volume = 0.0
        if sell[t] > buy[t] + 0.05:
            side = "sell"
            volume = float(sell[t] - buy[t])
        elif buy[t] > sell[t] + 0.05:
            side = "buy"
            volume = float(buy[t] - sell[t])

        series.append(
            {
                "ts": timestamps[t],
                "solar_mw": round(float(solar_mw[t]), 3),
                "wind_mw": round(float(wind_mw[t]), 3),
                "generation_mw": round(float(gen_mw[t]), 3),
                "commitment_mw": round(float(commitment[t]), 3),
                "demand_mw": round(float(dem_mw[t]), 1),
                "area_residual_mw": round(float(area_residual[t]), 1),
                "spot_yen_per_kwh": round(float(spot[t]), 3),
                "charge_mw": round(float(charge[t]), 3),
                "discharge_mw": round(float(discharge[t]), 3),
                "soc_mwh": round(float(soc[t]), 3),
                "sell_mw": round(float(sell[t]), 3),
                "buy_mw": round(float(buy[t]), 3),
                "deficit_mw": round(float(deficit[t]), 3),
                "net_pnl_jpy": round(float(net_pnl[t]), 2),
            }
        )
        trades.append(
            {
                "ts": timestamps[t],
                "market": market,
                "side": side,
                "volume_mw": round(volume, 3),
                "limit_price_yen_per_kwh": round(float(spot[t]), 3),
                "instrument": "day_ahead_spot",
                "rationale": {
                    "sell": "再エネ余剰・高値帯の売却",
                    "buy": "コミットメント不足の市場調達",
                    "hold": "需給均衡・様子見",
                }[side],
            }
        )

    summary = {
        "solar_volatility": round(_volatility(solar_mw), 4),
        "wind_volatility": round(_volatility(wind_mw), 4),
        "price_volatility": round(_volatility(spot), 4),
        "area_balance_rmse_mw": round(float(np.sqrt(np.mean(area_residual**2))), 2),
        "commitment_tracking_raw_std": round(raw_dev, 4),
        "commitment_tracking_opt_std": round(opt_dev, 4),
        "volatility_reduction_pct": round(
            max(0.0, (raw_dev - opt_dev) / raw_dev * 100) if raw_dev > 1e-9 else 0.0,
            2,
        ),
        "total_sell_mwh": round(float(np.sum(sell)), 3),
        "total_buy_mwh": round(float(np.sum(buy)), 3),
        "total_deficit_mwh": round(float(np.sum(deficit)), 3),
        "total_net_pnl_jpy": round(float(np.sum(net_pnl)), 2),
        "battery_cycles_proxy": round(
            float(np.sum(charge) + np.sum(discharge)) / max(battery_mwh, 1e-6) / 2,
            3,
        ),
    }

    ai_context = {
        "region": region,
        "market": market,
        "horizon_hours": horizon_hours,
        "objectives": [
            "太陽光発電の出力変動の緩和",
            "風力発電の発電量変動の緩和",
            "電力需給バランスの最適化",
            "電力価格変動を活用した市場取引",
        ],
        "summary": summary,
        "next_hours": series[: min(8, n)],
        "trade_preview": trades[: min(8, n)],
    }
    ai = advise_market_trading(ai_context) if use_ai else {"skipped": True}

    return {
        "module": "energy_market_optimize",
        "version": "1.0",
        "description": (
            "太陽光・風力の変動、需給バランス、価格変動を "
            "予測・数理最適化・AI・市場取引で一体最適化"
        ),
        "solver": solver,
        "status": status,
        "openai": {
            "configured": bool(ai.get("openai_configured")),
            "model": ai.get("model"),
            "source": "OPENAI_API_KEY (Railway Variables / .env)",
        },
        "inputs": {
            "region": region,
            "market": market,
            "solar_asset": solar_asset,
            "wind_asset": wind_asset,
            "horizon_hours": horizon_hours,
            "battery_mwh": battery_mwh,
            "max_power_mw": max_power_mw,
            "efficiency": efficiency,
            "imbalance_penalty_yen": imbalance_penalty_yen,
        },
        "pillars": {
            "solar_volatility": summary["solar_volatility"],
            "wind_volatility": summary["wind_volatility"],
            "supply_demand_balance_rmse_mw": summary["area_balance_rmse_mw"],
            "price_volatility": summary["price_volatility"],
            "volatility_reduction_pct": summary["volatility_reduction_pct"],
        },
        "summary": summary,
        "series": series,
        "trades": trades,
        "ai": ai,
    }
