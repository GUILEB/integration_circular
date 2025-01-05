"""Model definitions."""

from pydantic import BaseModel, Field


class WinetGetRegisterResult(BaseModel):
    """Base model for Winet stove status data."""

    params: list[list[int]] = Field(default=[])
    cat: int = Field(default=0)
    signal: int = Field(default=0)
    bk: int = Field(default=0)
    authlevel: int = Field(default=0)
    model: int = Field(default=0)
    name: str = Field(default="NO NAME")
    alr: str = Field(default="")
