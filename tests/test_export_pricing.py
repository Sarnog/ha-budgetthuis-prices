"""Unittests voor de terugleverprijs: saldering en de ZonneBonus."""

from __future__ import annotations

from datetime import datetime, time, timedelta

import pytest

from custom_components.budgetthuis.export_pricing import (
    Location,
    bonus_window,
    calculate_export_price,
)
from custom_components.budgetthuis.parser import AMSTERDAM, HourPrice

DE_BILT = Location(latitude=52.1, longitude=5.18)
CONTRACT_PRICE = 0.42


def _hour(start: datetime, commodity_net: float | None) -> HourPrice:
    return HourPrice(
        start=start,
        end=start + timedelta(hours=1),
        price=0.9999,  # de siteprijs: bewust anders, mag niet meetellen
        commodity_net=commodity_net,
        energy_tax_net=0.09161,
    )


def _local(year: int, month: int, day: int, hour: int) -> datetime:
    return datetime(year, month, day, hour, tzinfo=AMSTERDAM)


@pytest.mark.parametrize(
    ("month", "expected"),
    [(6, (time(5), time(22))), (9, (time(7), time(20)))],
)
def test_bonus_window_matches_the_examples_of_budget_thuis(month, expected) -> None:
    """Budget Thuis noemt juni 05:00-22:00 en september 07:00-20:00."""
    assert bonus_window(DE_BILT, 2027, month) == expected


@pytest.mark.parametrize("contract_price", [CONTRACT_PRICE, None])
def test_saldering_uses_the_contract_price_until_2027(contract_price) -> None:
    hour = _hour(_local(2026, 12, 31, 12), commodity_net=0.10)

    assert calculate_export_price(hour, contract_price, DE_BILT) == contract_price


def test_zonnebonus_adds_30_percent_to_the_beursprijs() -> None:
    """Het voorbeeld van Budget Thuis: beursprijs 0,10 levert 0,13 op."""
    hour = _hour(_local(2027, 6, 15, 12), commodity_net=0.10)

    assert calculate_export_price(hour, CONTRACT_PRICE, DE_BILT) == 0.13


def test_zonnebonus_is_capped_at_a_beursprijs_of_20_cents() -> None:
    hour = _hour(_local(2027, 6, 15, 12), commodity_net=0.30)

    assert calculate_export_price(hour, CONTRACT_PRICE, DE_BILT) == 0.36


@pytest.mark.parametrize("beursprijs", [0.0, -0.02])
def test_no_bonus_at_a_beursprijs_of_zero_or_lower(beursprijs) -> None:
    hour = _hour(_local(2027, 6, 15, 12), commodity_net=beursprijs)

    assert calculate_export_price(hour, CONTRACT_PRICE, DE_BILT) == beursprijs


@pytest.mark.parametrize("start_hour", [4, 22, 23])
def test_no_bonus_outside_the_window(start_hour) -> None:
    """Juni: 04:00-05:00 begint te vroeg, 22:00 en 23:00-24:00 eindigen te laat."""
    hour = _hour(_local(2027, 6, 15, start_hour), commodity_net=0.10)

    assert calculate_export_price(hour, CONTRACT_PRICE, DE_BILT) == 0.10


def test_bonus_applies_to_the_last_hour_inside_the_window() -> None:
    hour = _hour(_local(2027, 6, 15, 21), commodity_net=0.10)

    assert calculate_export_price(hour, CONTRACT_PRICE, DE_BILT) == 0.13


def test_missing_beursprijs_returns_none() -> None:
    hour = _hour(_local(2027, 6, 15, 12), commodity_net=None)

    assert calculate_export_price(hour, CONTRACT_PRICE, DE_BILT) is None
