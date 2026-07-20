"""Built-in live sandbox venue — raises practical readiness without external JEPX."""
from __future__ import annotations

import random
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from src.config import get_settings
from src.trading.models import OrderIntent, OrderRecord, utcnow
from src.trading import store

router = APIRouter(prefix="/api/broker/sandbox", tags=["broker-sandbox"])


class SandboxOrderRequest(BaseModel):
    account_id: str = "default"
    client_order_id: str
    market: str = "jepx_spot"
    side: str
    volume_mw: float = Field(gt=0)
    limit_price_yen_per_kwh: float = Field(gt=0)
    delivery_ts: str | None = None
    rationale: str = ""


def _simulate_fill(
    *,
    side: str,
    volume_mw: float,
    limit_price: float,
    seed_key: str,
) -> dict[str, Any]:
    rng = random.Random(hash(seed_key) % (2**32))
    if rng.random() < 0.05:
        return {"status": "rejected", "reason": "sandbox_liquidity_reject"}
    fill_ratio = 1.0 if rng.random() > 0.15 else rng.uniform(0.6, 0.95)
    fill_vol = round(float(volume_mw) * fill_ratio, 4)
    slip = rng.uniform(0.005, 0.04) * (1 if side == "buy" else -1)
    fill_px = round(max(0.01, float(limit_price) + slip), 4)
    return {
        "status": "filled",
        "fill_price_yen": fill_px,
        "fill_volume_mw": fill_vol,
        "fill_ratio": round(fill_ratio, 3),
        "slippage_yen": round(slip, 4),
    }


class SandboxBroker:
    """In-process live sandbox with partial-fill / reject simulation."""

    name = "live_sandbox"

    def place(self, intent: OrderIntent, mode: str = "live") -> OrderRecord:
        settings = get_settings()
        client_id = OrderRecord.new_id()
        sim = _simulate_fill(
            side=intent.side,
            volume_mw=float(intent.volume_mw),
            limit_price=float(intent.limit_price_yen),
            seed_key=f"{intent.delivery_ts}:{intent.side}:{intent.volume_mw}",
        )
        if sim["status"] == "rejected":
            order = OrderRecord(
                client_order_id=client_id,
                mode="live",
                market=intent.market,
                side=intent.side,
                volume_mw=float(intent.volume_mw),
                limit_price_yen=float(intent.limit_price_yen),
                status="rejected",
                rationale=intent.rationale,
                delivery_ts=intent.delivery_ts,
                raw={"venue": "live_sandbox", "reason": sim.get("reason")},
            )
            store.add_order(order)
            store.add_audit("sandbox_reject", {"client_order_id": client_id})
            return order

        fill_vol = float(sim["fill_volume_mw"])
        fill_px = float(sim["fill_price_yen"])
        order = OrderRecord(
            client_order_id=client_id,
            mode="live",
            market=intent.market,
            side=intent.side,
            volume_mw=float(intent.volume_mw),
            limit_price_yen=float(intent.limit_price_yen),
            status="filled",
            broker_order_id=f"SBX-{client_id[-10:]}",
            fill_price_yen=fill_px,
            fill_volume_mw=fill_vol,
            notional_jpy=round(fill_px * fill_vol * 1000.0, 2),
            rationale=intent.rationale,
            delivery_ts=intent.delivery_ts,
            filled_at=utcnow().isoformat(),
            raw={
                "venue": "live_sandbox",
                "account": settings.broker_account_id or "sandbox",
                "fill_ratio": sim["fill_ratio"],
                "slippage_yen": sim["slippage_yen"],
            },
        )
        store.add_order(order)
        store.apply_fill(order)
        store.add_audit(
            "sandbox_fill",
            {
                "client_order_id": client_id,
                "broker_order_id": order.broker_order_id,
                "fill_mw": fill_vol,
                "fill_px": fill_px,
            },
        )
        return order


@router.post("/orders")
def sandbox_orders(
    body: SandboxOrderRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """HTTP facade matching LiveGatewayBroker contract (no local store write)."""
    settings = get_settings()
    expected = settings.broker_api_key or "sandbox-key"
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Invalid sandbox bearer token")
    if body.side not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="side must be buy|sell")

    sim = _simulate_fill(
        side=body.side,
        volume_mw=body.volume_mw,
        limit_price=body.limit_price_yen_per_kwh,
        seed_key=body.client_order_id,
    )
    if sim["status"] == "rejected":
        return {
            "broker_order_id": f"SBX-R-{body.client_order_id[-8:]}",
            "status": "rejected",
            "venue": "live_sandbox",
            "reason": sim.get("reason"),
        }
    return {
        "broker_order_id": f"SBX-{body.client_order_id[-10:]}",
        "status": "filled",
        "fill_price_yen": sim["fill_price_yen"],
        "fill_volume_mw": sim["fill_volume_mw"],
        "client_order_id": body.client_order_id,
        "venue": "live_sandbox",
    }
