"""Gedeelde basis voor alle entiteiten van Budget Thuis Dynamic Prices."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BudgetThuisCoordinator
from .models import BudgetThuisData


class BudgetThuisEntity(CoordinatorEntity[BudgetThuisCoordinator]):
    """Gedeelde opzet voor alle Budget Thuis-entiteiten.

    Een subklasse zet _attr_translation_key: die bepaalt de (vertaalde) naam,
    het icoon (icons.json) en het unieke ID van de entiteit.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: BudgetThuisCoordinator) -> None:
        """Maak de entiteit aan onder het gedeelde apparaat."""
        super().__init__(coordinator)
        entry_id = coordinator.entry.entry_id
        self._attr_unique_id = f"{entry_id}_{self._attr_translation_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Budget Thuis Dynamic Prices",
            manufacturer="Budget Thuis",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def data(self) -> BudgetThuisData:
        """De actuele tariefgegevens van de coordinator."""
        return self.coordinator.data
