#!/usr/bin/env python3
"""Exception Management."""


class ApiRegisterError(Exception):
    """Classe d'exception personnalisée pour des cas spécifiques."""

    def __init__(self, message: str | None) -> None:
        """Init ."""
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        """Return msg."""
        return f"RegisterException : {self.message}"
