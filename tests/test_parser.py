"""Unit tests for the pure Budget Thuis tariff page parser.

Deliberately imports only custom_components.budgetthuis.parser (no Home
Assistant dependency), so these run with plain pytest.
"""
from pathlib import Path

import pytest

from custom_components.budgetthuis.parser import GAS, TariffParseError, parse_tariff_days

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "tariff_page.html"


@pytest.fixture
def tariff_html() -> str:
    return FIXTURE_PATH.read_text()


def test_parses_hourly_prices_per_day(tariff_html: str) -> None:
    by_date = parse_tariff_days(tariff_html)

    assert set(by_date) == {"2026-07-29", "2026-07-30"}

    today = by_date["2026-07-29"]
    assert [h.price for h in today] == [0.2431, 0.2109]
    assert today[0].start.isoformat() == "2026-07-29T00:00:00+02:00"
    assert today[0].end.isoformat() == "2026-07-29T01:00:00+02:00"
    assert today[0].commodity_net == 0.0521
    assert today[0].energy_tax_net == 0.1108


def test_skips_hours_with_no_total_tariff(tariff_html: str) -> None:
    by_date = parse_tariff_days(tariff_html)
    # The fixture's 02:00-03:00 entry has no TotalTariff and must be dropped,
    # not crash the parse or show up as a bogus zero price.
    today = by_date["2026-07-29"]
    assert len(today) == 2
    assert all(h.start.hour != 2 for h in today)


def test_skips_days_with_no_tariffs(tariff_html: str) -> None:
    by_date = parse_tariff_days(tariff_html)
    assert "2026-07-31" not in by_date


def test_missing_next_data_raises() -> None:
    with pytest.raises(TariffParseError, match="No __NEXT_DATA__"):
        parse_tariff_days("<html><body>no data here</body></html>")


def test_malformed_json_raises() -> None:
    html = (
        '<script id="__NEXT_DATA__" type="application/json">{not valid json</script>'
    )
    with pytest.raises(TariffParseError, match="Malformed __NEXT_DATA__"):
        parse_tariff_days(html)


def test_missing_tariff_days_raises() -> None:
    html = '<script id="__NEXT_DATA__" type="application/json">{"props": {"pageProps": {}}}</script>'
    with pytest.raises(TariffParseError, match="No tariffDays"):
        parse_tariff_days(html)


def test_parses_gas_blocks_per_day(tariff_html: str) -> None:
    by_date = parse_tariff_days(tariff_html, GAS)

    # Only 2026-07-29 carries gas in the fixture; days without it are left out.
    assert set(by_date) == {"2026-07-29"}
    blocks = by_date["2026-07-29"]
    # Sorted by start, whatever order the page lists them in.
    assert [b.start.hour for b in blocks] == [0, 6]
    assert blocks[0].end.isoformat() == "2026-07-29T06:00:00+02:00"
    assert blocks[1].end.isoformat() == "2026-07-30T00:00:00+02:00"
    assert blocks[1].commodity_net == 0.8529
    assert blocks[1].energy_tax_net == 0.6007


def test_gas_does_not_leak_into_electricity(tariff_html: str) -> None:
    today = parse_tariff_days(tariff_html)["2026-07-29"]
    assert [h.price for h in today] == [0.2431, 0.2109]


def test_page_without_gas_yields_no_gas_days() -> None:
    html = (
        '<script id="__NEXT_DATA__" type="application/json">'
        '{"props": {"pageProps": {"tariffDays": [{"ElectricityTariffs": []}]}}}'
        "</script>"
    )
    assert parse_tariff_days(html, GAS) == {}
