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


def after_timeout():
    later = api_mod.time.monotonic() + ECO_PARK_TIMEOUT + 1
    return patch.object(api_mod.time, "monotonic", return_value=later)


def test_park_lowers_setpoint_by_eco_delta_once(heating):
    asyncio.run(heating.set_delta_temp(3))
    asyncio.run(heating.park_in_eco())
    asyncio.run(heating.park_in_eco())  # déjà en veille
    assert writes(heating) == [17]
    assert heating.is_eco_parked
    assert heating.eco_park_setpoints == (20, 17)
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
    assert writes(heating) == [18, 20]
    assert not heating.is_eco_parked


def test_setpoint_changed_elsewhere_lifts_park(heating):
    asyncio.run(heating.park_in_eco())
    heating.data.temperature_set = 21  # télécommande ou appli Winet
    assert not heating.is_eco_parked
    asyncio.run(heating.resume_from_eco())
    assert writes(heating) == [18]


def test_restored_park_resumes(heating):
    # Veille mémorisée avant un redémarrage de HA
    heating.data.status = S.ECO_STOP
    heating.data.temperature_set = 18
    heating.restore_eco_park(20, 18)
    assert heating.is_eco_parked
    asyncio.run(heating.resume_from_eco())
    assert writes(heating) == [20]


def test_park_ends_pending_eco_restart_first(heating):
    heating.data.status = S.ECO_STOP
    heating.data.temperature_set = 19
    asyncio.run(heating.start_eco_mode_heating())
    heating.data.status = S.WAIT_FOR_FLAME
    asyncio.run(heating.park_in_eco())
    assert writes(heating) == [21, 19, 17]
    heating.data.status = S.ECO_STOP
    asyncio.run(heating.resume_from_eco())
    assert writes(heating) == [21, 19, 17, 19]


def test_turns_off_when_eco_stop_not_reached(heating):
    asyncio.run(heating.park_in_eco())
    asyncio.run(heating.eco_park_drive())
    heating._winetclient.get_registers.assert_not_awaited()
    with after_timeout():
        asyncio.run(heating.eco_park_drive())
        asyncio.run(heating.eco_park_drive())
    heating._winetclient.get_registers.assert_awaited_once()


def test_no_turn_off_while_room_below_park_setpoint(heating):
    heating.data.temperature_read = 17
    asyncio.run(heating.park_in_eco())
    with after_timeout():
        asyncio.run(heating.eco_park_drive())
    heating._winetclient.get_registers.assert_not_awaited()


def test_no_turn_off_once_eco_stop_reached(heating):
    asyncio.run(heating.park_in_eco())
    heating.data.status = S.ECO_STOP
    asyncio.run(heating.eco_park_drive())
    heating.data.status = S.WORK  # le poêle repart seul si la pièce refroidit
    with after_timeout():
        asyncio.run(heating.eco_park_drive())
    heating._winetclient.get_registers.assert_not_awaited()


def test_turn_on_restores_setpoint_after_real_off(heating):
    asyncio.run(heating.park_in_eco())
    heating.data.status = S.OFF  # éteint ensuite par le switch Marche
    asyncio.run(heating.turn_on())
    assert writes(heating) == [18, 20]
    heating._winetclient.get_registers.assert_awaited_once()
