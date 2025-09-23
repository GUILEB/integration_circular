"""The Circular integration."""

from __future__ import annotations

from datetime import timedelta
from turtle import st
from typing import TYPE_CHECKING

import async_timeout
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.circular.winet.exceptions import HAASAPIPollingError

from .api import CircularApiClient, CircularApiData
from .const import DOMAIN, LOGGER, UPDATE_INTERVAL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class CircularDataUpdateCoordinator(DataUpdateCoordinator[CircularApiData]):
    """Class to manage the polling of the fireplace API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: CircularApiClient,
        entity_id: str | None = None,
    ) -> None:
        """Initialize the Coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_method=self._async_update_data,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self._api = api
        self.entity_id = entity_id

    async def _async_update_data(self) -> CircularApiData:
        try:
            async with async_timeout.timeout(UPDATE_INTERVAL):
                await self._api.poll()

            if self.entity_id:
                # Obtenir la valeur actuelle de l'entité
                state = self.hass.states.get(self.entity_id)
                if state:
                    entity_value = state.state
                    try:
                        # Vérifier si la valeur est numérique
                        if entity_value not in ('unknown', 'unavailable'):
                            float_value = float(entity_value)
                            await self._api.set_temperature_ask_by_external_entity(
                                float_value
                            )
                    except ValueError:
                        LOGGER.warning(
                            "Invalid temperature value from entity %s: %s",
                            self.entity_id,
                            entity_value
                        )

            return self._api.data
        except HAASAPIPollingError as err:
            raise err from err

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
