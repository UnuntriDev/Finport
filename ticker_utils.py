"""Ticker normalization and validation helpers."""

from __future__ import annotations

import re

from constants import TICKER_PATTERN

_TICKER_REGEX = re.compile(TICKER_PATTERN)


def normalize_ticker(raw: object) -> str:
    """Return a validated Yahoo Finance ticker or an empty string."""
    ticker = str(raw).strip().upper()
    if not ticker or not _TICKER_REGEX.fullmatch(ticker):
        return ""
    return ticker
