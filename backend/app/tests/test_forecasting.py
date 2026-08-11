"""Forecasting tests — hand-checkable toy case + sanity bounds on full scenario."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from app.core.forecasting.engine import (
    HORIZON_WEEKS,
    MODEL_TIMEOUT_S,
    _backtest_weights,
    _seasonal_naive_forecast,
    forecast_sku,
    fit_lightgbm_forecast,
    fit_prophet_forecast,
    fit_sarima_forecast,
)
from app.data.generator import ScenarioConfig, generate_scenario


def _constant_series(level: float = 100.0, n: int = 104) -> pd.DataFrame:
    """Hand-checkable: every week is exactly `level` — forecast must stay ~level."""
    start = date(2024, 1, 1)
    weeks = [start + timedelta(weeks=i) for i in range(n)]
    return pd.DataFrame({"week_start": weeks, "quantity": np.full(n, level)})


def _synthetic_seasonal_series(
    n: int = 104,
    base: float = 100.0,
    amplitude: float = 20.0,
    trend: float = 0.05,
    noise_std: float = 2.0,
    seed: int = 0,
) -> pd.DataFrame:
    """Low-noise seasonal series for secondary checks."""
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    y = (
        base * ((1 + trend) ** (t / 52.0))
        + amplitude * np.sin(2 * np.pi * t / 52.0)
        + rng.normal(0, noise_std, size=n)
    )
    start = date(2024, 1, 1)
    weeks = [start + timedelta(weeks=i) for i in range(n)]
    return pd.DataFrame({"week_start": weeks, "quantity": np.maximum(y, 1.0)})


def test_toy_case_constant_level_hand_checkable():
    """
    Hand-verifiable toy case: y_t = 100 for 104 weeks.

    Any competent forecast of the next 12 weeks must average ≈ 100.
    Tolerance ±5% (95–105) — tight enough to catch broken models, wide enough
    for mild model noise on a flat series.
    """
    level = 100.0
    hist = _constant_series(level=level)
    weights = {"sarima": 0.4, "prophet": 0.3, "lightgbm": 0.3}
    result = forecast_sku(
        "TOY-CONST",
        hist,
        horizon=HORIZON_WEEKS,
        seed=0,
        weights=weights,
        timeout_s=MODEL_TIMEOUT_S,
    )

    assert len(result.forecast) == HORIZON_WEEKS
    fc_mean = float(result.forecast["forecast"].mean())
    assert 95.0 <= fc_mean <= 105.0, f"expected ~100, got {fc_mean}"
    assert (result.forecast["lower_ci"] <= result.forecast["forecast"]).all()
    assert (result.forecast["forecast"] <= result.forecast["upper_ci"]).all()
    assert abs(sum(result.weights.values()) - 1.0) < 1e-6
    assert result.metrics["mape"] < 0.1  # flat series → tiny error
    assert "model_timeout_s" in result.meta


def test_seasonal_naive_fallback_known_cycle():
    """Seasonal-naive of a pure 52-week cycle must reproduce the next cycle exactly."""
    cycle = np.arange(1, 53, dtype=float)  # 1..52
    y = pd.Series(np.tile(cycle, 2))  # two full years
    mean, lower, upper = _seasonal_naive_forecast(y, horizon=12)
    np.testing.assert_allclose(mean, cycle[:12], rtol=0, atol=1e-9)
    assert (lower <= mean).all() and (mean <= upper).all()


def test_sarima_positive_on_trending_series():
    hist = _synthetic_seasonal_series(noise_std=1.0)
    mean, lower, upper = fit_sarima_forecast(hist["quantity"], horizon=8)
    assert len(mean) == 8
    assert (mean >= 0).all()
    assert (lower <= upper).all()


def test_prophet_runs_and_positive():
    hist = _synthetic_seasonal_series(noise_std=1.0)
    mean, lower, upper = fit_prophet_forecast(
        hist["quantity"], hist["week_start"], horizon=8
    )
    assert mean.shape == (8,)
    assert (mean >= 0).all()
    assert (lower <= upper).all()


def test_lightgbm_recursive_horizon_length():
    hist = _synthetic_seasonal_series()
    mean, lower, upper = fit_lightgbm_forecast(hist["quantity"], horizon=12, seed=1)
    assert mean.shape == (12,)
    assert (mean >= 0).all()


def test_full_scenario_single_sku_sanity():
    """Sanity bounds on one SKU from the fixed synthetic scenario."""
    scenario = generate_scenario(ScenarioConfig(seed=42))
    sku_id = "SKU-001"
    hist = scenario["demand_history"].loc[
        scenario["demand_history"]["sku_id"] == sku_id, ["week_start", "quantity"]
    ]
    weights = {"sarima": 1 / 3, "prophet": 1 / 3, "lightgbm": 1 / 3}
    result = forecast_sku(sku_id, hist, weights=weights, seed=42)

    assert len(result.forecast) == HORIZON_WEEKS
    assert (result.forecast["forecast"] > 0).all()
    assert result.metrics["rmse"] > 0
    assert 0 < result.metrics["mape"] < 2.0


def test_backtest_weights_sum_to_one():
    hist = _synthetic_seasonal_series()
    w = _backtest_weights(hist["quantity"], hist["week_start"], n_origins=2, horizon=4)
    assert set(w) == {"sarima", "prophet", "lightgbm"}
    assert abs(sum(w.values()) - 1.0) < 1e-6


def test_too_short_history_raises():
    hist = _constant_series(n=20)
    with pytest.raises(ValueError):
        forecast_sku("SHORT", hist, weights={"sarima": 1, "prophet": 0, "lightgbm": 0})
