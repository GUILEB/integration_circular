"""Flame height number sensors."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    LOGGER,
    MAX_DELTA_ECOMODE_TEMP,
    MAX_POWER,
    MIN_DELTA_ECOMODE_TEMP,
    MIN_POWER,
    DEFAULT_DELTA_ECOMODE_TEMP,
)
from .coordinator import CircularDataUpdateCoordinator
from .entity import CircularEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up power."""
    coordinator: CircularDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    descriptionpower = NumberEntityDescription(
        key="power",
        name="Power Control",
        icon="mdi:arrow-expand-vertical",
    )

    async_add_entities(
        [
            CircularPowerControlEntity(
                coordinator=coordinator, description=descriptionpower
            )
        ]
    )

    descriptiondelta = NumberEntityDescription(
        key="delta eco mode",
        name="Delta ECO mode Control",
        icon="mdi:arrow-expand-vertical",
    )

    async_add_entities(
        [EcoDeltaControlEntity(coordinator=coordinator, description=descriptiondelta)]
    )


@dataclass
class CircularPowerControlEntity(CircularEntity, NumberEntity):
    """Power control entity."""

    _attr_native_max_value: float = MAX_POWER
    _attr_native_min_value: float = MIN_POWER
    _attr_native_step: float = 1
    _attr_mode: NumberMode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: CircularDataUpdateCoordinator,
        description: NumberEntityDescription,
    ) -> None:
        """Initialize Power Sensor."""
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> float | None:
        """Return the current power number value."""
        value = self.coordinator.read_api.data.power_set
        return value

    async def async_set_native_value(self, value: float) -> None:
        """Slider change."""
        value_to_send: int = int(value)
        LOGGER.debug(
            "%s set power to %d with raw value %s",
            self._attr_name,
            value,
            value_to_send,
        )
        await self.coordinator.control_api.set_power(value=value_to_send)
        await self.coordinator.async_refresh()


@dataclass
class EcoDeltaControlEntity(CircularEntity, NumberEntity):
    """Delta Power control entity."""

    _attr_native_max_value: int = MAX_DELTA_ECOMODE_TEMP
    _attr_native_min_value: int = MIN_DELTA_ECOMODE_TEMP
    _attr_native_value: int = DEFAULT_DELTA_ECOMODE_TEMP
    _attr_native_step: int = 1
    _attr_mode: NumberMode = NumberMode.BOX

    def __init__(
        self,
        coordinator: CircularDataUpdateCoordinator,
        description: NumberEntityDescription,
    ) -> None:
        """Initialize Power Sensor."""
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> float | None:
        """Return the current power number value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Slider change."""
        value_to_send: int = int(value)
        LOGGER.debug(
            "%s set delta eco_mode to %d with raw value %s",
            self._attr_name,
            value,
            value_to_send,
        )
        self._attr_native_value = value_to_send
        await self.coordinator.control_api.set_delta_temp(value=value_to_send)
        await self.coordinator.async_refresh()
        self.async_write_ha_state()
