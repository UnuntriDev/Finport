"""Tests for shared models, enums, and request validation."""
from __future__ import annotations

from datetime import date

import pytest

from models import (
    MonteCarloMethod,
    PortfolioAnalysisRequest,
    ValidationError,
    validate_request,
)


def _make_request(**overrides) -> PortfolioAnalysisRequest:
    defaults: dict = {
        "tickers": ["AAPL", "MSFT"],
        "weights_pct": {"AAPL": 50.0, "MSFT": 50.0},
        "start_date": date(2023, 1, 1),
        "end_date": date(2023, 12, 31),
        "initial_investment": 10_000.0,
        "risk_free_rate": 0.02,
        "mc_horizon_days": 252,
        "mc_simulations": 1000,
        "mc_method_label": MonteCarloMethod.PARAMETRIC.value,
    }
    defaults.update(overrides)
    return PortfolioAnalysisRequest(**defaults)


def test_monte_carlo_method_from_label_roundtrip():
    assert MonteCarloMethod.from_label("Parametric normal") is MonteCarloMethod.PARAMETRIC
    assert MonteCarloMethod.from_label("Historical bootstrap") is MonteCarloMethod.BOOTSTRAP


def test_monte_carlo_method_from_label_unknown_defaults_to_parametric():
    assert MonteCarloMethod.from_label("nonsense") is MonteCarloMethod.PARAMETRIC


def test_monte_carlo_method_key_maps_to_engine_identifier():
    assert MonteCarloMethod.PARAMETRIC.key == "parametric"
    assert MonteCarloMethod.BOOTSTRAP.key == "bootstrap"


def test_request_mc_method_property_uses_enum():
    request = _make_request(mc_method_label="Historical bootstrap")
    assert request.mc_method is MonteCarloMethod.BOOTSTRAP


def test_validate_request_accepts_valid_input():
    validate_request(_make_request())


def test_validate_request_rejects_missing_dates():
    with pytest.raises(ValidationError, match="start and end date"):
        validate_request(_make_request(start_date=None))


def test_validate_request_rejects_zero_investment():
    with pytest.raises(ValidationError, match="initial investment"):
        validate_request(_make_request(initial_investment=0.0))


def test_validate_request_rejects_reversed_dates():
    with pytest.raises(ValidationError, match="earlier than end"):
        validate_request(_make_request(
            start_date=date(2024, 12, 31),
            end_date=date(2024, 1, 1),
        ))


def test_validate_request_rejects_short_period():
    with pytest.raises(ValidationError, match="at least"):
        validate_request(_make_request(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 15),
        ))


def test_validate_request_rejects_single_ticker():
    with pytest.raises(ValidationError, match="at least two tickers"):
        validate_request(_make_request(tickers=["AAPL"]))
