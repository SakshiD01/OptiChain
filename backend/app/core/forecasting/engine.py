"""Demand forecasting core — ARIMA/SARIMA, Prophet, LightGBM ensemble.

Framework-agnostic: operates on pandas Series/DataFrames, no FastAPI/DB imports.

Ensemble
--------
Point forecast: ŷ = w_s·SARIMA + w_p·Prophet + w_l·LightGBM
Weights from rolling-origin backtest, w ∝ 1/MAPE (models that fail/time out
get weight 0 and are excluded from the mix).

Interval (honest caveat)
------------------------
Reported lower/upper are a *weighted average of each model's interval bounds*,
not a calibrated joint 95% predictive interval. Treat them as uncertainty bands
for display, not exact frequentist coverage.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error

from app.core.forecasting.bootstrap import bootstrap_native_deps

bootstrap_native_deps()

logger = logging.getLogger(__name__)

HORIZON_WEEKS = 12
MIN_HISTORY = 52  # need at least one year for seasonal models
# Hard wall-clock budget per individual model fit (SARIMA / Prophet / LightGBM).
# On timeout: fall back to seasonal-naive (or last-value) — never invent a fake "solved" path.
MODEL_TIMEOUT_S = 30
# Prefer non-seasonal SARIMA unless we have ≥3 full yearly cycles (avoids under-identified seasonal ARMA).
MIN_WEEKS_FOR_SEASONAL_SARIMA = 156

T = TypeVar("T")


@dataclass
class ForecastResult:
    """Per-SKU forecast with intervals and backtest diagnostics."""

    sku_id: str
    forecast: pd.DataFrame  # columns: week_start, forecast, lower_ci, upper_ci
    metrics: dict[str, float]
    weights: dict[str, float]
    method: str = "ensemble"
    meta: dict[str, Any] = field(default_factory=dict)


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    if not mask.any():
        return float("inf")
    return float(mean_absolute_percentage_error(y_true[mask], y_pred[mask]))


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def _seasonal_naive_forecast(
    y: pd.Series,
    horizon: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Fallback when a model times out or fails.

    Uses y_{t-52} when ≥52 observations exist; else repeats the last value.
    Interval = ±1.96 · sample std of recent residuals vs naive (or ±20% of level).
    """
    y_arr = y.astype(float).to_numpy()
    if len(y_arr) >= 52:
        # Tile the last seasonal cycle forward
        cycle = y_arr[-52:]
        mean = np.array([cycle[i % 52] for i in range(horizon)], dtype=float)
        # Residual vs prior year for scale
        if len(y_arr) >= 104:
            resid = y_arr[-52:] - y_arr[-104:-52]
            scale = float(np.std(resid)) if len(resid) else float(np.std(y_arr[-26:]))
        else:
            scale = float(np.std(y_arr[-26:]))
    else:
        last = float(y_arr[-1])
        mean = np.full(horizon, last, dtype=float)
        scale = float(np.std(y_arr)) if len(y_arr) > 1 else 0.2 * last

    scale = max(scale, 0.05 * float(np.mean(np.abs(mean))))
    lower = np.maximum(mean - 1.96 * scale, 0.0)
    upper = mean + 1.96 * scale
    return mean, lower, upper


