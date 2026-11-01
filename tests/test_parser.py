"""Unittests voor het inlezen van de tarievenpagina van Budget Thuis."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from custom_components.budgetthuis.parser import (
    GAS,
    TariffParseError,
    parse_tariff_days,
)

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
    # De regel 02:00-03:00 in de fixture heeft geen TotalTariff en moet vervallen,
    # niet de uitlezing laten crashen of als valse nulprijs verschijnen.
    today = by_date["2026-07-29"]
    assert len(today) == 2
    assert all(h.start.hour != 2 for h in today)


def test_skips_days_with_no_tariffs(tariff_html: str) -> None:
    by_date = parse_tariff_days(tariff_html)
    assert "2026-07-31" not in by_date


def test_missing_next_data_raises() -> None:
    with pytest.raises(TariffParseError, match="Geen __NEXT_DATA__"):
        parse_tariff_days("<html><body>no data here</body></html>")


def test_malformed_json_raises() -> None:
    html = '<script id="__NEXT_DATA__" type="application/json">{not valid json</script>'
    with pytest.raises(TariffParseError, match="Ongeldige __NEXT_DATA__"):
        parse_tariff_days(html)


def test_missing_tariff_days_raises() -> None:
    html = (
        '<script id="__NEXT_DATA__" type="application/json">'
        '{"props": {"pageProps": {}}}</script>'
    )
    with pytest.raises(TariffParseError, match="Geen tariffDays"):
        parse_tariff_days(html)


def test_parses_gas_blocks_per_day(tariff_html: str) -> None:
    by_date = parse_tariff_days(tariff_html, GAS)

    # Alleen 2026-07-29 heeft gas in de fixture; dagen zonder gas blijven weg.
    assert set(by_date) == {"2026-07-29"}
    blocks = by_date["2026-07-29"]
    # Gesorteerd op begin, in welke volgorde de pagina ze ook toont.
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


# --- Zomertijd ---------------------------------------------------
# De pagina gebruikt naïeve Amsterdamse klokkijden. Op 2026-10-25 gaat de klok
# terug (02:00-03:00 komt twee keer voor, 25 uur); op 2027-03-28 gaat hij vooruit
# (02:00-03:00 bestaat niet, 23 uur).


def _dst_page(
    entries: list[tuple[str, str, float]], key: str = "ElectricityTariffs"
) -> str:
    tariffs = [
        {
            "Start": start,
            "End": end,
            "TotalTariff": {"AmountGross": price},
            "Commodity": {"AmountNet": price},
            "EnergyTax": {"AmountNet": 0.0},
        }
        for start, end, price in entries
    ]
    payload = {"props": {"pageProps": {"tariffDays": [{key: tariffs}]}}}
    return (
        '<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(payload)}</script>"
    )


def _wall(day: str, hour: int) -> str:
    return f"{day} {hour:02d}:00:00"


def _autumn_entries(first_repeat_end: int = 3) -> list[tuple[str, str, float]]:
    day = "2026-10-25"
    entries = [(_wall(day, 0), _wall(day, 1), 0.0), (_wall(day, 1), _wall(day, 2), 1.0)]
    entries.append((_wall(day, 2), _wall(day, first_repeat_end), 2.0))  # summer time
    entries.append((_wall(day, 2), _wall(day, 3), 3.0))  # winter time
    entries += [(_wall(day, h), _wall(day, h + 1), float(h + 1)) for h in range(3, 23)]
    entries.append((_wall(day, 23), "2026-10-26 00:00:00", 24.0))
    return entries


def _assert_contiguous_utc_hours(blocks, first_utc: str) -> None:
    start = datetime.fromisoformat(first_utc)
    for i, block in enumerate(blocks):
        assert block.start.astimezone(UTC) == start + timedelta(hours=i), i
        assert block.end.astimezone(UTC) == start + timedelta(hours=i + 1), i


@pytest.mark.parametrize("first_repeat_end", [3, 2])
def test_autumn_changeover_keeps_both_0200_hours(first_repeat_end: int) -> None:
    """Beide schrijfwijzen van het einde van het eerste 02:00-blok."""
    blocks = parse_tariff_days(_dst_page(_autumn_entries(first_repeat_end)))[
        "2026-10-25"
    ]

    assert len(blocks) == 25
    assert [b.price for b in blocks] == [float(i) for i in range(25)]
    _assert_contiguous_utc_hours(blocks, "2026-10-24T22:00:00+00:00")
    assert blocks[2].start.isoformat() == "2026-10-25T02:00:00+02:00"
    assert blocks[3].start.isoformat() == "2026-10-25T02:00:00+01:00"


def test_autumn_changeover_skipped_first_0200_still_marks_the_repeat() -> None:
    entries = _autumn_entries()
    html = _dst_page(entries).replace('"TotalTariff": {"AmountGross": 2.0}, ', "", 1)
    blocks = parse_tariff_days(html)["2026-10-25"]

    repeat = next(b for b in blocks if b.price == 3.0)
    assert repeat.start.isoformat() == "2026-10-25T02:00:00+01:00"


def test_spring_changeover_has_23_contiguous_hours() -> None:
    day = "2027-03-28"
    entries = [(_wall(day, 0), _wall(day, 1), 0.0), (_wall(day, 1), _wall(day, 2), 1.0)]
    entries += [(_wall(day, h), _wall(day, h + 1), float(h - 1)) for h in range(3, 23)]
    entries.append((_wall(day, 23), "2027-03-29 00:00:00", 22.0))
    blocks = parse_tariff_days(_dst_page(entries))[day]

    assert len(blocks) == 23
    _assert_contiguous_utc_hours(blocks, "2027-03-27T23:00:00+00:00")
    assert blocks[2].start.isoformat() == "2027-03-28T03:00:00+02:00"


def test_timestamps_with_an_offset_are_respected() -> None:
    """De app-API stuurt UTC-verschillen mee; behoud ze als de pagina dat ook doet."""
    entries = [
        ("2026-10-25T02:00:00+02:00", "2026-10-25T02:00:00+01:00", 2.0),
        ("2026-10-25T02:00:00+01:00", "2026-10-25T03:00:00+01:00", 3.0),
    ]
    blocks = parse_tariff_days(_dst_page(entries))["2026-10-25"]

    _assert_contiguous_utc_hours(blocks, "2026-10-25T00:00:00+00:00")


def test_autumn_gas_block_spans_seven_real_hours() -> None:
    entries = [
        ("2026-10-25 00:00:00", "2026-10-25 06:00:00", 1.0),
        ("2026-10-25 06:00:00", "2026-10-26 00:00:00", 2.0),
    ]
    blocks = parse_tariff_days(_dst_page(entries, GAS), GAS)["2026-10-25"]

    assert (blocks[0].end - blocks[0].start) == timedelta(hours=6)  # wall clock
    assert blocks[0].end.timestamp() - blocks[0].start.timestamp() == 7 * 3600
    assert blocks[0].end.timestamp() == blocks[1].start.timestamp()


def test_skips_blocks_without_start_or_end() -> None:
    """Een blok zonder begin of einde is onbruikbaar en wordt overgeslagen."""
    tariffs = [
        {"End": "2026-07-29 01:00:00", "TotalTariff": {"AmountGross": 0.2}},
        {"Start": "2026-07-29 01:00:00", "TotalTariff": {"AmountGross": 0.2}},
        {
            "Start": "2026-07-29 02:00:00",
            "End": "2026-07-29 03:00:00",
            "TotalTariff": {"AmountGross": 0.3},
        },
    ]
    payload = json.dumps(
        {"props": {"pageProps": {"tariffDays": [{"ElectricityTariffs": tariffs}]}}}
    )
    html = f'<script id="__NEXT_DATA__" type="application/json">{payload}</script>'

    by_date = parse_tariff_days(html)

    assert [h.price for h in by_date["2026-07-29"]] == [0.3]
