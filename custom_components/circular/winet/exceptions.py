#!/usr/bin/env python3
"""Exception Management."""

import logging

LOGGER = logging.getLogger(__package__)


class APIError(Exception):
    """Exception de base pour les erreurs du client API."""

    def __init__(self, message: str | None) -> None:
        """Init ."""
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        """Return msg."""
        return f"RegisterException : {self.message}"


class WinetAPIError(APIError):
    """Erreur de connexion à l'API WINET."""


class WinetAPIConnectionError(WinetAPIError):
    """Erreur de connexion de connection HTTP de l'API WINET."""

    def __init__(self, msg: str | None = None, exc: Exception | None = None) -> None:
        super().__init__(msg)
        LOGGER.warning("Error Winet Api Connection : [%s]", msg)

        if exc:
            raise exc


class WinetAPIJsonDecodeError(WinetAPIError):
    """Erreur de décodage du JSON WINET."""

    def __init__(self, msg: str | None = None) -> None:
        super().__init__(msg)
        LOGGER.warning("Error decoding JSON: [%s]", msg)


class HAASAPIError(APIError):
    """Erreur de connexion à l'API WINET."""


class HAASAPIPollingError(HAASAPIError):
    """Erreur de décodage du JSON WINET."""

    def __init__(self, msg: str | None = None) -> None:
        super().__init__(msg)
        LOGGER.warning("Error decoding JSON: [%s]", msg)
