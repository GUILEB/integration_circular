"""http-Control."""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus
from json import JSONDecodeError
from typing import Any

import aiohttp
from aiohttp import (
    ClientConnectorError,
    ClientOSError,
    ServerDisconnectedError,
)

from .exceptions import WinetAPIConnectionError, WinetAPIJsonDecodeError

LOGGER = logging.getLogger(__package__)

# Constants
DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY = 0.5


class HTTPMethod(Enum):
    """HTTP request methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


@dataclass
class HTTPRequest:
    """HTTP Request builder result."""

    url: str
    method: HTTPMethod
    headers: dict[str, str]
    data: dict[str, Any] | None = None
    timeout: int = DEFAULT_TIMEOUT


class HTTPRequestBuilder:
    """Builder for HTTP requests with default headers and configuration."""

    def __init__(
        self, base_url: str, default_headers: dict[str, str] | None = None
    ) -> None:
        """
        Initialize HTTP request builder.

        Args:
            base_url: Base URL for all requests (e.g., "http://192.168.1.100")
            default_headers: Default headers to include in all requests

        """
        self._base_url = base_url
        self._default_headers = default_headers or {}

    def build_get_request(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> HTTPRequest:
        """
        Build a GET request.

        Args:
            endpoint: API endpoint (e.g., "/ajax/get-registers")
            headers: Additional headers to merge with defaults
            timeout: Request timeout in seconds

        Returns:
            HTTPRequest object ready to execute

        """
        return HTTPRequest(
            url=f"{self._base_url}{endpoint}",
            method=HTTPMethod.GET,
            headers=self._merge_headers(headers),
            timeout=timeout,
        )

    def build_post_request(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> HTTPRequest:
        """
        Build a POST request.

        Args:
            endpoint: API endpoint (e.g., "/ajax/set-register")
            data: Request body data
            headers: Additional headers to merge with defaults
            timeout: Request timeout in seconds

        Returns:
            HTTPRequest object ready to execute

        """
        return HTTPRequest(
            url=f"{self._base_url}{endpoint}",
            method=HTTPMethod.POST,
            headers=self._merge_headers(headers),
            data=data,
            timeout=timeout,
        )

    def _merge_headers(
        self, additional_headers: dict[str, str] | None = None
    ) -> dict[str, str]:
        """
        Merge default headers with additional headers.

        Args:
            additional_headers: Headers to merge with defaults

        Returns:
            Merged headers dictionary

        """
        merged = self._default_headers.copy()
        if additional_headers:
            merged.update(additional_headers)
        return merged


class HTTPRequestExecutor:
    """Executes HTTP requests with error handling and retry logic."""

    def __init__(
        self,
        session: aiohttp.ClientSession | None,
        max_retries: int = DEFAULT_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        """
        Initialize HTTP request executor.

        Args:
            session: aiohttp ClientSession (optional, creates one if not provided)
            max_retries: Maximum number of retries on failure
            retry_delay: Delay between retries in seconds

        """
        self._session = session
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    async def execute(self, request: HTTPRequest) -> dict[str, Any] | str:
        """
        Execute HTTP request with automatic retry and error handling.

        Args:
            request: HTTPRequest object to execute

        Returns:
            Response data as dict (for JSON responses) or str (for text responses)

        Raises:
            WinetAPIConnectionError: On connection errors
            WinetAPIJsonDecodeError: On JSON decode errors

        """
        session_to_use = self._session
        created_session = False

        try:
            if session_to_use is None:
                session_to_use = aiohttp.ClientSession()
                created_session = True

            return await self._execute_with_retry(session_to_use, request)

        finally:
            if created_session and session_to_use:
                await session_to_use.close()

    async def _execute_with_retry(
        self, session: aiohttp.ClientSession, request: HTTPRequest
    ) -> dict[str, Any] | str:
        """
        Execute request with retry logic.

        Args:
            session: aiohttp ClientSession
            request: HTTPRequest object

        Returns:
            Response data

        Raises:
            WinetAPIConnectionError: If all retries fail

        """
        last_exception = None
        attempt = 0

        while attempt < self._max_retries:
            try:
                return await self._execute_single(session, request)
            except (
                TimeoutError,
                ServerDisconnectedError,
                ClientConnectorError,
                ClientOSError,
                ConnectionError,
                UnboundLocalError,
            ) as exc:
                last_exception = exc
                attempt += 1
                if attempt < self._max_retries:
                    LOGGER.debug(
                        "Request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt,
                        self._max_retries,
                        self._retry_delay,
                        str(exc),
                    )
                    await asyncio.sleep(self._retry_delay)
                else:
                    msg = (
                        f"Connection failed {request.url} after "
                        f"{self._max_retries} attempts"
                    )
                    raise WinetAPIConnectionError(msg, last_exception) from None

        msg = f"Connection failed {request.url}"
        raise WinetAPIConnectionError(msg, last_exception) from None

    async def _execute_single(
        self, session: aiohttp.ClientSession, request: HTTPRequest
    ) -> dict[str, Any] | str:
        """
        Execute a single HTTP request without retry.

        Args:
            session: aiohttp ClientSession
            request: HTTPRequest object

        Returns:
            Response data

        Raises:
            WinetAPIConnectionError: On HTTP or connection errors
            WinetAPIJsonDecodeError: On JSON decode errors

        """
        LOGGER.debug(
            "%s %s with headers=%s, data=%s",
            request.method.value,
            request.url,
            request.headers,
            request.data,
        )

        try:
            timeout = aiohttp.ClientTimeout(total=request.timeout)

            if request.method == HTTPMethod.GET:
                async with session.get(
                    request.url, headers=request.headers, timeout=timeout
                ) as response:
                    return await self._handle_response(response, request.url)
            elif request.method == HTTPMethod.POST:
                async with session.post(
                    request.url,
                    data=request.data,
                    headers=request.headers,
                    timeout=timeout,
                ) as response:
                    return await self._handle_response(response, request.url)
            else:
                msg = f"Unsupported HTTP method: {request.method}"
                raise WinetAPIConnectionError(msg)

        except WinetAPIJsonDecodeError:
            raise
        except (
            ServerDisconnectedError,
            ClientConnectorError,
            ClientOSError,
            ConnectionError,
        ) as exc:
            msg = f"Connection failed {request.url}"
            raise WinetAPIConnectionError(msg, exc) from None

    async def _handle_response(
        self, response: aiohttp.ClientResponse, url: str
    ) -> dict[str, Any] | str:
        """
        Handle HTTP response with status and content validation.

        Args:
            response: aiohttp response object
            url: Request URL (for logging)

        Returns:
            Response data as dict or str

        Raises:
            WinetAPIConnectionError: On non-200 status
            WinetAPIJsonDecodeError: On JSON decode errors

        """
        if response.status != HTTPStatus.OK:
            text = await response.text()
            msg = f"HTTP {response.status} from {url}: {text}"
            raise WinetAPIConnectionError(msg)

        try:
            json_data = await response.json(content_type=None)
        except JSONDecodeError:
            text = await response.text()
            LOGGER.debug("Response not JSON, returning as text (%d bytes)", len(text))
            return text
        else:
            LOGGER.debug("Received: %s", json_data)
            return json_data