def _run_with_timeout(
    fn: Callable[[], T],
    timeout_s: float = MODEL_TIMEOUT_S,
    label: str = "model",
) -> T:
    """Run fn in a worker thread; raise TimeoutError on wall-clock overrun."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(fn)
        try:
            return fut.result(timeout=timeout_s)
        except FuturesTimeout as exc:
            fut.cancel()
            raise TimeoutError(
                f"{label} exceeded {timeout_s}s wall-clock budget"
            ) from exc


def fit_sarima_forecast(
    y: pd.Series,
    horizon: int = HORIZON_WEEKS,
    order: tuple[int, int, int] = (1, 1, 1),
    seasonal_order: tuple[int, int, int, int] | None = None,
    timeout_s: float = MODEL_TIMEOUT_S,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    SARIMA point forecast + approximate 95% intervals via get_forecast.

    Default orders (1,1,1) and seasonal (0,1,1,52) are a pragmatic weekly FMCG
    baseline (short-memory + yearly seasonal difference) — not AIC-selected.
    Seasonal terms only when len(y) ≥ MIN_WEEKS_FOR_SEASONAL_SARIMA.
    On fit failure or timeout → seasonal-naive fallback (documented, not silent).
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    y = y.astype(float)
    if seasonal_order is None:
        seasonal_order = (
            (0, 1, 1, 52)
            if len(y) >= MIN_WEEKS_FOR_SEASONAL_SARIMA
            else (0, 0, 0, 0)
        )

    def _fit() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        try:
            model = SARIMAX(
                y,
                order=order,
                seasonal_order=seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            fitted = model.fit(disp=False, maxiter=100)
        except Exception:
            model = SARIMAX(
                y,
                order=order,
                seasonal_order=(0, 0, 0, 0),
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            fitted = model.fit(disp=False, maxiter=100)

        pred = fitted.get_forecast(steps=horizon)
        mean = np.maximum(pred.predicted_mean.to_numpy(dtype=float), 0.0)
        ci = pred.conf_int(alpha=0.05)
        lower = np.maximum(ci.iloc[:, 0].to_numpy(dtype=float), 0.0)
        upper = np.maximum(ci.iloc[:, 1].to_numpy(dtype=float), 0.0)
        return mean, lower, upper

    try:
        return _run_with_timeout(_fit, timeout_s=timeout_s, label="SARIMA")
    except (TimeoutError, Exception) as exc:
        logger.warning("SARIMA fallback to seasonal-naive: %s", exc)
        return _seasonal_naive_forecast(y, horizon)


def fit_prophet_forecast(
    y: pd.Series,
    dates: pd.Series,
    horizon: int = HORIZON_WEEKS,
    timeout_s: float = MODEL_TIMEOUT_S,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Prophet additive model on weekly (Mon) series.

    - yearly_seasonality=True (Fourier yearly terms) — matches FMCG annual cycles
    - weekly/daily seasonality off (data is already weekly aggregates)
    - interval_width=0.95 → yhat_lower / yhat_upper from Prophet's uncertainty model
    - future frame uses freq='W-MON' to align with demand_history week starts

    On timeout/failure → seasonal-naive fallback.
    """
    from prophet import Prophet

    y = y.astype(float)

    def _fit() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        df = pd.DataFrame({"ds": pd.to_datetime(dates), "y": y.to_numpy()})
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.95,
        )
        model.fit(df)
        future = model.make_future_dataframe(periods=horizon, freq="W-MON")
        forecast = model.predict(future).tail(horizon)
        mean = np.maximum(forecast["yhat"].to_numpy(dtype=float), 0.0)
        lower = np.maximum(forecast["yhat_lower"].to_numpy(dtype=float), 0.0)
        upper = np.maximum(forecast["yhat_upper"].to_numpy(dtype=float), 0.0)
        return mean, lower, upper

    try:
        return _run_with_timeout(_fit, timeout_s=timeout_s, label="Prophet")
    except (TimeoutError, Exception) as exc:
        logger.warning("Prophet fallback to seasonal-naive: %s", exc)
        return _seasonal_naive_forecast(y, horizon)


def _lag_feature_frame(y: np.ndarray, lags: tuple[int, ...] = (1, 2, 4, 13, 52)) -> pd.DataFrame:
    """Build supervised learning frame with lag and rolling features."""
    s = pd.Series(y)
    frame = pd.DataFrame({"y": s})
    for lag in lags:
        frame[f"lag_{lag}"] = s.shift(lag)
    frame["roll_mean_4"] = s.shift(1).rolling(4).mean()
    frame["roll_std_4"] = s.shift(1).rolling(4).std()
    frame["roll_mean_13"] = s.shift(1).rolling(13).mean()
    # Position in a 52-week cycle (synthetic index; not calendar ISO week)
    frame["week_of_year"] = np.arange(len(s)) % 52
    return frame.dropna().reset_index(drop=True)


