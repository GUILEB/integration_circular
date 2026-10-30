"""Shared fixtures for the Circular tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.circular.api import CircularApiClient


@pytest.fixture
def client() -> CircularApiClient:
    """Return an API client with a fake Winet module storing written registers."""
    api = CircularApiClient(None, "192.168.1.23")
    api._winetclient = MagicMock()
    api._winetclient.get_registers = AsyncMock()
    api._winetclient.set_register = AsyncMock()

    async def write(_register, value):  # le poêle relit la consigne écrite
        api.data.temperature_set = value

    api._winetclient.set_register.side_effect = write
    return api


def writes(api: CircularApiClient) -> list[int]:
    """Values written to the stove registers, in order."""
    return [call.args[1] for call in api._winetclient.set_register.await_args_list]
