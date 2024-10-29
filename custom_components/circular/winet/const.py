"""Constants and Globals."""

from enum import Enum


class WinetProductModel(Enum):  # type: ignore
    """Product models based on the web-ui"""

    UNSET = 0
    L023_1 = 1
    N100_O047 = 2
    O086 = 3
    L023_2 = 4
    U047 = 5
    PNEM00005 = 8

    def get_message(self) -> str:
        """Get a message associated with the enum."""
        if self.name == "UNSET":
            return "Unset"
        if self.name == "L023_1":
            return "L023 - 1"
        if self.name == "N100_O047":
            return "N100 / O047"
        if self.name == "O086":
            return "O086"
        if self.name == "L023_2":
            return "L023 - 2"
        if self.name == "U047":
            return "U047"
        if self.name == "80023CR01":
            return "80023CR01"
        return "UNKNOWN"


class WinetRegister(Enum):
    """Winet raw registers ids from web ui"""

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
    """'key' parameter for get-registers url"""

    POLL_DATA = "020"
    CHANGE_STATUS = "022"


class WinetRegisterCategory(Enum):
    """'category' parameter for get-registers url"""

    NONE = -1
    POLL_CATEGORY_2 = 2
    POLL_CATEGORY_4 = 4
    POLL_CATEGORY_6 = 6
