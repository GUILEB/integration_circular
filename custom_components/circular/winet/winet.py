#!/usr/bin/env python3
"""Winet-Control API."""

import logging
from http import HTTPStatus
from json import JSONDecodeError

import aiohttp
from aiohttp import (
    ClientConnectorError,
    ClientOSError,
    ServerDisconnectedError,
)

from .const import (
    WinetRegister,
    WinetRegisterCategory,
    WinetRegisterKey,
)
from .exceptions import WinetAPIConnectionError, WinetAPIJsonDecodeError
from .model import WinetGetRegisterResult

LOGGER = logging.getLogger(__package__)


class WinetAPILocal:
    """Bottom level API. handle http communication with the local winet module."""

    def __init__(self, session: aiohttp.ClientSession | None, stove_ip: str) -> None:
        """Initialize Winet local api."""
        self._session = session
        self._stove_ip = stove_ip

    async def get_registers(
        self,
        key: WinetRegisterKey,
        category: WinetRegisterCategory = WinetRegisterCategory.NONE,
    ) -> WinetGetRegisterResult | None:
        """Poll registers."""
        async with aiohttp.ClientSession() as session:
            url = f"http://{self._stove_ip}/ajax/get-registers"
            data = {"key": key.value}

            if category != WinetRegisterCategory.NONE:
                data["category"] = str(category.value)

            headers = {
                "Access-Control-Request-Method": "POST",
                "Host": f"{self._stove_ip}",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
                ),
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Encoding": "gzip, deflate",
                "Content-Type": "application/json; charset=utf-8",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": f"http://{self._stove_ip}",
                "Referer": f"http://{self._stove_ip}/management.html",
                "Accept-Language": "fr,fr-FR;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "Connection": "keep - alive",
            }
            LOGGER.debug("Querying %s with data=%s", url, data)
            try:
                async with session.post(url, data=data, headers=headers) as response:
                    try:
                        if response.status != HTTPStatus.OK:
                            msg = f"Response status {response.status}"
                            raise WinetAPIConnectionError(msg)
                        try:
                            json_data = await response.json(content_type=None)
                            LOGGER.debug("Received: %s", json_data)

                            # Update Data
                            if "result" not in json_data:
                                return WinetGetRegisterResult(**json_data)
                            # handle an action's result
                            if "result" in json_data and json_data["result"] is False:
                                LOGGER.warning("Api result is False")
                        except JSONDecodeError:
                            msg = f"Error decoding JSON: [{response.text}]"
                            raise WinetAPIJsonDecodeError(msg) from None

                    except ConnectionError as exc:
                        msg = "ConnectionError - host not found"
                        raise WinetAPIConnectionError(msg, exc) from None

            except (
                ServerDisconnectedError,
                ClientConnectorError,
                ClientOSError,
                ConnectionError,
                UnboundLocalError,
            ) as exc:
                msg = f"Connection failed {url}"
                raise WinetAPIConnectionError(msg, exc) from None

    async def set_register(
        self, registerid: WinetRegister, value: int, key: str = "002", memory: int = 1
    ) -> None:
        """Send raw register values !!!."""
        # data exemple: key=002&memory=1&regId=51&value=3
        async with aiohttp.ClientSession() as session:
            url = f"http://{self._stove_ip}/ajax/set-register"
            data = {
                "key": key,
                "memory": str(memory),
                "regId": str(registerid.value),
                "value": str(value),
            }
            headers = {
                "Access-Control-Request-Method": "POST",
                "Host": f"{self._stove_ip}",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
                ),
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Encoding": "gzip, deflate",
                "Content-Type": "application/json; charset=utf-8",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": f"http://{self._stove_ip}",
                "Referer": f"http://{self._stove_ip}/management.html",
            }
            LOGGER.debug("Posting to %s, data=%s", url, data)
            try:
                async with session.post(url, data=data, headers=headers) as response:
                    try:
                        if response.status != HTTPStatus.OK:
                            msg = f"Error accessing {url} - {response.status}"
                            raise WinetAPIConnectionError(msg)
                        try:
                            json_data = await response.json(content_type=None)
                            if json_data["result"] is not True:
                                LOGGER.debug("Received: %s", json_data)

                        except JSONDecodeError:
                            msg = f"Error decoding JSON: [{response.text}]"
                            raise WinetAPIJsonDecodeError(msg) from None
                    except ConnectionError as exc:
                        msg = f"Host not found Connection Error accessing {url}"
                        raise WinetAPIConnectionError(msg, exc) from None
            except (
                ServerDisconnectedError,
                ClientConnectorError,
                ClientOSError,
                ConnectionError,
                UnboundLocalError,
            ) as exc:
                msg = f"Connection failed {url}"
                raise WinetAPIConnectionError(msg, exc) from None
