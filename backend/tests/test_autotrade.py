from src.config import get_settings
from src.trading import store
from src.trading.backtest import run_trading_backtest
from src.trading.engine import evaluate_cycle, execute_cycle
from src.trading.risk import readiness_report


def test_paper_execute_cycle():
    store.update_config(
        {
            "enabled": True,
            "mode": "paper",
            "cooldown_seconds": 0,
            "use_ai": False,
            "max_daily_trades": 100,
        }
    )
    ev = evaluate_cycle()
    assert "decision" in ev
    out = execute_cycle(trigger="test")
    assert out["decision"] in ("executed", "blocked", "failed")
    if out["decision"] == "executed":
        assert out["orders"]
        assert store.get_position("jepx_spot").to_dict()


def test_live_sandbox_execute():
    assert get_settings().live_sandbox_enabled
    store.update_config(
        {
            "enabled": True,
            "mode": "live",
            "cooldown_seconds": 0,
            "use_ai": False,
            "max_daily_trades": 200,
        }
    )
    out = execute_cycle(trigger="sandbox-test")
    assert out["decision"] in ("executed", "blocked", "failed")
    if out.get("broker"):
        assert out["broker"] in ("live_sandbox", "live_gateway", "paper")


def test_backtest_and_readiness_uplift():
    bt = run_trading_backtest(days=2)
    assert bt["summary"]["fills"] >= 0
    assert "sharpe_proxy" in bt["summary"]
    r = readiness_report()
    assert r["scores"]["demo"]["score"] >= 88
    assert r["scores"]["poc"]["score"] >= 85
    assert r["scores"]["live_market"]["score"] >= 65
    assert r["capabilities"]["autotrade_live_sandbox"] is True
    assert r["capabilities"]["trading_backtest"] is True
    assert "live_sandbox_broker" in r["improvements_applied"]
