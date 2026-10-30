"""Diagnostics support for Circular."""

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import CircularConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CircularConfigEntry
) -> dict[str, Any]:
    """Return the stove state and the raw Winet registers."""
    coordinator = entry.runtime_data
    data = coordinator.read_api.data
    return {
        "entry": dict(entry.data),
        "last_update_success": coordinator.last_update_success,
        "stove": {
            "name": data.name,
            "model": data.model.get_message(),
            "signal": data.signal,
            "status": data.status.name,
            "alarms": [alarm.name for alarm in data.alarms],
            "alr": data.alr,
            "temperature_read": data.temperature_read,
            "temperature_set": data.temperature_set,
            "power_set": data.power_set,
            "fan_speed": data.fan_speed,
            "auto_regulated_temperature": data.auto_regulated_temperature,
        },
        # Registres bruts [id, valeur] reçus du module Winet
        "registers": data._rawdata.params,  # noqa: SLF001
    }
