"""Define switch func."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CircularDataUpdateCoordinator
from .entity import CircularEntity
from .api import CircularApiClient, CircularApiData


@dataclass()
class CircularSwitchRequiredKeysMixin:
    """Mixin for required keys."""

    on_fn: Callable[[CircularApiClient], Awaitable]
    off_fn: Callable[[CircularApiClient], Awaitable]
    value_fn: Callable[[CircularApiData], bool]


@dataclass
class CircularSwitchEntityDescription(
    SwitchEntityDescription, CircularSwitchRequiredKeysMixin
):
    """Describes a switch entity."""


CIRCULAR_SWITCHES: tuple[CircularSwitchEntityDescription, ...] = (
    CircularSwitchEntityDescription(
        key="on_off",
        name="Turn On",
        on_fn=lambda control_api: control_api.turn_on(),
        off_fn=lambda control_api: control_api.turn_off(),
        value_fn=lambda data: data.is_on,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure switch entities."""
    coordinator: CircularDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        CircularSwitch(coordinator=coordinator, description=description)
        for description in CIRCULAR_SWITCHES
    )


class CircularSwitch(CircularEntity, SwitchEntity):
    """Define an Circular Switch."""

    entity_description: CircularSwitchEntityDescription

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.entity_description.on_fn(self.coordinator.control_api)
        await self.async_update_ha_state(force_refresh=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.entity_description.off_fn(self.coordinator.control_api)
        await self.async_update_ha_state(force_refresh=True)

    @property
    def is_on(self) -> bool | None:
        """Return the on state."""
        return self.entity_description.value_fn(self.coordinator.read_api.data)
