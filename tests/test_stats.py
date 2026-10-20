"""Unit tests for the pure hourly-price statistics helpers.

No Home Assistant dependency, same as test_parser.py/test_pricing.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from custom_components.budgetthuis.stats import (
    average,
    cheapest_period,
    highest,
    hour_for,
    lowest,
    most_expensive_period,
)


@dataclass
class _Hour:
    """Stands in for coordinator.PricedHour - stats.py only needs start/end/price."""

    start: datetime
    end: datetime
    price: float | None


def _hours(*prices: float | None) -> list[_Hour]:
    base = datetime(2026, 7, 29, 0, 0, tzinfo=UTC)
    return [
        _Hour(
            start=base + timedelta(hours=i),
            end=base + timedelta(hours=i + 1),
            price=price,
        )
        for i, price in enumerate(prices)
    ]


def test_hour_for_matches_containing_interval() -> None:
    hours = _hours(0.1, 0.2, 0.3)
    moment = hours[1].start + timedelta(minutes=30)

    assert hour_for(hours, moment) is hours[1]


def test_hour_for_returns_none_outside_range() -> None:
    hours = _hours(0.1, 0.2)
    moment = hours[-1].end + timedelta(hours=1)

    assert hour_for(hours, moment) is None


def test_average_lowest_highest_ignore_missing_prices() -> None:
    hours = _hours(0.1, None, 0.3)

    assert average(hours) == 0.2
    assert lowest(hours) == 0.1
    assert highest(hours) == 0.3


def test_average_lowest_highest_of_empty_or_all_missing() -> None:
    assert average(_hours()) is None
    assert lowest(_hours(None, None)) is None
    assert highest(_hours(None, None)) is None


def test_cheapest_period_picks_the_lowest_average_run() -> None:
    # average = 0.2; two below-average runs: [0.1] and [0.05, 0.1] - the
    # second has the lower average.
    hours = _hours(0.1, 0.3, 0.05, 0.1, 0.4)

    start, end, run_average = cheapest_period(hours)

    assert start == hours[2].start
    assert end == hours[3].end
    assert run_average == 0.075


def test_most_expensive_period_picks_the_highest_average_run() -> None:
    # average = 0.2; two above-average runs: [0.3] and [0.5, 0.4] - the
    # second has the higher average.
    hours = _hours(0.3, 0.1, 0.05, 0.5, 0.4)

    start, end, run_average = most_expensive_period(hours)

    assert start == hours[3].start
    assert end == hours[4].end
    assert run_average == 0.45


def test_periods_are_none_without_data() -> None:
    assert cheapest_period(_hours()) is None
    assert most_expensive_period(_hours()) is None


def test_most_expensive_period_none_when_every_hour_is_identical() -> None:
    # Every hour equals the average, so there's no above-average run.
    hours = _hours(0.2, 0.2, 0.2)

    assert most_expensive_period(hours) is None
    # But the whole day is a (tied) below-average run, so cheapest_period
    # still finds it.
    start, end, run_average = cheapest_period(hours)
    assert start == hours[0].start
    assert end == hours[-1].end
    assert run_average == 0.2


def test_periods_skip_hours_with_missing_price() -> None:
    # None breaks runs, same as an hour that's plainly not part of any block.
    hours = _hours(0.05, None, 0.4)

    start, end, run_average = cheapest_period(hours)
    assert (start, end, run_average) == (hours[0].start, hours[0].end, 0.05)


def test_hour_for_tells_the_repeated_autumn_hour_apart() -> None:
    """Same tzinfo + same wall-clock time must still match by real instant."""
    from zoneinfo import ZoneInfo

    ams = ZoneInfo("Europe/Amsterdam")
    summer = datetime(2026, 10, 25, 2, 0, tzinfo=ams, fold=0)
    winter = datetime(2026, 10, 25, 2, 0, tzinfo=ams, fold=1)
    after = datetime(2026, 10, 25, 3, 0, tzinfo=ams)
    hours = [_Hour(summer, winter, 0.1), _Hour(winter, after, 0.2)]

    assert (
        hour_for(hours, datetime(2026, 10, 25, 2, 30, tzinfo=ams, fold=0)).price == 0.1
    )
    assert (
        hour_for(hours, datetime(2026, 10, 25, 2, 30, tzinfo=ams, fold=1)).price == 0.2
    )
