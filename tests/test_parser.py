"""Unit tests for the pure Budget Thuis tariff page parser.

Deliberately imports only custom_components.budgetthuis.parser (no Home
Assistant dependency), so these run with plain pytest.
"""
import json
from datetime import UTC, datetime, timedelta
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


# --- Daylight saving time ---------------------------------------------------
# The page uses naive Amsterdam wall-clock timestamps. On 2026-10-25 the
# clock goes back (02:00-03:00 happens twice, 25 hours); on 2027-03-28 it
# jumps forward (02:00-03:00 doesn't exist, 23 hours).


def _dst_page(entries: list[tuple[str, str, float]], key: str = "ElectricityTariffs") -> str:
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
    """Both spellings of the first 02:00 block's end ("03:00" or "02:00")."""
    blocks = parse_tariff_days(_dst_page(_autumn_entries(first_repeat_end)))["2026-10-25"]

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
    """The app API sends offsets; if the page ever does too, keep them."""
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
