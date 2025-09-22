"""Constants and Globals."""

from enum import Enum


class WinetProductModel(Enum):
    """Product models based on the web-ui."""

    UNSET = 0
    L023_1 = 1
    N100_O047 = 2
    O086 = 3
    L023_2 = 4
    U047 = 5
    PNEM00005 = 8

    def get_message(self) -> str:
        """Get a message associated with the enum."""
        messages = {
            "UNSET": "Unset",
            "L023_1": "L023 - 1",
            "N100_O047": "N100 / O047",
            "O086": "O086",
            "L023_2": "L023 - 2",
            "U047": "U047",
            "PNEM00005": "PNEM00005",
        }
        return messages.get(self.name, "UNKNOWN")


class WinetRegister(Enum):
    """Winet raw registers ids from web ui."""

    """ POLL_CATEGORY_2 """
    STATUS = 2
    ALARMS_BITS = 3
    UNKNOWN_REGISTER_2_1 = 5
    TEMPERATURE_PROBE = 6
    TEMPERATURE_INTERNE = 7
    TEMPERATURE_INTERNE_1 = 8
    TEMPERATURE_INTERNE_2 = 9
    TEMPERATURE_INTERNE_3 = 10
    UNKNOWN_REGISTER_2_2 = 37
    TEMPERATURE_SET = 50
    POWER_SET = 51

    """ POLL_CATEGORY_4 """
    UNKNOWN_REGISTER_4_1 = 60
    UNKNOWN_REGISTER_4_2 = 61
    UNKNOWN_REGISTER_4_3 = 62
    UNKNOWN_REGISTER_4_4 = 63
    UNKNOWN_REGISTER_4_5 = 64

    """ POLL_CATEGORY_6 """
    FAN_AR_SPEED = 187
    FAN_AV_SPEED = 188
    ACT_T_EXT = 191


class WinetRegisterKey(Enum):
    """'key' parameter for get-registers url."""

    SUBSCRIBE = "019"
    POLL_DATA = "020"
    CHANGE_STATUS = "022"


class WinetRegisterCategory(Enum):
    """'category' parameter for get-registers url."""

    NONE = -1
    POLL_CATEGORY_2 = 2
    POLL_CATEGORY_4 = 4
    POLL_CATEGORY_6 = 6
