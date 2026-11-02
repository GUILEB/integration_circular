"""Thermostat entity."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate.const import HVACAction, HVACMode

from custom_components.circular.api import CircularDeviceStatus as S
from custom_components.circular.climate import CircularClimate

from .conftest import writes


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


@pytest.mark.parametrize(
    ("status", "action"),
    [(S.WORK, HVACAction.HEATING), (S.ECO_STOP, HVACAction.IDLE)],
)
def test_eco_parked_reported_off(climate, client, status, action):
    client.data.status = status
    client.data.temperature_set = 10
    assert (climate.hvac_mode, climate.hvac_action) == (HVACMode.OFF, action)
    for target in (9, 20):  # une consigne basse ordinaire n'est pas une veille
        client.data.temperature_set = target
        assert climate.hvac_mode == HVACMode.HEAT


def test_set_hvac_mode_calls_stove(climate, client):
    client.turn_on = AsyncMock()
    client.park_in_eco = AsyncMock()
    client.resume_from_eco = AsyncMock()
    client.start_eco_mode_heating = AsyncMock()
    client.data.status = S.OFF
    asyncio.run(climate.async_set_hvac_mode(HVACMode.HEAT))
    client.turn_on.assert_awaited_once()
    client.data.status = S.ECO_STOP
    asyncio.run(climate.async_set_hvac_mode(HVACMode.HEAT))
    client.start_eco_mode_heating.assert_awaited_once()
    asyncio.run(climate.async_set_hvac_mode(HVACMode.OFF))
    client.park_in_eco.assert_awaited_once()
    assert client.resume_from_eco.await_count == 2
    assert climate.coordinator.async_request_refresh.await_count == 3


def test_power_preset(climate, client):
    client.data.power_set = 3
    assert climate.preset_mode == "3"
    asyncio.run(climate.async_set_preset_mode("5"))
    assert client._winetclient.set_register.await_args.args[1] == 5


def test_off_then_heat_parks_and_restarts_from_eco(climate, client):
    client.data.status = S.WORK
    client.data.temperature_read = 19
    client.data.temperature_set = 20
    asyncio.run(climate.async_set_hvac_mode(HVACMode.OFF))
    client.data.status = S.ECO_STOP
    asyncio.run(climate.async_set_hvac_mode(HVACMode.HEAT))
    # Consigne rétablie puis relevée pour relancer, restaurée une fois en chauffe
    assert writes(client) == [10, 20, 21]
    client.data.status = S.WORK
    asyncio.run(client.eco_mode_drive())
    assert writes(client) == [10, 20, 21, 20]
    client._winetclient.get_registers.assert_not_awaited()


def test_off_really_turns_off_when_eco_park_disabled(climate, client):
    client.data.status = S.WORK
    client.data.temperature_set = 20
    asyncio.run(client.eco_park_off())
    asyncio.run(climate.async_set_hvac_mode(HVACMode.OFF))
    assert writes(client) == []
    client._winetclient.get_registers.assert_awaited_once()
