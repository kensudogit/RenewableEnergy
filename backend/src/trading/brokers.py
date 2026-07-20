"""Broker adapters: paper book and live HTTP gateway (JEPX/OTC connector)."""
from __future__ import annotations

from typing import Any, Protocol

import httpx

from src.config import get_settings
from src.trading.models import OrderIntent, OrderRecord, utcnow
from src.trading import store


class Broker(Protocol):
    name: str

    def place(self, intent: OrderIntent, mode: str) -> OrderRecord: ...


class PaperBroker:
    name = "paper"

    def place(self, intent: OrderIntent, mode: str = "paper") -> OrderRecord:
        # Immediate fill at limit (demo-realistic for spot schedule)
        fill_px = float(intent.limit_price_yen)
        # Tiny slippage model
        slip = 0.01 if intent.side == "buy" else -0.01
        fill_px = max(0.01, fill_px + slip)
        order = OrderRecord(
            client_order_id=OrderRecord.new_id(),
            mode="paper",
            market=intent.market,
            side=intent.side,
            volume_mw=float(intent.volume_mw),
            limit_price_yen=float(intent.limit_price_yen),
            status="filled",
            broker_order_id=f"PAPER-{OrderRecord.new_id()[-8:]}",
            fill_price_yen=round(fill_px, 4),
            fill_volume_mw=float(intent.volume_mw),
            notional_jpy=round(fill_px * float(intent.volume_mw) * 1000.0, 2),
            rationale=intent.rationale,
            delivery_ts=intent.delivery_ts,
            filled_at=utcnow().isoformat(),
            raw={"venue": "paper_book", "slippage_yen": slip},
        )
        store.add_order(order)
        store.apply_fill(order)
        return order


class LiveGatewayBroker:
    """
    Posts orders to an external market gateway.

    Expected gateway contract (configurable via BROKER_API_URL):
      POST {BROKER_API_URL}
      Headers: Authorization: Bearer {BROKER_API_KEY}
      Body: {
        account_id, client_order_id, market, side, volume_mw,
        limit_price_yen_per_kwh, delivery_ts, rationale
      }
      Response 200: { broker_order_id, status, fill_price_yen?, fill_volume_mw? }
    """

    name = "live_gateway"

    def place(self, intent: OrderIntent, mode: str = "live") -> OrderRecord:
        settings = get_settings()
        if not settings.live_trading_allowed:
            order = OrderRecord(
                client_order_id=OrderRecord.new_id(),
                mode="live",
                market=intent.market,
                side=intent.side,
                volume_mw=float(intent.volume_mw),
                limit_price_yen=float(intent.limit_price_yen),
                status="rejected",
                rationale=intent.rationale,
                delivery_ts=intent.delivery_ts,
                raw={
                    "error": (
                        "Live trading blocked. Set BROKER_API_URL, BROKER_API_KEY, "
                        "and LIVE_TRADING_CONFIRM=I_UNDERSTAND_LIVE_RISK"
                    )
                },
            )
            store.add_order(order)
            return order

        client_id = OrderRecord.new_id()
        payload = {
            "account_id": settings.broker_account_id or "default",
            "client_order_id": client_id,
            "market": intent.market,
            "side": intent.side,
            "volume_mw": float(intent.volume_mw),
            "limit_price_yen_per_kwh": float(intent.limit_price_yen),
            "delivery_ts": intent.delivery_ts,
            "rationale": intent.rationale,
        }
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    settings.broker_api_url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {settings.broker_api_key}",
                        "Content-Type": "application/json",
                    },
                )
            data: dict[str, Any]
            try:
                data = resp.json()
            except Exception:  # noqa: BLE001
                data = {"raw_text": resp.text}

            if resp.status_code >= 400:
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
                    raw={"http_status": resp.status_code, "response": data},
                )
                store.add_order(order)
                return order

            status = str(data.get("status", "submitted"))
            if status not in ("submitted", "filled", "rejected", "cancelled"):
                status = "submitted"
            fill_px = data.get("fill_price_yen")
            fill_vol = data.get("fill_volume_mw")
            order = OrderRecord(
                client_order_id=client_id,
                mode="live",
                market=intent.market,
                side=intent.side,
                volume_mw=float(intent.volume_mw),
                limit_price_yen=float(intent.limit_price_yen),
                status=status,  # type: ignore[arg-type]
                broker_order_id=str(data.get("broker_order_id") or data.get("id") or ""),
                fill_price_yen=float(fill_px) if fill_px is not None else None,
                fill_volume_mw=float(fill_vol) if fill_vol is not None else None,
                notional_jpy=(
                    round(float(fill_px) * float(fill_vol or intent.volume_mw) * 1000.0, 2)
                    if fill_px is not None
                    else None
                ),
                rationale=intent.rationale,
                delivery_ts=intent.delivery_ts,
                filled_at=utcnow().isoformat() if status == "filled" else None,
                raw={"response": data},
            )
            store.add_order(order)
            if status == "filled":
                if order.fill_price_yen is None:
                    order.fill_price_yen = order.limit_price_yen
                if order.fill_volume_mw is None:
                    order.fill_volume_mw = order.volume_mw
                if order.notional_jpy is None:
                    order.notional_jpy = round(
                        order.fill_price_yen * order.fill_volume_mw * 1000.0, 2
                    )
                store.apply_fill(order)
            return order
        except Exception as exc:  # noqa: BLE001
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
                raw={"error": str(exc)},
            )
            store.add_order(order)
            return order


def get_broker(mode: str) -> Broker:
    if mode == "live":
        settings = get_settings()
        # Prefer in-process sandbox when enabled and no external URL
        if settings.live_sandbox_enabled and not settings.broker_api_url.strip():
            from src.trading.sandbox import SandboxBroker

            return SandboxBroker()
        if settings.external_live_configured or settings.broker_api_url.strip():
            return LiveGatewayBroker()
        if settings.live_sandbox_enabled:
            from src.trading.sandbox import SandboxBroker

            return SandboxBroker()
        return LiveGatewayBroker()
    return PaperBroker()
