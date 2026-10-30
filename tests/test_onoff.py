"""On/off toggle protection."""

import asyncio
from unittest.mock import patch

from custom_components.circular import api as api_mod
from custom_components.circular.api import CircularDeviceStatus as S


def test_double_turn_on_sends_one_toggle(client):
    client.data.status = S.OFF
    asyncio.run(client.turn_on())
    asyncio.run(client.turn_on())
    assert client._winetclient.get_registers.await_count == 1


def test_turn_on_ignored_when_already_on(client):
    client.data.status = S.WAIT_FOR_FLAME
    asyncio.run(client.turn_on())
    client._winetclient.get_registers.assert_not_awaited()


def test_turn_off_not_repeated_during_final_cleaning(client):
    client.data.status = S.WORK
    asyncio.run(client.turn_off())
    asyncio.run(client.turn_off())  # statut pas encore rafraîchi
    client.data.status = S.FINAL_CLEANING
    asyncio.run(client.turn_off())
    assert client._winetclient.get_registers.await_count == 1


def test_new_toggle_allowed_after_timeout(client):
    client.data.status = S.OFF
    asyncio.run(client.turn_on())
    with patch.object(api_mod.time, "monotonic", return_value=1e12):
        asyncio.run(client.turn_on())
    assert client._winetclient.get_registers.await_count == 2
