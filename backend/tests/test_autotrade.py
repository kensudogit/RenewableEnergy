from src.trading import store
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


def test_readiness_scores_improved():
    r = readiness_report()
    assert r["scores"]["demo"]["score"] >= 80
    assert r["scores"]["poc"]["score"] >= 70
    assert r["scores"]["live_market"]["score"] >= 35
    assert r["capabilities"]["autotrade_paper"] is True
    assert r["capabilities"]["autotrade_live_gateway"] is True
