#!/usr/bin/env python3
"""Model definitions."""

from pydantic import BaseModel, Field


class WinetGetRegisterResult(BaseModel):
    """Base model for Winet stove status data."""

    fwupdate: bool = Field(default=False)
    localweb: int = Field(default=0)
    model: int = Field(default=0)
    cat: int = Field(default=0)
    signal: int = Field(default=0)
    authlevel: int = Field(default=0)
    name: str = Field(default="CIRCULAR8")
    alr: str = Field(default="")
    params: list[list[int]] = Field(default_factory=list)
