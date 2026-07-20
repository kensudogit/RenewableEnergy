"""Battery dispatch optimization (linear program via scipy.linprog)."""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import linprog

from src.services.generation import forecast_generation
from src.services.market_price import forecast_market_price


def optimize_battery_dispatch(
    asset_code: str = "solar_tokyo_1",
    market: str = "jepx_spot",
    horizon_hours: int = 48,
    battery_mwh: float = 20.0,
    max_power_mw: float = 5.0,
    efficiency: float = 0.92,
    initial_soc: float | None = None,
) -> dict[str, Any]:
    gen = forecast_generation(asset_code=asset_code, horizon_hours=horizon_hours)
    price = forecast_market_price(market=market, horizon_hours=horizon_hours)

    gen_mw = np.array([r["value"] for r in gen["forecast"]], dtype=float)
    spot = np.array([r["value"] for r in price["forecast"]], dtype=float)
    n = len(gen_mw)
    soc0 = battery_mwh * 0.5 if initial_soc is None else float(initial_soc)
    eta = max(min(efficiency, 0.99), 0.5)

    # Decision vars: [charge_0..n-1, discharge_0..n-1, soc_0..n-1]
    # charge/discharge in MWh (1h step), soc in MWh
    c = np.concatenate(
        [
            spot * 1000.0,  # charging cost (buy / opportunity)
            -spot * 1000.0 * eta,  # discharge revenue (eff. adjusted)
            np.zeros(n),
        ]
    )

    bounds = (
        [(0.0, max_power_mw)] * n
        + [(0.0, max_power_mw)] * n
        + [(0.0, battery_mwh)] * n
    )

    # SOC dynamics: soc[t] - soc[t-1] - eta*charge[t] + discharge[t]/eta = 0
    # For t=0: soc[0] - eta*charge[0] + discharge[0]/eta = soc0
    A_eq = []
    b_eq = []
    for t in range(n):
        row = np.zeros(3 * n)
        row[t] = -eta  # charge
        row[n + t] = 1.0 / eta  # discharge removes more energy from SOC when eta applied on discharge side
        row[2 * n + t] = 1.0  # soc[t]
        if t == 0:
            b_eq.append(soc0)
        else:
            row[2 * n + t - 1] = -1.0
            b_eq.append(0.0)
        A_eq.append(row)

    # Optional: cannot charge more than available generation + grid (allow grid for arbitrage)
    # Keep unconstrained buy for market arbitrage demo.

    res = linprog(
        c=c,
        A_eq=np.asarray(A_eq),
        b_eq=np.asarray(b_eq),
        bounds=bounds,
        method="highs",
    )

    if not res.success:
        # Fallback greedy arbitrage (no circular import to revenue)
        median = float(np.median(spot))
        soc = soc0
        charge_f = np.zeros(n)
        discharge_f = np.zeros(n)
        soc_f = np.zeros(n)
        for i in range(n):
            if spot[i] < median * 0.9 and soc < battery_mwh:
                ch = min(max_power_mw, battery_mwh - soc)
                soc += ch * eta
                charge_f[i] = ch
            elif spot[i] > median * 1.1 and soc > 0:
                dh = min(max_power_mw, soc * eta)
                soc -= dh / eta
                discharge_f[i] = dh
            soc_f[i] = soc
        batt_mw = discharge_f - charge_f
        marketable = np.clip(gen_mw + batt_mw, 0, None)
        net = marketable * 1000.0 * spot - charge_f * 1000.0 * spot
        series = [
            {
                "ts": gen["forecast"][i]["ts"],
                "generation_mw": round(float(gen_mw[i]), 3),
                "charge_mw": round(float(charge_f[i]), 3),
                "discharge_mw": round(float(discharge_f[i]), 3),
                "battery_mw": round(float(batt_mw[i]), 3),
                "soc_mwh": round(float(soc_f[i]), 3),
                "spot_yen_per_kwh": round(float(spot[i]), 3),
                "net_revenue_jpy": round(float(net[i]), 2),
            }
            for i in range(n)
        ]
        return {
            "module": "battery_optimize",
            "solver": "greedy_fallback",
            "status": res.message,
            "summary": {
                "total_net_revenue_jpy": round(float(np.sum(net)), 2),
                "avg_hourly_net_jpy": round(float(np.mean(net)), 2),
                "total_charge_mwh": round(float(np.sum(charge_f)), 3),
                "total_discharge_mwh": round(float(np.sum(discharge_f)), 3),
                "final_soc_mwh": round(float(soc_f[-1]), 3),
                "objective_jpy": round(float(np.sum(net)), 2),
            },
            "series": series,
            "params": {
                "asset_code": asset_code,
                "market": market,
                "horizon_hours": horizon_hours,
                "battery_mwh": battery_mwh,
                "max_power_mw": max_power_mw,
                "efficiency": efficiency,
            },
        }

    x = res.x
    charge = x[:n]
    discharge = x[n : 2 * n]
    soc = x[2 * n :]
    batt_mw = discharge - charge
    marketable = np.clip(gen_mw + batt_mw, 0, None)
    revenue = marketable * 1000.0 * spot
    # Net of charging cost when charging from market
    charge_cost = charge * 1000.0 * spot
    net = revenue - charge_cost

    series = []
    for i in range(n):
        series.append(
            {
                "ts": gen["forecast"][i]["ts"],
                "generation_mw": round(float(gen_mw[i]), 3),
                "charge_mw": round(float(charge[i]), 3),
                "discharge_mw": round(float(discharge[i]), 3),
                "battery_mw": round(float(batt_mw[i]), 3),
                "soc_mwh": round(float(soc[i]), 3),
                "spot_yen_per_kwh": round(float(spot[i]), 3),
                "net_revenue_jpy": round(float(net[i]), 2),
            }
        )

    return {
        "module": "battery_optimize",
        "solver": "scipy_highs",
        "status": "optimal",
        "params": {
            "asset_code": asset_code,
            "market": market,
            "horizon_hours": horizon_hours,
            "battery_mwh": battery_mwh,
            "max_power_mw": max_power_mw,
            "efficiency": efficiency,
            "initial_soc_mwh": soc0,
        },
        "summary": {
            "total_net_revenue_jpy": round(float(np.sum(net)), 2),
            "avg_hourly_net_jpy": round(float(np.mean(net)), 2),
            "total_charge_mwh": round(float(np.sum(charge)), 3),
            "total_discharge_mwh": round(float(np.sum(discharge)), 3),
            "final_soc_mwh": round(float(soc[-1]), 3),
            "objective_jpy": round(float(-res.fun), 2),
        },
        "series": series,
    }
