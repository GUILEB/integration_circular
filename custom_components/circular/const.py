"""Constants for the Circular integration."""

import logging

from homeassistant.const import (
    Platform,
)

# Base component constants
NAME = "Circular Integration"
DOMAIN = "circular"
VERSION = "1.4.0"
ISSUE_URL = "https://github.com/GUILEB/integration_circular/issues"

LOGGER = logging.getLogger(__package__)

# Platforms
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

# Configuration and options
CONF_HOST = "host"
CONF_ENTITY = "entity"

UPDATE_INTERVAL = 5
# Délai maximum d'un cycle de mise à jour (plusieurs requêtes et tentatives)
UPDATE_TIMEOUT = 30
# Nombre de cycles de mise à jour avant d'abandonner une demande de mode éco (5 min)
ECO_DRIVE_MAX_CYCLES = 60
# Délai pendant lequel une nouvelle bascule marche/arrêt est refusée (secondes)
STATUS_CHANGE_TIMEOUT = 60
# Defaults
DEFAULT_NAME = "Circular 8"
DEFAULT_THERMOSTAT_TEMP = 21
DEFAULT_DELTA_ECOMODE_TEMP = 2

MIN_DELTA_ECOMODE_TEMP = 0
MAX_DELTA_ECOMODE_TEMP = 5

MIN_THERMOSTAT_TEMP = 5
MAX_THERMOSTAT_TEMP = 40

MIN_POWER = 1
MAX_POWER = 5

MIN_FAN_SPEED = 0
MAX_FAN_SPEED = 6  # 6 = (AUTO)

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
