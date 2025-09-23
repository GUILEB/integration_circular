"""Platform for sensor integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature,EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CircularDataUpdateCoordinator
from .entity import CircularEntity
from .api import CircularApiData


@dataclass(frozen=True)
class CircularSensorRequiredKeysMixin:
    """Mixin for required keys."""

    value_fn: Callable[[CircularApiData], float | int | str | datetime | None]


@dataclass(frozen=True)
class CircularSensorEntityDescription(
    SensorEntityDescription,
    CircularSensorRequiredKeysMixin,
):
    """Describes a sensor entity."""


Circular_SENSORS: tuple[CircularSensorEntityDescription, ...] = (
    CircularSensorEntityDescription(
        key="power_set",
        icon="mdi:fire-circle",
        name="Power",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.power_set,
    ),
    CircularSensorEntityDescription(
        key="temperature_set",
        name="Set Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.temperature_set,
    ),
    CircularSensorEntityDescription(
        key="temperature_read",
        name="Read Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.temperature_read,
    ),
    CircularSensorEntityDescription(
        key="status",
        name="Status",
        value_fn=lambda data: data.status.get_message(),
    ),
    CircularSensorEntityDescription(
        key="alarms",
        name="Alarms",
        value_fn=lambda data: data.alr,
    ),
    CircularSensorEntityDescription(
        key="name",
        name="Name",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.name,
        entity_registry_enabled_default=False,
    ),
    CircularSensorEntityDescription(
        key="host",
        name="Host",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.host,
        entity_registry_enabled_default=False,
    ),
    CircularSensorEntityDescription(
        key="wifi_signal",
        name="Wifi Signal Strength",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.signal,
    ),
    CircularSensorEntityDescription(
        key="product_model",
        name="Product model",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.model.get_message(),
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Define setup entry call."""

    coordinator: CircularDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CircularSensor(coordinator=coordinator, description=description)
        for description in Circular_SENSORS
    )


class CircularSensor(CircularEntity, SensorEntity):
    """Extends CircularEntity with Sensor specific logic."""

    entity_description: CircularSensorEntityDescription

    @property
    def native_value(self) -> float | int | str | datetime | None:
        """Return the state."""
        return self.entity_description.value_fn(self.coordinator.read_api.data)
