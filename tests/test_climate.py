"""Thermostat entity."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate.const import HVACAction, HVACMode

from custom_components.circular.api import CircularDeviceStatus as S
from custom_components.circular.climate import CircularClimate


@pytest.fixture
def climate(client):
    entity = CircularClimate.__new__(CircularClimate)
    entity.coordinator = MagicMock(read_api=client, control_api=client)
    entity.coordinator.async_request_refresh = AsyncMock()
    return entity


@pytest.mark.parametrize(
    ("status", "mode", "action"),
    [
        (S.OFF, HVACMode.OFF, HVACAction.OFF),
        (S.WAIT_FOR_FLAME, HVACMode.HEAT, HVACAction.PREHEATING),
        (S.WORK, HVACMode.HEAT, HVACAction.HEATING),
        (S.ECO_STOP, HVACMode.HEAT, HVACAction.IDLE),
        (S.FINAL_CLEANING, HVACMode.OFF, HVACAction.OFF),
        (S.ALARM, HVACMode.OFF, HVACAction.OFF),
    ],
)
def test_mode_and_action(climate, client, status, mode, action):
    client.data.status = status
    assert (climate.hvac_mode, climate.hvac_action) == (mode, action)


def test_set_hvac_mode_calls_stove(climate, client):
    client.turn_on = AsyncMock()
    client.turn_off = AsyncMock()
    client.start_eco_mode_heating = AsyncMock()
    client.data.status = S.OFF
    asyncio.run(climate.async_set_hvac_mode(HVACMode.HEAT))
    client.turn_on.assert_awaited_once()
    client.data.status = S.ECO_STOP
    asyncio.run(climate.async_set_hvac_mode(HVACMode.HEAT))
    client.start_eco_mode_heating.assert_awaited_once()
    asyncio.run(climate.async_set_hvac_mode(HVACMode.OFF))
    client.turn_off.assert_awaited_once()
    assert climate.coordinator.async_request_refresh.await_count == 3


def test_power_preset(climate, client):
    client.data.power_set = 3
    assert climate.preset_mode == "3"
    asyncio.run(climate.async_set_preset_mode("5"))
    assert client._winetclient.set_register.await_args.args[1] == 5
