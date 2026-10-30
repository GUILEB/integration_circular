"""Eco delta restore and diagnostics."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.number import NumberExtraStoredData

from custom_components.circular.api import CircularApiData
from custom_components.circular.diagnostics import async_get_config_entry_diagnostics
from custom_components.circular.number import EcoDeltaControlEntity
from custom_components.circular.winet.model import WinetGetRegisterResult


def restored_delta(last):
    entity = EcoDeltaControlEntity.__new__(EcoDeltaControlEntity)
    entity._attr_native_value = 2
    entity.coordinator = MagicMock()
    entity.coordinator.control_api.set_delta_temp = AsyncMock()
    entity.async_get_last_number_data = AsyncMock(return_value=last)
    with patch(
        "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_added_to_hass",
        AsyncMock(),
    ):
        asyncio.run(entity.async_added_to_hass())
    return entity


def test_delta_restored_and_applied():
    last = NumberExtraStoredData(
        native_max_value=5,
        native_min_value=0,
        native_step=1,
        native_unit_of_measurement=None,
        native_value=4.0,
    )
    entity = restored_delta(last)
    assert entity.native_value == 4
    entity.coordinator.control_api.set_delta_temp.assert_awaited_once_with(value=4)


def test_delta_default_applied_on_first_start():
    entity = restored_delta(None)
    entity.coordinator.control_api.set_delta_temp.assert_awaited_once_with(value=2)


def test_diagnostics_serializable():
    data = CircularApiData("h")
    data.update(WinetGetRegisterResult(name="NO NAME", model=8, params=[[2, 5]]))
    entry = MagicMock(data={"host": "192.168.1.23", "entity": None})
    entry.runtime_data.read_api.data = data
    entry.runtime_data.last_update_success = True
    diag = asyncio.run(async_get_config_entry_diagnostics(None, entry))
    json.dumps(diag)
    assert diag["stove"]["status"] == "WORK"
    assert diag["registers"] == [[2, 5]]
