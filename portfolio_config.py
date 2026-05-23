"""Saved portfolio configuration (JSON) parsing and weight normalization."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from constants import MAX_TICKERS
from ticker_utils import normalize_ticker


@dataclass(frozen=True)
class PortfolioConfig:
    tickers: list[str]
    weights: dict[str, float]
    locks: dict[str, bool]
    start: date | None
    end: date | None


def parse_portfolio_config(raw: bytes | str) -> PortfolioConfig:
    """Parse a saved FinPort config. Raises ValueError on any validation issue."""
    try:
        config = json.loads(raw)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid JSON file: {exc}") from exc

    if not isinstance(config, dict):
        raise ValueError("Config root must be a JSON object.")

    raw_tickers = config.get("tickers", [])
    raw_weights = config.get("weights", {})
    raw_locks = config.get("locks", {})

    if not isinstance(raw_tickers, list) or not raw_tickers:
        raise ValueError("Config has no tickers.")
    if not isinstance(raw_weights, dict) or not isinstance(raw_locks, dict):
        raise ValueError("Config weights/locks must be objects.")

    tickers: list[str] = []
    invalid_tickers: list[str] = []
    for item in raw_tickers:
        ticker = normalize_ticker(item)
        if not ticker:
            invalid_tickers.append(str(item))
            continue
        if ticker not in tickers:
            tickers.append(ticker)
        if len(tickers) >= MAX_TICKERS:
            break

    if invalid_tickers:
        raise ValueError(
            "Config contains invalid ticker symbols: "
            + ", ".join(invalid_tickers[:5])
        )
    if not tickers:
        raise ValueError("Config has no valid tickers.")

    start = _parse_optional_date(config.get("start"), "start")
    end = _parse_optional_date(config.get("end"), "end")
    if start is not None and end is not None and start >= end:
        raise ValueError("Config start date must be earlier than end date.")

    weights = {ticker: _safe_float(raw_weights.get(ticker, 0.0)) for ticker in tickers}
    locks = {ticker: bool(raw_locks.get(ticker, False)) for ticker in tickers}

    return PortfolioConfig(
        tickers=tickers,
        weights=weights,
        locks=locks,
        start=start,
        end=end,
    )


def normalize_weights_to_100(weights: dict[str, float]) -> dict[str, float]:
    """Scale weights to sum to 100%. Falls back to equal-weight when total is zero."""
    if not weights:
        return {}

    cleaned = {ticker: max(0.0, float(value)) for ticker, value in weights.items()}
    total = sum(cleaned.values())
    if total <= 0:
        share = round(100.0 / len(cleaned), 2)
        normalized = {ticker: share for ticker in cleaned}
    else:
        normalized = {
            ticker: round(value * 100.0 / total, 2)
            for ticker, value in cleaned.items()
        }

    diff = round(100.0 - sum(normalized.values()), 2)
    if abs(diff) > 0.001:
        last = next(reversed(normalized))
        normalized[last] = round(normalized[last] + diff, 2)
    return normalized


def _parse_optional_date(value: object, field: str) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"Config {field} date must be an ISO date string.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Config contains invalid {field} date.") from exc


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
