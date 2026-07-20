from src.services.demand import forecast_demand
from src.services.dr import plan_demand_response
from src.services.fuel_price import forecast_fuel_price
from src.services.generation import forecast_generation
from src.services.market_price import forecast_market_price
from src.services.optimize import optimize_battery_dispatch
from src.services.revenue import simulate_revenue
from src.services.risk import analyze_risk
from src.services.vpp import aggregate_vpp


def test_generation_forecast_shape():
    out = forecast_generation(horizon_hours=24)
    assert out["module"] == "generation"
    assert len(out["forecast"]) == 24
    assert out["model"].startswith("weather_")


def test_all_modules_run():
    assert forecast_demand(horizon_hours=12)["forecast"]
    assert forecast_market_price(horizon_hours=12)["forecast"]
    assert forecast_fuel_price(horizon_hours=12)["forecast"]
    assert "risk_score" in analyze_risk()["metrics"]
    assert "total_revenue_jpy" in simulate_revenue(horizon_hours=12)["summary"]


def test_optimize_vpp_dr():
    opt = optimize_battery_dispatch(horizon_hours=24)
    assert opt["summary"]["total_net_revenue_jpy"] is not None
    assert len(opt["series"]) == 24
    vpp = aggregate_vpp(horizon_hours=12)
    assert vpp["summary"]["peak_flexible_mw"] >= 0
    dr = plan_demand_response(horizon_hours=12)
    assert "event_count" in dr["summary"]


def test_energy_market_optimize():
    from src.services.market_engine import optimize_energy_market

    out = optimize_energy_market(horizon_hours=12, use_ai=False)
    assert out["module"] == "energy_market_optimize"
    assert "solar_volatility" in out["pillars"]
    assert "wind_volatility" in out["pillars"]
    assert "supply_demand_balance_rmse_mw" in out["pillars"]
    assert "price_volatility" in out["pillars"]
    assert len(out["trades"]) == 12
    assert len(out["series"]) == 12
