"""Data decoding and polling."""

import asyncio
import logging
from unittest.mock import AsyncMock, patch

from custom_components.circular import api as api_mod
from custom_components.circular.api import (
    CircularApiData,
    device_name,
)
from custom_components.circular.api import (
    CircularDeviceStatus as S,
)
from custom_components.circular.winet.const import WinetRegisterKey
from custom_components.circular.winet.model import WinetGetRegisterResult


def test_device_name_fallback():
    assert device_name("NO NAME") == "Circular 8"
    assert device_name(" no name ") == "Circular 8"
    assert device_name("") == "Circular 8"
    assert device_name(None) == "Circular 8"
    assert device_name("Poêle salon") == "Poêle salon"


def test_status_decoded_only_when_present(caplog):
    data = CircularApiData("h")
    with caplog.at_level(logging.ERROR):
        data.update(WinetGetRegisterResult(name="NO NAME", model=8, params=[]))
    assert data.status == S.UNKNOWN
    assert not caplog.records
    data.update(WinetGetRegisterResult(name="NO NAME", model=8, params=[[2, 5]]))
    assert data.status == S.WORK


def polled_keys(client):
    return [call.args[0] for call in client._winetclient.get_registers.await_args_list]


def test_hardware_polled_only_when_due(client):
    client._winetclient.get_registers.side_effect = None
    client._winetclient.get_registers.return_value = WinetGetRegisterResult()
    with patch.object(api_mod.asyncio, "sleep", AsyncMock()):
        asyncio.run(client.update_data())
        asyncio.run(client.update_data())
    assert polled_keys(client).count(WinetRegisterKey.UPDATE_HARDWARE) == 1
