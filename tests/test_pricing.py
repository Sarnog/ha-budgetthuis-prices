"""Unit tests for the pure contract-pricing formula.

No Home Assistant dependency, same as test_parser.py.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from custom_components.budgetthuis.parser import HourPrice
from custom_components.budgetthuis.pricing import ContractConfig, calculate_price


def _hour(commodity_net: float | None, energy_tax_net: float | None = 0.09161) -> HourPrice:
    return HourPrice(
        start=datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc),
        end=datetime(2026, 7, 29, 13, 0, tzinfo=timezone.utc),
        price=0.9999,  # the site's own figure - deliberately different, must be ignored
        commodity_net=commodity_net,
        energy_tax_net=energy_tax_net,
    )


def test_calculates_all_in_price_from_beursprijs() -> None:
    config = ContractConfig(inkoopvergoeding=0.01682, vat_percent=21.0)
    price = calculate_price(_hour(0.05), config)

    expected = round((0.05 + 0.01682 + 0.09161) * 1.21, 5)
    assert price == expected


def test_beursprijs_markup_is_added_before_vat() -> None:
    config = ContractConfig(inkoopvergoeding=0.01682, vat_percent=21.0, beursprijs_markup=0.01)
    price = calculate_price(_hour(0.05), config)

    expected = round((0.05 + 0.01 + 0.01682 + 0.09161) * 1.21, 5)
    assert price == expected


def test_zero_vat_returns_bare_subtotal() -> None:
    config = ContractConfig(inkoopvergoeding=0.01, vat_percent=0.0)
    price = calculate_price(_hour(0.02, energy_tax_net=0.10), config)

    assert price == round(0.02 + 0.01 + 0.10, 5)


def test_missing_beursprijs_returns_none() -> None:
    config = ContractConfig(inkoopvergoeding=0.01682, vat_percent=21.0)
    assert calculate_price(_hour(None), config) is None


def test_missing_energiebelasting_returns_none() -> None:
    config = ContractConfig(inkoopvergoeding=0.01682, vat_percent=21.0)
    assert calculate_price(_hour(0.05, energy_tax_net=None), config) is None
