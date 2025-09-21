"""The Circular integration."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.circular.winet.exceptions import HAASAPIPollingError

from .api import CircularApiClient, CircularApiData
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class CircularDataUpdateCoordinator(DataUpdateCoordinator[CircularApiData]):
    """Class to manage the polling of the fireplace API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: CircularApiClient,
    ) -> None:
        """Initialize the Coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_method=self._async_update_data,
            update_interval=timedelta(seconds=1),
        )
        self._api = api

    async def _async_update_data(self) -> CircularApiData:
        try:
            await self._api.poll()
        except HAASAPIPollingError as err:
            raise err from err

        return self._api.data

    @property
    def read_api(self) -> CircularApiClient:
        """Return the Status API pointer."""
        return self._api

    @property
    def control_api(self) -> CircularApiClient:
        """Return the control API."""
        return self._api

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            manufacturer="Ravelli",
            model="Circular 8",
            name=self.read_api.data.name,
            identifiers={("Circular", f"{self.read_api.data.model}]")},
            sw_version="1.0",
            configuration_url=f"http://{self._api.stove_ip}/",
        )
