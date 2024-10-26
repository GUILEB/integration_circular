"""Constants for the Circular integration."""

from __future__ import annotations
import logging
from homeassistant.const import (
    Platform,
)

# Base component constants
NAME = "Circular Integration"
DOMAIN = "circular"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "1.0.0"
ISSUE_URL = "https://github.com/docteurzoidberg/ha-circular/issues"

LOGGER = logging.getLogger(__package__)

# Icons
ICON = "mdi:fire"

# Device classes
BINARY_SENSOR_DEVICE_CLASS = "connectivity"

# Platforms
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.FAN,
]

# Configuration and options
CONF_ENABLED = "enabled"
CONF_HOST = "host"

# Defaults
DEFAULT_NAME = DOMAIN
DEFAULT_THERMOSTAT_TEMP = 21

MIN_THERMOSTAT_TEMP = 5
MAX_THERMOSTAT_TEMP = 40

MIN_FAN_SPEED = 0
MAX_FAN_SPEED = 6

MIN_POWER = 2
MAX_POWER = 5

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
