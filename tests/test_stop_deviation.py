"""Stop Déviation: the stove target follows the external entity."""

import asyncio

import pytest

from custom_components.circular.api import CircularDeviceStatus as S

from .conftest import writes


def follow(client, value: float) -> None:
    asyncio.run(client.set_temperature_ask_by_external_entity(value))


@pytest.fixture
def regulated(client):
    client.data.auto_regulated_temperature = True
    client.data.status = S.WORK
    client.data.temperature_read = 19.0
    client.data.temperature_set = 18
    return client


def test_disabled_does_nothing(regulated):
    regulated.data.auto_regulated_temperature = False
    follow(regulated, 21.0)
    assert writes(regulated) == []


def test_aligns_rounded_value(regulated):
    follow(regulated, 20.6)
    follow(regulated, 21.4)  # même consigne entière : pas de réécriture
    assert writes(regulated) == [21]


@pytest.mark.parametrize("status", [S.ECO_STOP, S.WAIT_FOR_FLAME, S.STABLE_FLAME])
def test_aligns_in_any_running_status(regulated, status):
    regulated.data.status = status
    follow(regulated, 21.0)
    assert writes(regulated) == [21]


@pytest.mark.parametrize("status", [S.OFF, S.FINAL_CLEANING, S.ALARM, S.UNKNOWN])
def test_ignored_when_stopped(regulated, status):
    regulated.data.status = status
    follow(regulated, 21.0)
    assert writes(regulated) == []


def test_outside_change_is_corrected_again(regulated):
    follow(regulated, 21.0)
    regulated.data.temperature_set = 20  # télécommande ou appli Winet
    follow(regulated, 21.0)
    assert writes(regulated) == [21, 21]


def test_eco_restart_is_not_overridden(regulated):
    regulated.data.status = S.ECO_STOP
    regulated.data.temperature_set = 19
    asyncio.run(regulated.start_eco_mode_heating())
    follow(regulated, 19.0)
    assert writes(regulated) == [21]
    regulated.data.status = S.WORK
    asyncio.run(regulated.eco_mode_drive())
    follow(regulated, 19.0)  # consigne déjà restaurée à 19
    assert writes(regulated) == [21, 19]


def test_enabled_by_default(client):
    assert client.data.auto_regulated_temperature is True


@pytest.mark.parametrize(("value", "expected"), [(20.5, 21), (21.5, 22), (20.49, 20)])
def test_half_rounds_up(regulated, value, expected):
    follow(regulated, value)
    assert writes(regulated) == [expected]


@pytest.mark.parametrize(("value", "bound"), [(3.0, 5), (45.0, 40)])
def test_out_of_range_written_once(regulated, value, bound):
    follow(regulated, value)
    follow(regulated, value)  # déjà à la borne : pas de réécriture en boucle
    assert writes(regulated) == [bound]
