"""Shared test data for the Home Assistant-level tests.

A fake tariff page with two recognisable days of electricity and gas prices,
plus the helpers to build it. Used by the setup_integration fixture in
conftest.py and the test_ha_* modules. Plain module, no Home Assistant import.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

AMSTERDAM = ZoneInfo("Europe/Amsterdam")
DAY_1 = date(2026, 7, 29)
DAY_2 = DAY_1 + timedelta(days=1)
ENERGY_TAX = 0.1
GAS_INKOOPVERGOEDING = 0.05
NO_SURCHARGES = {
    "inkoopvergoeding": 0.0,
    "vat_percent": 0.0,
    "beursprijs_markup": 0.0,
    "gas_inkoopvergoeding": GAS_INKOOPVERGOEDING,
}


def commodity(day: date, hour: int) -> float:
    """A distinct, easily recognisable beursprijs per (day, hour)."""
    return round((0.5 if day == DAY_2 else 0.0) + hour / 100, 4)


def ts(day: date, hour: int) -> str:
    """Budget Thuis's naive local timestamp format; hour 24 is the next midnight."""
    return f"{(day + timedelta(days=hour // 24)).isoformat()} {hour % 24:02d}:00:00"


def tariff(start: str, end: str, commodity: float, tax: float) -> dict:
    return {
        "Start": start,
        "End": end,
        "TotalTariff": {"AmountGross": round((commodity + tax) * 1.21, 5)},
        "Commodity": {"AmountNet": commodity},
        "EnergyTax": {"AmountNet": tax},
    }


def page(days: list[date]) -> str:
    tariff_days = []
    for day in days:
        electricity = [
            tariff(ts(day, h), ts(day, h + 1), commodity(day, h), ENERGY_TAX)
            for h in range(24)
        ]
        gas_day_price = 1.0 if day == DAY_1 else 1.2
        gas = [
            # 00:00-06:00 still belongs to the previous gas day.
            tariff(ts(day, 0), ts(day, 6), round(gas_day_price - 0.1, 4), 0.6),
            tariff(ts(day, 6), ts(day, 24), gas_day_price, 0.6),
        ]
        tariff_days.append(
            {"Start": ts(day, 0), "ElectricityTariffs": electricity, "GasTariffs": gas}
        )
    payload = json.dumps({"props": {"pageProps": {"tariffDays": tariff_days}}})
    script = f'<script id="__NEXT_DATA__" type="application/json">{payload}</script>'
    return f"<html>{script}</html>"


def local(day: date, hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(
        day.year, day.month, day.day, hour, minute, second, tzinfo=AMSTERDAM
    )
