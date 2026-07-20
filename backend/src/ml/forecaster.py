"""Lightweight time-series forecaster (sklearn Ridge + lag features)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error


@dataclass
class ForecastResult:
    history: list[dict]
    forecast: list[dict]
    metrics: dict
    model_name: str = "ridge_lags"


def _build_supervised(values: np.ndarray, lags: int = 24) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for i in range(lags, len(values)):
        X.append(values[i - lags : i])
        y.append(values[i])
    return np.asarray(X), np.asarray(y)


def forecast_series(
    df: pd.DataFrame,
    value_col: str,
    horizon: int = 48,
    lags: int = 24,
) -> ForecastResult:
    values = df[value_col].astype(float).to_numpy()
    if len(values) < lags + 10:
        # Fallback: seasonal naive
        last = values[-1] if len(values) else 0.0
        pattern = values[-24:] if len(values) >= 24 else np.full(24, last)
        preds = [float(pattern[i % len(pattern)]) for i in range(horizon)]
        hist = [
            {"ts": r.ts.isoformat(), "value": float(r[value_col])}
            for r in df.itertuples(index=False)
        ]
        last_ts = pd.Timestamp(df["ts"].iloc[-1])
        fc = [
            {
                "ts": (last_ts + pd.Timedelta(hours=i + 1)).isoformat(),
                "value": preds[i],
                "p10": preds[i] * 0.9,
                "p90": preds[i] * 1.1,
            }
            for i in range(horizon)
        ]
        return ForecastResult(history=hist[-72:], forecast=fc, metrics={"mae": None, "rmse": None}, model_name="seasonal_naive")

    X, y = _build_supervised(values, lags=lags)
    split = max(int(len(X) * 0.8), 1)
    model = Ridge(alpha=1.0)
    model.fit(X[:split], y[:split])
    pred_val = model.predict(X[split:])
    mae = float(mean_absolute_error(y[split:], pred_val)) if len(pred_val) else 0.0
    rmse = float(np.sqrt(mean_squared_error(y[split:], pred_val))) if len(pred_val) else 0.0

    window = values[-lags:].tolist()
    preds: list[float] = []
    for _ in range(horizon):
        x = np.asarray(window[-lags:]).reshape(1, -1)
        p = float(model.predict(x)[0])
        preds.append(p)
        window.append(p)

    hist = [
        {"ts": pd.Timestamp(r.ts).isoformat(), "value": float(getattr(r, value_col))}
        for r in df.itertuples(index=False)
    ]
    last_ts = pd.Timestamp(df["ts"].iloc[-1])
    residual_std = float(np.std(y[split:] - pred_val)) if len(pred_val) else abs(preds[0]) * 0.1
    fc = [
        {
            "ts": (last_ts + pd.Timedelta(hours=i + 1)).isoformat(),
            "value": preds[i],
            "p10": preds[i] - 1.28 * residual_std,
            "p90": preds[i] + 1.28 * residual_std,
        }
        for i in range(horizon)
    ]
    return ForecastResult(
        history=hist[-72:],
        forecast=fc,
        metrics={"mae": round(mae, 4), "rmse": round(rmse, 4)},
        model_name="ridge_lags",
    )
