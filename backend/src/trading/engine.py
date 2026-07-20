from __future__ import annotations

import time
from typing import Any

from src.services.market_engine import optimize_energy_market
from src.trading.brokers import get_broker
from src.trading.models import OrderIntent, RunLog
from src.trading.risk import check_risk_guards
from src.trading import store


def _intents_from_optimize(plan: dict[str, Any], market: str, max_orders: int = 6) -> list[OrderIntent]:
    trades = plan.get("trades") or []
    intents: list[OrderIntent] = []
    for t in trades:
        side = t.get("side")
        if side not in ("buy", "sell"):
            continue
        vol = float(t.get("volume_mw") or 0)
        if vol <= 0:
            continue
        intents.append(
            OrderIntent(
                side=side,
                volume_mw=vol,
                limit_price_yen=float(t.get("limit_price_yen_per_kwh") or 0),
                delivery_ts=t.get("ts"),
                rationale=str(t.get("rationale") or ""),
                market=market,
            )
        )
        if len(intents) >= max_orders:
            break
    return intents


def evaluate_cycle(trigger: str = "evaluate", dry_run: bool = True) -> dict[str, Any]:
    cfg = store.get_config()
    plan = optimize_energy_market(
        region=cfg.region,
        market=cfg.market,
        horizon_hours=24,
        use_ai=False,
    )
    intents = _intents_from_optimize(plan, cfg.market)
    # For dry-run preview, temporarily treat as enabled for guard preview
    preview_cfg = store.get_config()
    preview_cfg.enabled = True
    ok, reason, filtered = check_risk_guards(preview_cfg, intents)

    result = {
        "trigger": trigger,
        "dry_run": dry_run,
        "config": cfg.to_dict(),
        "pillars": plan.get("pillars"),
        "summary": plan.get("summary"),
        "candidate_trades": [i.__dict__ for i in intents],
        "approved_trades": [i.__dict__ for i in filtered],
        "risk_ok": ok,
        "risk_reason": reason,
        "decision": "ready" if ok else "blocked",
    }
    store.add_run(
        RunLog(
            trigger=trigger,
            mode=cfg.mode,
            decision="ready" if ok else "blocked",
            orders_submitted=0,
            message=reason,
            snapshot={
                "approved": len(filtered),
                "candidates": len(intents),
                "pillars": plan.get("pillars"),
            },
        )
    )
    return result


def execute_cycle(trigger: str = "manual") -> dict[str, Any]:
    cfg = store.get_config()
    if not cfg.enabled:
        run = RunLog(
            trigger=trigger,
            mode=cfg.mode,
            decision="disabled",
            message="Set enabled=true in /api/autotrade/config",
        )
        store.add_run(run)
        return {"decision": "disabled", "message": run.message, "orders": []}

    from src.config import get_settings

    settings = get_settings()
    if cfg.mode == "live" and not settings.live_trading_allowed:
        run = RunLog(
            trigger=trigger,
            mode=cfg.mode,
            decision="blocked",
            message="Live mode requires BROKER_API_URL, BROKER_API_KEY, LIVE_TRADING_CONFIRM",
        )
        store.add_run(run)
        return {"decision": "blocked", "message": run.message, "orders": []}

    plan = optimize_energy_market(
        region=cfg.region,
        market=cfg.market,
        horizon_hours=24,
        use_ai=cfg.use_ai,
    )
    intents = _intents_from_optimize(plan, cfg.market)
    ok, reason, filtered = check_risk_guards(cfg, intents)
    if not ok:
        run = RunLog(
            trigger=trigger,
            mode=cfg.mode,
            decision="blocked",
            message=reason,
            snapshot={"candidates": len(intents)},
        )
        store.add_run(run)
        return {
            "decision": "blocked",
            "message": reason,
            "orders": [],
            "pillars": plan.get("pillars"),
        }

    broker = get_broker(cfg.mode)
    placed = []
    for intent in filtered:
        order = broker.place(intent, mode=cfg.mode)
        placed.append(order.to_dict())

    store.set_last_order_ts(time.time())
    filled = sum(1 for o in placed if o["status"] == "filled")
    rejected = sum(1 for o in placed if o["status"] == "rejected")
    decision = "executed" if placed and rejected < len(placed) else ("failed" if placed else "blocked")
    store.add_audit(
        "execute_cycle",
        {
            "trigger": trigger,
            "mode": cfg.mode,
            "broker": broker.name,
            "submitted": len(placed),
            "filled": filled,
            "rejected": rejected,
            "decision": decision,
        },
    )

    run = RunLog(
        trigger=trigger,
        mode=cfg.mode,
        decision=decision,  # type: ignore[arg-type]
        orders_submitted=len(placed),
        message=f"submitted={len(placed)} filled={filled} rejected={rejected}",
        snapshot={
            "pillars": plan.get("pillars"),
            "ai_summary": (plan.get("ai") or {}).get("summary"),
            "order_ids": [o["client_order_id"] for o in placed],
        },
    )
    store.add_run(run)

    return {
        "decision": decision,
        "message": run.message,
        "mode": cfg.mode,
        "broker": broker.name,
        "orders": placed,
        "position": store.get_position(cfg.market).to_dict(),
        "pillars": plan.get("pillars"),
        "ai": plan.get("ai"),
    }
