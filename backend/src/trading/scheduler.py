from __future__ import annotations

import asyncio
import logging
from typing import Optional

from src.trading import store
from src.trading.engine import execute_cycle

logger = logging.getLogger("gridleaf.scheduler")

_task: Optional[asyncio.Task] = None
_stop = asyncio.Event()


async def _loop() -> None:
    logger.info("autotrade scheduler started")
    while not _stop.is_set():
        cfg = store.get_config()
        interval = max(30, int(cfg.scheduler_interval_sec or 300))
        if cfg.enabled and cfg.scheduler_enabled:
            try:
                result = await asyncio.to_thread(execute_cycle, "scheduler")
                logger.info("scheduler cycle: %s", result.get("decision"))
            except Exception:  # noqa: BLE001
                logger.exception("scheduler cycle failed")
        try:
            await asyncio.wait_for(_stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
    logger.info("autotrade scheduler stopped")


def start_scheduler() -> dict:
    global _task
    store.update_config({"scheduler_enabled": True})
    if _task is None or _task.done():
        _stop.clear()
        _task = asyncio.create_task(_loop())
    return {"scheduler_enabled": True, "running": True}


def stop_scheduler() -> dict:
    global _task
    store.update_config({"scheduler_enabled": False})
    _stop.set()
    return {"scheduler_enabled": False, "running": bool(_task and not _task.done())}


def scheduler_status() -> dict:
    running = _task is not None and not _task.done()
    cfg = store.get_config()
    return {
        "scheduler_enabled": cfg.scheduler_enabled,
        "running": running,
        "interval_sec": cfg.scheduler_interval_sec,
        "enabled": cfg.enabled,
        "mode": cfg.mode,
    }


async def ensure_scheduler_from_config() -> None:
    """Start background loop if config says so (on app startup)."""
    cfg = store.get_config()
    if cfg.scheduler_enabled and cfg.enabled:
        start_scheduler()
