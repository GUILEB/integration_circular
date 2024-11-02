"""Support for Circular Binary Sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CircularDataUpdateCoordinator
from .const import DOMAIN
from .entity import CircularEntity
from .api import CircularApiData


@dataclass
class CircularBinarySensorRequiredKeysMixin:
    """Mixin for required keys."""

    value_fn: Callable[[CircularApiData], bool]


@dataclass
class CircularBinarySensorEntityDescription(
    BinarySensorEntityDescription, CircularBinarySensorRequiredKeysMixin
):
    """Describes a binary sensor entity."""


CIRCULAR_BINARY_SENSORS: tuple[CircularBinarySensorEntityDescription, ...] = (
    CircularBinarySensorEntityDescription(
        key="on_off",
        name="Power on",
        icon="mdi:power",
        value_fn=lambda data: data.is_on,
    ),
    CircularBinarySensorEntityDescription(
        key="heating",
        name="Heating",
        icon="mdi:fire",
        value_fn=lambda data: data.is_heating,
    ),
    CircularBinarySensorEntityDescription(
        key="error_offline",
        name="Offline Error",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_offline,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    CircularBinarySensorEntityDescription(
        key="alarm_extractor_malfunction",
        name="Extractor malfunction Alarm",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.alarm_extractor_malfunction,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    CircularBinarySensorEntityDescription(
        key="alarm_failed_ignition",
        name="Failed ignition Alarm",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.alarm_failed_ignition,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    CircularBinarySensorEntityDescription(
        key="alarm_no_pellets",
        name="No pellets Alarm",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.alarm_no_pellets,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    CircularBinarySensorEntityDescription(
        key="alarm_open_pellet_compartment",
        name="Open pellet compartment Alarm",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.alarm_open_pellet_compartment,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    CircularBinarySensorEntityDescription(
        key="alarm_thermal_safety",
        name="Thermal safety Alarm",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.alarm_thermal_safety,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    CircularBinarySensorEntityDescription(
        key="alarm_smoke_overtemp",
        name="Smoke over temperature Alarm",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.alarm_smoke_overtemp,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    CircularBinarySensorEntityDescription(
        key="alarm_smoke_probe_failure",
        name="Smoke probe failure Alarm",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.alarm_smoke_probe_failure,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Circular On/Off Sensor."""
    coordinator: CircularDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        CircularBinarySensor(coordinator=coordinator, description=description)
        for description in CIRCULAR_BINARY_SENSORS
    )


class CircularBinarySensor(CircularEntity, BinarySensorEntity):
    """Extends CircularEntity with Binary Sensor specific logic."""

    entity_description: CircularBinarySensorEntityDescription

    @property
    def is_on(self) -> bool:
        """Use this to get the correct value."""
        return self.entity_description.value_fn(self.coordinator.read_api.data)