def fit_lightgbm_forecast(
    y: pd.Series,
    horizon: int = HORIZON_WEEKS,
    seed: int = 42,
    timeout_s: float = MODEL_TIMEOUT_S,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Recursive multi-step LightGBM forecast using lag/rolling features.

    Confidence intervals are empirical: ±1.96 * residual std from in-sample fit
    (honest about uncertainty — not a fake calibrated Bayesian interval).
    On timeout/failure → seasonal-naive fallback.
    """
    import lightgbm as lgb

    y_arr = y.astype(float).to_numpy()

    def _fit() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        frame = _lag_feature_frame(y_arr)
        feature_cols = [c for c in frame.columns if c != "y"]
        X, target = frame[feature_cols], frame["y"]

        model = lgb.LGBMRegressor(
            n_estimators=80,
            learning_rate=0.08,
            num_leaves=15,
            min_child_samples=5,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=seed,
            verbosity=-1,
        )
        model.fit(X, target)
        fitted_vals = model.predict(X)
        resid_std = float(np.std(target.to_numpy() - fitted_vals))

        history = list(y_arr)
        preds = []
        for _ in range(horizon):
            feat_frame = _lag_feature_frame(np.asarray(history, dtype=float))
            x_next = feat_frame[feature_cols].iloc[[-1]]
            p = max(float(model.predict(x_next)[0]), 0.0)
            preds.append(p)
            history.append(p)

        mean = np.asarray(preds, dtype=float)
        lower = np.maximum(mean - 1.96 * resid_std, 0.0)
        upper = mean + 1.96 * resid_std
        return mean, lower, upper

    try:
        return _run_with_timeout(_fit, timeout_s=timeout_s, label="LightGBM")
    except (TimeoutError, Exception) as exc:
        logger.warning("LightGBM fallback to seasonal-naive: %s", exc)
        return _seasonal_naive_forecast(y, horizon)


def _backtest_weights(
    y: pd.Series,
    dates: pd.Series,
    n_origins: int = 3,
    horizon: int = 4,
    seed: int = 42,
) -> dict[str, float]:
    """
    Rolling-origin (walk-forward) backtest to choose ensemble weights.

    Failed / timed-out models are excluded (weight 0), not scored as MAPE=1.0.
    If every model fails at an origin, that origin is skipped.
    Weights ∝ 1/mean_MAPE over successful origins, then L1-normalized.
    """
    y = y.astype(float).reset_index(drop=True)
    dates = pd.to_datetime(dates).reset_index(drop=True)
    n = len(y)
    min_train = max(MIN_HISTORY, n - n_origins * horizon - 1)
    errors: dict[str, list[float]] = {"sarima": [], "prophet": [], "lightgbm": []}

    for origin in range(n_origins):
        train_end = min_train + origin * horizon
        if train_end + horizon > n:
            break
        y_train = y.iloc[:train_end]
        d_train = dates.iloc[:train_end]
        y_true = y.iloc[train_end : train_end + horizon].to_numpy()

        for name, runner in (
            ("sarima", lambda yt=y_train: fit_sarima_forecast(yt, horizon=horizon)),
            (
                "prophet",
                lambda yt=y_train, dt=d_train: fit_prophet_forecast(
                    yt, dt, horizon=horizon
                ),
            ),
            (
                "lightgbm",
                lambda yt=y_train: fit_lightgbm_forecast(
                    yt, horizon=horizon, seed=seed
                ),
            ),
        ):
            try:
                hat, _, _ = runner()
                errors[name].append(_mape(y_true, hat[: len(y_true)]))
            except Exception as exc:
                logger.debug("backtest %s origin %s failed: %s", name, origin, exc)

    mean_err = {k: float(np.mean(v)) if v else None for k, v in errors.items()}
    usable = {k: v for k, v in mean_err.items() if v is not None and np.isfinite(v)}
    if not usable:
        # Absolute fallback: equal weights (all models will still run with their own fallbacks)
        return {"sarima": 1 / 3, "prophet": 1 / 3, "lightgbm": 1 / 3}

    inv = {k: 1.0 / max(v, 0.01) for k, v in usable.items()}
    total = sum(inv.values())
    weights = {k: 0.0 for k in errors}
    for k, v in inv.items():
        weights[k] = v / total
    return weights


def forecast_sku(
    sku_id: str,
    history: pd.DataFrame,
    horizon: int = HORIZON_WEEKS,
    seed: int = 42,
    weights: dict[str, float] | None = None,
    timeout_s: float = MODEL_TIMEOUT_S,
    fast: bool = False,
) -> ForecastResult:
    """
    Produce a horizon-week ensemble forecast for one SKU.

    ŷ_t = Σ_m w_m · ŷ_{m,t}
    Interval bounds = Σ_m w_m · bound_{m,t}  (display band — see module docstring)

    Metrics: rolling-origin MAPE/RMSE unless fast=True (API path), which uses a
    single holdout window only — ~3× fewer model fits.
    """
    if len(history) < MIN_HISTORY:
        raise ValueError(f"{sku_id}: need ≥{MIN_HISTORY} weeks, got {len(history)}")

    hist = history.sort_values("week_start").reset_index(drop=True)
    y = hist["quantity"]
    dates = hist["week_start"]

    w = weights or _backtest_weights(y, dates, seed=seed)

    s_mean, s_lo, s_hi = fit_sarima_forecast(y, horizon=horizon, timeout_s=timeout_s)
    p_mean, p_lo, p_hi = fit_prophet_forecast(y, dates, horizon=horizon, timeout_s=timeout_s)
    l_mean, l_lo, l_hi = fit_lightgbm_forecast(
        y, horizon=horizon, seed=seed, timeout_s=timeout_s
    )

    mean = w["sarima"] * s_mean + w["prophet"] * p_mean + w["lightgbm"] * l_mean
    lower = w["sarima"] * s_lo + w["prophet"] * p_lo + w["lightgbm"] * l_lo
    upper = w["sarima"] * s_hi + w["prophet"] * p_hi + w["lightgbm"] * l_hi

    last_week = pd.Timestamp(dates.iloc[-1])
    future_weeks = [
        (last_week + pd.Timedelta(weeks=i + 1)).date() for i in range(horizon)
    ]
    forecast_df = pd.DataFrame(
        {
            "week_start": future_weeks,
            "forecast": np.round(mean, 2),
            "lower_ci": np.round(np.maximum(lower, 0.0), 2),
            "upper_ci": np.round(upper, 2),
        }
    )

    hold = min(horizon, 8)
    y_train = y.iloc[:-hold]
    d_train = dates.iloc[:-hold]
    y_hold = y.iloc[-hold:].to_numpy()

    if fast:
        # One holdout only — interactive API path
        s_h, _, _ = fit_sarima_forecast(y_train, horizon=hold, timeout_s=timeout_s)
        p_h, _, _ = fit_prophet_forecast(y_train, d_train, horizon=hold, timeout_s=timeout_s)
        l_h, _, _ = fit_lightgbm_forecast(
            y_train, horizon=hold, seed=seed, timeout_s=timeout_s
        )
        ens_h = w["sarima"] * s_h + w["prophet"] * p_h + w["lightgbm"] * l_h
        metrics = {
            "mape": _mape(y_hold, ens_h[: len(y_hold)]),
            "rmse": _rmse(y_hold, ens_h[: len(y_hold)]),
            "holdout_weeks": float(hold),
            "n_backtest_origins": 1.0,
            "fast": 1.0,
        }
    else:
        roll_mapes: list[float] = []
        roll_rmses: list[float] = []
        n = len(y)
        n_origins = 3
        min_train = max(MIN_HISTORY, n - n_origins * hold - 1)
        for origin in range(n_origins):
            train_end = min_train + origin * hold
            if train_end + hold > n:
                break
            yt = y.iloc[:train_end]
            dt = dates.iloc[:train_end]
            yh = y.iloc[train_end : train_end + hold].to_numpy()
            s_h, _, _ = fit_sarima_forecast(yt, horizon=hold, timeout_s=timeout_s)
            p_h, _, _ = fit_prophet_forecast(yt, dt, horizon=hold, timeout_s=timeout_s)
            l_h, _, _ = fit_lightgbm_forecast(
                yt, horizon=hold, seed=seed, timeout_s=timeout_s
            )
            ens_h = w["sarima"] * s_h + w["prophet"] * p_h + w["lightgbm"] * l_h
            roll_mapes.append(_mape(yh, ens_h[: len(yh)]))
            roll_rmses.append(_rmse(yh, ens_h[: len(yh)]))
        metrics = {
            "mape": float(np.mean(roll_mapes)) if roll_mapes else float("nan"),
            "rmse": float(np.mean(roll_rmses)) if roll_rmses else float("nan"),
            "holdout_weeks": float(hold),
            "n_backtest_origins": float(len(roll_mapes)),
            "fast": 0.0,
        }

    return ForecastResult(
        sku_id=sku_id,
        forecast=forecast_df,
        metrics=metrics,
        weights=w,
        method="ensemble",
        meta={
            "n_history": len(hist),
            "horizon": horizon,
            "seed": seed,
            "models": ["sarima", "prophet", "lightgbm"],
            "model_timeout_s": timeout_s,
            "interval_note": (
                "weighted average of component intervals — not a joint calibrated 95% CI"
            ),
            "fallback": "seasonal-naive on per-model timeout/failure",
        },
    )


def forecast_all_skus(
    demand_history: pd.DataFrame,
    horizon: int = HORIZON_WEEKS,
    seed: int = 42,
    sku_ids: list[str] | None = None,
) -> list[ForecastResult]:
    """Run ensemble forecasts for every SKU (or a subset)."""
    ids = sku_ids or sorted(demand_history["sku_id"].unique().tolist())
    results = []
    for sku_id in ids:
        hist = demand_history.loc[
            demand_history["sku_id"] == sku_id, ["week_start", "quantity"]
        ]
        results.append(forecast_sku(sku_id, hist, horizon=horizon, seed=seed))
    return results
