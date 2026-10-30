#!/usr/bin/env python3
"""Custom integration to integrate Circular (Winet Control based) Pellet Stoves."""

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CircularApiClient
from .const import (
    CONF_ENTITY,
    CONF_HOST,
    LOGGER,
    PLATFORMS,
    STARTUP_MESSAGE,
)
from .coordinator import CircularConfigEntry, CircularDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: CircularConfigEntry) -> bool:
    """Set up this integration using UI."""
    LOGGER.info(STARTUP_MESSAGE)

    host: str = str(entry.data.get(CONF_HOST))
    session = async_get_clientsession(hass)
    api = CircularApiClient(session, host)
    entity_id = entry.data.get(CONF_ENTITY)

    coordinator = CircularDataUpdateCoordinator(hass, api=api, entity_id=entity_id)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CircularConfigEntry) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: CircularConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Allow removing a stale device, but not the stove currently in use."""
    coordinator: CircularDataUpdateCoordinator | None = getattr(
        entry, "runtime_data", None
    )
    if coordinator is None:
        return True
    current = coordinator.device_info.get("identifiers", set())
    return not current & device.identifiers
