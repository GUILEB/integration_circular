"""Circular Climate Entities."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CircularDeviceStatus
from .const import (
    DEFAULT_THERMOSTAT_TEMP,
    DOMAIN,
    LOGGER,
    MAX_THERMOSTAT_TEMP,
    MIN_THERMOSTAT_TEMP,
)
from .coordinator import CircularDataUpdateCoordinator
from .entity import CircularEntity

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
    _attr_fan_mode = "FAN_AUTO"
    _attr_fan_modes = [
        "FAN_OFF",
        "FAN_LOW",
        "FAN_MEDIUM",
        "FAN_HIGH",
        "FAN_AUTO",
    ]
    _attr_min_temp = MIN_THERMOSTAT_TEMP
    _attr_max_temp = MAX_THERMOSTAT_TEMP
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 0.5
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    last_temp = DEFAULT_THERMOSTAT_TEMP

    def __init__(
        self,
        coordinator: CircularDataUpdateCoordinator,
        description: ClimateEntityDescription,
    ) -> None:
        """Configure climate entry - and override last_temp if the thermostat is currently on."""
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
            "Setting mode to [%s] - using last temp: %s", hvac_mode, self.last_temp
        )

        if hvac_mode == HVACMode.OFF:
            return

        # hvac_mode == HVACMode.HEAT
        # 1) Set the desired target temp
        # await self.coordinator.control_api.set_thermostat_c(
        #    temp_c=self.last_temp,
        # )

        # 2) Make sure the fireplace is on!
        # if not self.coordinator.read_api.data.is_on:
        #    await self.coordinator.control_api.flame_on()

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

    async def async_turn_on(self):
        """Turn the entity on."""

    @property
    def turn_off(self):
        """Turn the entity off."""

    async def async_turn_off(self):
        """Turn the entity off."""

    @property
    def toggle(self):
        """Toggle the entity."""

    async def async_toggle(self):
        """Toggle the entity."""

    @property
    def set_fan_mode(self, fan_mode) -> str:
        """Set new target fan mode."""
        int_value = self.coordinator.read_api.data.fan_speed
        match int_value:
            case 0:
                return "FAN_OFF"
            case 1:
                return "FAN_LOW"
            case 3:
                return "FAN_MEDIUM"
            case 5:
                return "FAN_HIGH"
            case 6:
                return "FAN_AUTO"

        return "FAN_OFF"

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        LOGGER.debug("Setting Fan value %s", fan_mode)

        match fan_mode:
            case "FAN_OFF":
                int_value = 0
            case "FAN_LOW":
                int_value = 1
            case "FAN_MEDIUM":
                int_value = 3
            case "FAN_HIGH":
                int_value = 5
            case "FAN_AUTO":
                int_value = 6

        await self.coordinator.control_api.set_fan_speed(int_value)
