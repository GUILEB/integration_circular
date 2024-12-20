"""Circular Climate Entities."""

from __future__ import annotations

import asyncio
from typing import Any, TYPE_CHECKING

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
)
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CircularDeviceStatus
from .const import (
    DEFAULT_DELTA_ECOMODE_TEMP,
    DEFAULT_DELTA_ECOMODE_TIME,
    DEFAULT_THERMOSTAT_TEMP,
    DOMAIN,
    LOGGER,
    MAX_THERMOSTAT_TEMP,
    MIN_THERMOSTAT_TEMP,
)
from .entity import CircularEntity

if TYPE_CHECKING:
    from .coordinator import CircularDataUpdateCoordinator

CIRCULAR_CLIMATES: tuple[ClimateEntityDescription, ...] = (
    ClimateEntityDescription(key="climate", name="Thermostat"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Climate entity setup."""
    coordinator: CircularDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CircularClimate(
            coordinator=coordinator,
            description=description,
        )
        for description in CIRCULAR_CLIMATES
    )


class CircularClimate(CircularEntity, ClimateEntity):
    """Circular climate entity."""

    entity_description: ClimateEntityDescription
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    attr_fan_mode = FAN_AUTO
    _attr_fan_modes = [
        FAN_OFF,
        FAN_LOW,
        FAN_MEDIUM,
        FAN_HIGH,
        FAN_AUTO,
    ]
    _attr_min_temp = MIN_THERMOSTAT_TEMP
    _attr_max_temp = MAX_THERMOSTAT_TEMP
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    _attr_target_temperature_step = 1
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    last_temp = DEFAULT_THERMOSTAT_TEMP

    fan_mode_register = {
        FAN_OFF: 0,
        FAN_LOW: 1,
        FAN_MEDIUM: 3,
        FAN_HIGH: 5,
        FAN_AUTO: 6,
    }

    def __init__(
        self,
        coordinator: CircularDataUpdateCoordinator,
        description: ClimateEntityDescription,
    ) -> None:
        """Configure climate entry and override last_temp if the thermostat is currently on."""
        super().__init__(coordinator, description)
        self.last_temp = coordinator.data.temperature_set

    @property
    def hvac_mode(self) -> str:
        """Return current hvac mode."""
        status = self.coordinator.read_api.data.status
        if status not in [
            CircularDeviceStatus.OFF,
            CircularDeviceStatus.ALARM,
            CircularDeviceStatus.UNKNOWN,
        ]:
            return HVACMode.HEAT
        return HVACMode.OFF

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode to normal or thermostat control."""
        LOGGER.warning(
            "Setting hvac mode to [%s] - last temp: %s", hvac_mode, self.last_temp
        )

        # Changement d'état Chauffage à OFF
        if hvac_mode == HVACMode.OFF:
            temp_c = min(
                self.coordinator.read_api.data.temperature_read, self.last_temp
            )
            await self.coordinator.control_api.set_temperature(temp_c)
            return

        # ECO MODE : Restauration de la consigne de temperature, suite arrêt en ECO Mode
        if (
            hvac_mode == HVACMode.HEAT
            and self.coordinator.read_api.data.is_ecomode_stop
        ):
            await self.coordinator.control_api.set_temperature_with_delta(
                self.coordinator.read_api.data.temperature_read
            )
        return

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Turn on thermostat by setting a target temperature."""
        raw_target_temp = kwargs[ATTR_TEMPERATURE]
        self.last_temp = raw_target_temp
        LOGGER.warning(
            "Setting target temp to %sc %sf",
            int(raw_target_temp),
            (raw_target_temp * 9 / 5) + 32,
        )
        await self.coordinator.control_api.set_temperature(raw_target_temp)

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return float(self.coordinator.read_api.data.temperature_read)

    @property
    def target_temperature(self) -> float:
        """Return target temperature."""
        return float(self.coordinator.read_api.data.temperature_set)

    @property
    def turn_on(self):
        """Turn the entity on."""
        LOGGER.debug("Setting turn_on : %s ", self._attr_hvac_mode)

    async def async_turn_on(self):
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    @property
    def turn_off(self):
        """Turn the entity off."""
        LOGGER.debug("Setting turn_off : %s ", self._attr_hvac_mode)

    async def async_turn_off(self):
        """Turn the entity off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    @property
    def fan_mode(self) -> str | None:
        """Set new target fan mode."""
        keys = [
            k
            for k, v in self.fan_mode_register.items()
            if v == self.coordinator.read_api.data.fan_speed
        ]
        if keys:
            return keys[0]
        return FAN_AUTO

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        LOGGER.debug("Setting Fan value %s", fan_mode)
        await self.coordinator.control_api.set_fan_speed(
            self.fan_mode_register[fan_mode]
        )
