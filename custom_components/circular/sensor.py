"""Platform for sensor integration."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CircularApiData
from .coordinator import CircularConfigEntry
from .entity import CircularEntity


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
        translation_key="power_set",
        icon="mdi:fire-circle",
        name="Power",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.power_set,
    ),
    CircularSensorEntityDescription(
        key="temperature_set",
        translation_key="temperature_set",
        name="Set Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.temperature_set,
    ),
    CircularSensorEntityDescription(
        key="temperature_read",
        translation_key="temperature_read",
        name="Read Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.temperature_read,
    ),
    CircularSensorEntityDescription(
        key="status",
        translation_key="status",
        name="Status",
        value_fn=lambda data: data.status.get_message(),
    ),
    CircularSensorEntityDescription(
        key="alarms",
        translation_key="alarms",
        name="Alarms",
        value_fn=lambda data: data.alr,
    ),
    CircularSensorEntityDescription(
        key="name",
        translation_key="name",
        name="Name",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.name,
        entity_registry_enabled_default=False,
    ),
    CircularSensorEntityDescription(
        key="host",
        translation_key="host",
        name="Host",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.host,
        entity_registry_enabled_default=False,
    ),
    CircularSensorEntityDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        name="Wifi Signal Strength",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.signal,
    ),
    CircularSensorEntityDescription(
        key="product_model",
        translation_key="product_model",
        name="Product model",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.model.get_message(),
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CircularConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Define setup entry call."""
    coordinator = entry.runtime_data
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
