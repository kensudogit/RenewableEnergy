from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.config import get_settings
from src.trading import store
from src.trading.engine import evaluate_cycle, execute_cycle
from src.trading.risk import readiness_report
from src.trading.scheduler import scheduler_status, start_scheduler, stop_scheduler

router = APIRouter(prefix="/api/autotrade", tags=["autotrade"])


class ConfigPatch(BaseModel):
    enabled: Optional[bool] = None
    mode: Optional[Literal["paper", "live"]] = None
    market: Optional[str] = None
    region: Optional[str] = None
    max_order_mw: Optional[float] = Field(None, gt=0)
    max_position_mw: Optional[float] = Field(None, gt=0)
    max_daily_trades: Optional[int] = Field(None, ge=1)
    max_daily_notional_jpy: Optional[float] = Field(None, gt=0)
    min_trade_mw: Optional[float] = Field(None, gt=0)
    cooldown_seconds: Optional[int] = Field(None, ge=0)
    scheduler_enabled: Optional[bool] = None
    scheduler_interval_sec: Optional[int] = Field(None, ge=30)
    use_ai: Optional[bool] = None


@router.get("/config")
def get_config():
    settings = get_settings()
    cfg = store.get_config().to_dict()
    return {
        "config": cfg,
        "live_trading_allowed": settings.live_trading_allowed,
        "broker_configured": bool(settings.broker_api_url and settings.broker_api_key),
    }


@router.put("/config")
def put_config(patch: ConfigPatch):
    settings = get_settings()
    data = patch.model_dump(exclude_none=True)
    if data.get("mode") == "live" and not settings.live_trading_allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                "Live mode unavailable. Set BROKER_API_URL, BROKER_API_KEY, and "
                "LIVE_TRADING_CONFIRM=I_UNDERSTAND_LIVE_RISK in Railway Variables."
            ),
        )
    cfg = store.update_config(data)
    return {"config": cfg.to_dict(), "live_trading_allowed": settings.live_trading_allowed}


@router.get("/status")
def status():
    cfg = store.get_config()
    settings = get_settings()
    return {
        "config": cfg.to_dict(),
        "scheduler": scheduler_status(),
        "position": store.get_position(cfg.market).to_dict(),
        "positions": store.list_positions(),
        "recent_orders": store.list_orders(20),
        "recent_runs": store.list_runs(15),
        "daily": store.daily_stats(),
        "live_trading_allowed": settings.live_trading_allowed,
    }


@router.post("/evaluate")
def evaluate():
    return evaluate_cycle(trigger="evaluate", dry_run=True)


@router.post("/run")
def run():
    return execute_cycle(trigger="manual")


@router.post("/scheduler/start")
async def sched_start():
    cfg = store.get_config()
    if not cfg.enabled:
        store.update_config({"enabled": True})
    return start_scheduler()


@router.post("/scheduler/stop")
async def sched_stop():
    return stop_scheduler()


@router.get("/orders")
def orders(limit: int = 50):
    return {"orders": store.list_orders(limit)}


@router.get("/positions")
def positions():
    return {"positions": store.list_positions()}


@router.get("/runs")
def runs(limit: int = 30):
    return {"runs": store.list_runs(limit)}


@router.get("/readiness")
def readiness():
    return readiness_report()
