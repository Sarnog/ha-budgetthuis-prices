"""Unittests voor de prijsberekening voor het eigen contract."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.budgetthuis.parser import HourPrice
from custom_components.budgetthuis.pricing import ContractConfig, calculate_price


def _hour(
    commodity_net: float | None, energy_tax_net: float | None = 0.09161
) -> HourPrice:
    return HourPrice(
        start=datetime(2026, 7, 29, 12, 0, tzinfo=UTC),
        end=datetime(2026, 7, 29, 13, 0, tzinfo=UTC),
        price=0.9999,  # de siteprijs: bewust anders, mag niet meetellen
        commodity_net=commodity_net,
        energy_tax_net=energy_tax_net,
    )


def test_calculates_all_in_price_from_beursprijs() -> None:
    config = ContractConfig(inkoopvergoeding=0.016822, vat_percent=21.0)
    price = calculate_price(_hour(0.05), config)

    expected = round((0.05 + 0.09161) * 1.21 + 0.016822, 5)
    assert price == expected


def test_inkoopvergoeding_is_not_taxed_again() -> None:
    """De app toont de inkoopvergoeding incl. BTW; nogmaals belasten rekent te veel."""
    config = ContractConfig(inkoopvergoeding=0.121, vat_percent=21.0)
    price = calculate_price(_hour(0.0, energy_tax_net=0.0), config)

    assert price == 0.121


def test_beursprijs_markup_is_added_before_vat() -> None:
    config = ContractConfig(
        inkoopvergoeding=0.016822, vat_percent=21.0, beursprijs_markup=0.01
    )
    price = calculate_price(_hour(0.05), config)

    expected = round((0.05 + 0.01 + 0.09161) * 1.21 + 0.016822, 5)
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


def test_keeps_five_decimals_like_mijn_budgetthuis() -> None:
    """mijn.budgetthuis.nl toont 5 decimalen; afronden op 3 vertekende de gemiddelden.

    Echt gasblok van 2026-11-02 06:00: de siteprijs 1,96299389 is (beursprijs +
    energiebelasting) incl. BTW; met de gasinkoopvergoeding van 0,06413 geeft de
    contractpagina 2,02712, niet 2,027.
    """
    config = ContractConfig(inkoopvergoeding=0.06413, vat_percent=21.0)
    price = calculate_price(_hour(1.96299389 / 1.21, energy_tax_net=0.0), config)

    assert price == 2.02712
