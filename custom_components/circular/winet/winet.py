"""Winet-Control API."""

import logging

import aiohttp

from .const import WinetRegister, WinetRegisterCategory, WinetRegisterKey
from .exceptions import WinetAPIJsonDecodeError
from .HTTPRequestExecutor import HTTPRequestBuilder, HTTPRequestExecutor
from .model import WinetGetRegisterResult

LOGGER = logging.getLogger(__package__)


class WinetAPILocal:
    """Bottom level API. Handle HTTP communication with the local Winet module."""

    def __init__(self, session: aiohttp.ClientSession | None, stove_ip: str) -> None:
        """
        Initialize Winet local API.

        Args:
            session: aiohttp ClientSession (optional)
            stove_ip: IP address of the Winet device

        """
        self._session = session
        self._stove_ip = stove_ip
        self._base_url = f"http://{stove_ip}"

        # Initialize request builder with default headers
        self._request_builder = HTTPRequestBuilder(
            self._base_url,
            self._get_default_headers(),
        )

        # Initialize request executor
        self._request_executor = HTTPRequestExecutor(session)

    @staticmethod
    def _get_default_headers() -> dict[str, str]:
        """
        Get default HTTP headers for Winet API requests.

        Returns:
            Dictionary of default headers

        """
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/141.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.6",
            "Accept-Encoding": "gzip, deflate",
        }

    async def get_registers(
        self,
        key: WinetRegisterKey,
        category: WinetRegisterCategory | None = None,
    ) -> WinetGetRegisterResult | None:
        """
        Poll registers from the Winet device.

        Args:
            key: Register key to poll
            category: Register category filter (optional)

        Returns:
            WinetGetRegisterResult object with device data

        Raises:
            WinetAPIConnectionError: On connection or HTTP errors
            WinetAPIJsonDecodeError: On JSON decode errors

        """
        data = {"key": key.value}

        if category is not None:
            data["category"] = str(category.value)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }

        request = self._request_builder.build_post_request(
            "/ajax/get-registers",
            data=data,
            headers=headers,
        )

        try:
            response = await self._request_executor.execute(request)

            if isinstance(response, dict):
                # Handle an action's result
                if "result" in response and response["result"] is False:
                    LOGGER.warning("Api result is False")

                # Update Data
                if "result" not in response:
                    return WinetGetRegisterResult(**response)
            else:
                return None

        except WinetAPIJsonDecodeError:
            msg = f"Error decoding JSON response from {request.url}"
            LOGGER.exception("%s", msg)
            raise

    async def set_register(
        self,
        registerid: WinetRegister,
        value: int,
        key: str = "002",
        memory: int = 1,
    ) -> None:
        """
        Set a register value on the Winet device.

        Args:
            registerid: Register ID to set
            value: Value to set
            key: Device key (default: "002")
            memory: Memory location (default: 1)

        Raises:
            WinetAPIConnectionError: On connection or HTTP errors
            WinetAPIJsonDecodeError: On JSON decode errors

        """
        data = {
            "key": key,
            "memory": str(memory),
            "regId": str(registerid.value),
            "value": str(value),
        }

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }

        request = self._request_builder.build_post_request(
            "/ajax/set-register",
            data=data,
            headers=headers,
        )

        try:
            response = await self._request_executor.execute(request)

            if isinstance(response, dict) and response.get("result") is not True:
                LOGGER.debug("Received: %s", response)

        except WinetAPIJsonDecodeError:
            msg = f"Error decoding JSON response from {request.url}"
            LOGGER.exception("%s", msg)
            raise
