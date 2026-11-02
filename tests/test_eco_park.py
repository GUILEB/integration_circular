"""Stop heating through the stove Eco mode instead of turning it off."""

import asyncio
from unittest.mock import patch

import pytest

from custom_components.circular import api as api_mod
from custom_components.circular.api import CircularDeviceStatus as S
from custom_components.circular.const import ECO_PARK_TIMEOUT

from .conftest import writes


@pytest.fixture
def heating(client):
    client.data.status = S.WORK
    client.data.temperature_read = 19
    client.data.temperature_set = 20
    return client


def test_park_lowers_setpoint_once(heating):
    asyncio.run(heating.park_in_eco())
    asyncio.run(heating.park_in_eco())  # déjà en veille
    assert writes(heating) == [5]
    assert heating.is_eco_parked
    heating._winetclient.get_registers.assert_not_awaited()


@pytest.mark.parametrize("status", [S.OFF, S.FINAL_CLEANING, S.ALARM, S.UNKNOWN])
def test_park_ignored_when_stopped(heating, status):
    heating.data.status = status
    asyncio.run(heating.park_in_eco())
    assert writes(heating) == []


def test_resume_restores_saved_setpoint(heating):
    asyncio.run(heating.park_in_eco())
    heating.data.status = S.ECO_STOP
    asyncio.run(heating.resume_from_eco())
    asyncio.run(heating.resume_from_eco())  # plus en veille
    assert writes(heating) == [5, 20]
    assert not heating.is_eco_parked


def test_resume_after_restart_uses_read_plus_delta(heating):
    # Consigne de veille lue sur le poêle, valeur d'origine perdue
    heating.data.status = S.ECO_STOP
    heating.data.temperature_set = 5
    asyncio.run(heating.resume_from_eco())
    assert writes(heating) == [21]


def test_park_ends_pending_eco_restart_first(heating):
    heating.data.status = S.ECO_STOP
    heating.data.temperature_set = 19
    asyncio.run(heating.start_eco_mode_heating())
    heating.data.status = S.WAIT_FOR_FLAME
    asyncio.run(heating.park_in_eco())
    assert writes(heating) == [21, 19, 5]
    heating.data.status = S.ECO_STOP
    asyncio.run(heating.resume_from_eco())
    assert writes(heating) == [21, 19, 5, 19]


def test_turns_off_when_eco_stop_not_reached(heating):
    asyncio.run(heating.park_in_eco())
    asyncio.run(heating.eco_park_drive())
    heating._winetclient.get_registers.assert_not_awaited()
    later = api_mod.time.monotonic() + ECO_PARK_TIMEOUT + 1
    with patch.object(api_mod.time, "monotonic", return_value=later):
        asyncio.run(heating.eco_park_drive())
        asyncio.run(heating.eco_park_drive())
    heating._winetclient.get_registers.assert_awaited_once()


def test_no_turn_off_once_eco_stop_reached(heating):
    asyncio.run(heating.park_in_eco())
    heating.data.status = S.ECO_STOP
    asyncio.run(heating.eco_park_drive())
    later = api_mod.time.monotonic() + ECO_PARK_TIMEOUT + 1
    heating.data.status = S.WORK  # ne doit plus arriver, mais sans effet
    with patch.object(api_mod.time, "monotonic", return_value=later):
        asyncio.run(heating.eco_park_drive())
    heating._winetclient.get_registers.assert_not_awaited()
