"""Restart from Eco Stop."""

import asyncio
from unittest.mock import patch

from custom_components.circular import api as api_mod
from custom_components.circular.api import CircularDeviceStatus as S
from custom_components.circular.const import ECO_DRIVE_TIMEOUT

from .conftest import writes


def eco_stop(client, read: float, target: int):
    client.data.status = S.ECO_STOP
    client.data.temperature_read = read
    client.data.temperature_set = target
    return client


def test_restart_raises_then_restores_target(client):
    eco_stop(client, 19.4, 19)
    asyncio.run(client.start_eco_mode_heating())
    asyncio.run(client.start_eco_mode_heating())  # commande répétée ignorée
    assert writes(client) == [21]
    client.data.status = S.WAIT_FOR_FLAME
    asyncio.run(client.eco_mode_drive())
    assert writes(client) == [21]
    client.data.status = S.WORK
    asyncio.run(client.eco_mode_drive())
    assert writes(client) == [21, 19]


def test_target_changed_meanwhile_is_kept(client):
    eco_stop(client, 19.0, 19)
    asyncio.run(client.start_eco_mode_heating())
    client.data.temperature_set = 23
    client.data.status = S.WORK
    asyncio.run(client.eco_mode_drive())
    assert writes(client) == [21]


def test_timeout_restores_target(client):
    eco_stop(client, 19.0, 19)
    asyncio.run(client.start_eco_mode_heating())
    later = api_mod.time.monotonic() + ECO_DRIVE_TIMEOUT + 1
    with patch.object(api_mod.time, "monotonic", return_value=later):
        asyncio.run(client.eco_mode_drive())
    assert writes(client) == [21, 19]


def test_no_raise_when_target_high_enough(client):
    eco_stop(client, 18.0, 25)
    asyncio.run(client.start_eco_mode_heating())
    assert writes(client) == []


def test_turn_off_during_restart_restores_first(client):
    eco_stop(client, 19.0, 19)
    asyncio.run(client.start_eco_mode_heating())
    asyncio.run(client.turn_off())
    assert writes(client) == [21, 19]
    client._winetclient.get_registers.assert_awaited_once()
