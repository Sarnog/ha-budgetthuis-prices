"""Unittests voor de terugleverprijs: saldering en de ZonneBonus."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pytest

from custom_components.budgetthuis.export_pricing import (
    ExportConfig,
    Location,
    bonus_window,
    calculate_export_price,
)
from custom_components.budgetthuis.parser import AMSTERDAM, HourPrice

DE_BILT = Location(latitude=52.1, longitude=5.18)
CONTRACT_PRICE = 0.42


def _config(
    percent: float,
    max_beursprijs: float,
    bonus_from: date = date(2027, 1, 1),
    bonus_until: date | None = None,
) -> ExportConfig:
    return ExportConfig(
        location=DE_BILT,
        bonus_percent=percent,
        bonus_max_beursprijs=max_beursprijs,
        bonus_from=bonus_from,
        bonus_until=bonus_until,
    )


ZONNEBONUS = _config(30.0, 0.20)


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

    assert calculate_export_price(hour, contract_price, ZONNEBONUS) == contract_price


def test_zonnebonus_adds_30_percent_to_the_beursprijs() -> None:
    """Het voorbeeld van Budget Thuis: beursprijs 0,10 levert 0,13 op."""
    hour = _hour(_local(2027, 6, 15, 12), commodity_net=0.10)

    assert calculate_export_price(hour, CONTRACT_PRICE, ZONNEBONUS) == 0.13


def test_zonnebonus_is_capped_at_a_beursprijs_of_20_cents() -> None:
    hour = _hour(_local(2027, 6, 15, 12), commodity_net=0.30)

    assert calculate_export_price(hour, CONTRACT_PRICE, ZONNEBONUS) == 0.36


@pytest.mark.parametrize("beursprijs", [0.0, -0.02])
def test_no_bonus_at_a_beursprijs_of_zero_or_lower(beursprijs) -> None:
    hour = _hour(_local(2027, 6, 15, 12), commodity_net=beursprijs)

    assert calculate_export_price(hour, CONTRACT_PRICE, ZONNEBONUS) == beursprijs


@pytest.mark.parametrize("start_hour", [4, 22, 23])
def test_no_bonus_outside_the_window(start_hour) -> None:
    """Juni: 04:00-05:00 begint te vroeg, 22:00 en 23:00-24:00 eindigen te laat."""
    hour = _hour(_local(2027, 6, 15, start_hour), commodity_net=0.10)

    assert calculate_export_price(hour, CONTRACT_PRICE, ZONNEBONUS) == 0.10


def test_bonus_applies_to_the_last_hour_inside_the_window() -> None:
    hour = _hour(_local(2027, 6, 15, 21), commodity_net=0.10)

    assert calculate_export_price(hour, CONTRACT_PRICE, ZONNEBONUS) == 0.13


def test_missing_beursprijs_returns_none() -> None:
    hour = _hour(_local(2027, 6, 15, 12), commodity_net=None)

    assert calculate_export_price(hour, CONTRACT_PRICE, ZONNEBONUS) is None


def test_bonus_percentage_and_cap_follow_the_options() -> None:
    config = _config(50.0, 0.10)
    hour = _hour(_local(2027, 6, 15, 12), commodity_net=0.30)

    assert calculate_export_price(hour, CONTRACT_PRICE, config) == 0.35


def test_zero_percent_switches_the_bonus_off() -> None:
    config = _config(0.0, 0.20)
    hour = _hour(_local(2027, 6, 15, 12), commodity_net=0.10)

    assert calculate_export_price(hour, CONTRACT_PRICE, config) == 0.10


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2027, 2, 28), 0.10),  # voor de begindatum
        (date(2027, 3, 1), 0.13),  # de begindatum telt mee
        (date(2027, 6, 30), 0.13),  # de einddatum telt mee
        (date(2027, 7, 1), 0.10),  # na de einddatum
    ],
)
def test_bonus_only_applies_within_the_configured_period(day, expected) -> None:
    config = _config(30.0, 0.20, date(2027, 3, 1), date(2027, 6, 30))
    hour = _hour(_local(day.year, day.month, day.day, 12), commodity_net=0.10)

    assert calculate_export_price(hour, CONTRACT_PRICE, config) == expected
