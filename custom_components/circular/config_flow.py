"""Config flow for Circular integration."""

from typing import Any

import voluptuous as vol
from aiohttp import ClientConnectionError
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import selector

from .api import CircularApiClient
from .const import CONF_ENTITY, CONF_HOST, DOMAIN, LOGGER
from .winet.exceptions import WinetAPIError

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,  # IP ou URL de l'API REST
        vol.Optional(CONF_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor"],  # on filtre uniquement les entités "sensor"
            )
        ),
    }
)


async def validate_host_input(host: str) -> str:
    """Validate the user input allows us to connect."""
    LOGGER.debug("Instantiating Circular Winet-Control API with host: [%s]", host)
    api = CircularApiClient(session=None, host=host)
    await api.update_data()
    productmodel = api.data.model.get_message()
    LOGGER.debug("Found a stove: %s", productmodel)
    # Return the serial number which will be used to calculate a unique ID for the device/sensors
    return productmodel


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Circular."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self):
        """Initialize the Config Flow Handler."""
        self._productmodel: str = ""

    # ENTRYPOINT
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        """Start the user flow (config step entrypoint)"""

        if user_input is not None:
            host = user_input[CONF_HOST]
            entity = user_input.get(CONF_ENTITY)

            try:
                self._async_abort_entries_match({CONF_HOST: host})
                self._productmodel = await validate_host_input(host)
                await self.async_set_unique_id(
                    self._productmodel, raise_on_progress=False
                )
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                return self.async_create_entry(
                    title=f"{self._productmodel} ({host})",
                    data={CONF_HOST: host, CONF_ENTITY: entity},
                )

            except (
                ConnectionError,
                ClientConnectionError,
                WinetAPIError,
                TimeoutError,
            ):
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=STEP_USER_DATA_SCHEMA,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the stove IP address or the external temperature sensor."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            host = user_input[CONF_HOST]
            try:
                productmodel = await validate_host_input(host)
            except (
                ConnectionError,
                ClientConnectionError,
                WinetAPIError,
                TimeoutError,
            ):
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # La nouvelle adresse doit désigner le même poêle
                await self.async_set_unique_id(productmodel)
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    title=f"{productmodel} ({host})",
                    data={CONF_HOST: host, CONF_ENTITY: user_input.get(CONF_ENTITY)},
                )

        return self.async_show_form(
            step_id="reconfigure",
            errors=errors,
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input or entry.data
            ),
        )
