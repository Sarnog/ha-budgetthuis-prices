"""Ophalen van de openbare tarievenpagina van Budget Thuis.

Alleen het netwerkverzoek; inlezen (parser.py) en prijzen (pricing.py) staan los
hiervan, en de coordinator verbindt ze.
"""

from __future__ import annotations

from aiohttp import ClientError, ClientSession

from .const import TARIFF_URL


class BudgetThuisApiError(Exception):
    """De tarievenpagina kon niet worden opgehaald."""


class BudgetThuisApiClient:
    """Haalt de HTML van de tarievenpagina op met de sessie van Home Assistant."""

    def __init__(self, session: ClientSession) -> None:
        """Bewaar de gedeelde HTTP-sessie."""
        self._session = session

    async def async_get_tariff_page(self) -> str:
        """Geef de HTML van de tarievenpagina, of een BudgetThuisApiError."""
        try:
            async with self._session.get(TARIFF_URL) as response:
                response.raise_for_status()
                return await response.text()
        except (ClientError, TimeoutError) as err:
            raise BudgetThuisApiError(
                f"Fout bij het ophalen van de tarievenpagina: {err}"
            ) from err
