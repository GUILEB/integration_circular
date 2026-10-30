"""Circular Climate Entities."""

from typing import Any

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
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CircularDeviceStatus
from .const import (
    LOGGER,
    MAX_POWER,
    MAX_THERMOSTAT_TEMP,
    MIN_POWER,
    MIN_THERMOSTAT_TEMP,
)
from .coordinator import CircularConfigEntry
from .entity import CircularEntity

CIRCULAR_CLIMATES: tuple[ClimateEntityDescription, ...] = (
    ClimateEntityDescription(
        key="climate", name="Thermostat", translation_key="thermostat"
    ),
)

# Statuts pour lesquels le poêle n'est pas en mode chauffage
HVAC_OFF_STATUSES = (
    CircularDeviceStatus.OFF,
    CircularDeviceStatus.FINAL_CLEANING,
    CircularDeviceStatus.ALARM,
    CircularDeviceStatus.UNKNOWN,
)

HVAC_ACTIONS = {
    CircularDeviceStatus.WAIT_FOR_FLAME: HVACAction.PREHEATING,
    CircularDeviceStatus.POWER_ON: HVACAction.PREHEATING,
    CircularDeviceStatus.STABLE_FLAME: HVACAction.PREHEATING,
    CircularDeviceStatus.WORK: HVACAction.HEATING,
    CircularDeviceStatus.MODULA: HVACAction.HEATING,
    CircularDeviceStatus.BRAZIER_CLEANING: HVACAction.HEATING,
    CircularDeviceStatus.ECO_STOP: HVACAction.IDLE,
}

# Niveaux de puissance exposés en preset ("1" à "5")
POWER_PRESETS = [str(power) for power in range(MIN_POWER, MAX_POWER + 1)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CircularConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Climate entity setup."""
    coordinator = entry.runtime_data
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
    _attr_fan_modes = [
        FAN_OFF,
        FAN_LOW,
        FAN_MEDIUM,
        FAN_HIGH,
        FAN_AUTO,
    ]
    _attr_preset_modes = POWER_PRESETS
    _attr_min_temp = MIN_THERMOSTAT_TEMP
    _attr_max_temp = MAX_THERMOSTAT_TEMP
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    _attr_target_temperature_step = 1
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    fan_mode_register = {
        FAN_OFF: 0,
        FAN_LOW: 1,
        FAN_MEDIUM: 3,
        FAN_HIGH: 5,
        FAN_AUTO: 6,
    }

    @property
    def hvac_mode(self) -> str:
        """Return current hvac mode."""
        if self.coordinator.read_api.data.status in HVAC_OFF_STATUSES:
            return HVACMode.OFF
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction:
        """Return the current burner activity."""
        return HVAC_ACTIONS.get(self.coordinator.read_api.data.status, HVACAction.OFF)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Turn the stove on (heat) or off."""
        LOGGER.debug("Setting hvac mode to [%s]", hvac_mode)

        if hvac_mode == HVACMode.OFF:
            await self.coordinator.control_api.turn_off()

        # ECO MODE : Demmarrage du poele s'il était arrêté en EcoMode
        elif self.coordinator.read_api.data.is_ecomode_stop:
            await self.coordinator.control_api.start_eco_mode_heating()

        else:
            await self.coordinator.control_api.turn_on()
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Turn on thermostat by setting a target temperature."""
        raw_target_temp = kwargs[ATTR_TEMPERATURE]
        LOGGER.debug("Setting target temp to %s", raw_target_temp)
        await self.coordinator.control_api.set_temperature(raw_target_temp)
        await self.coordinator.async_request_refresh()

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return float(self.coordinator.read_api.data.temperature_read)

    @property
    def target_temperature(self) -> float:
        """Return target temperature."""
        return float(self.coordinator.read_api.data.temperature_set)

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
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
        await self.coordinator.async_request_refresh()

    @property
    def preset_mode(self) -> str | None:
        """Return the current power level."""
        power = str(self.coordinator.read_api.data.power_set)
        return power if power in POWER_PRESETS else None

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the power level (1 to 5)."""
        LOGGER.debug("Setting power to %s", preset_mode)
        await self.coordinator.control_api.set_power(int(preset_mode))
        await self.coordinator.async_request_refresh()
