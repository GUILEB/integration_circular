"""API Client."""

from enum import Enum

import aiohttp

from custom_components.circular.winet.const import (
    WinetProductModel,
    WinetRegister,
    WinetRegisterCategory,
    WinetRegisterKey,
)
from custom_components.circular.winet.exceptions import WinetAPIError
from custom_components.circular.winet.model import WinetGetRegisterResult
from custom_components.circular.winet.winet import WinetAPILocal

from .const import (
    LOGGER,
    MAX_DELTA_ECOMODE_TEMP,
    MAX_FAN_SPEED,
    MAX_POWER,
    MAX_THERMOSTAT_TEMP,
    MIN_DELTA_ECOMODE_TEMP,
    MIN_FAN_SPEED,
    MIN_POWER,
    MIN_THERMOSTAT_TEMP,
)


def clamp(value: float, valuemin: float, valuemax: float) -> float | int:
    """Clamp value between min and max."""
    return max(valuemin, min(value, valuemax))


class CircularDeviceStatus(Enum):
    """Status Class based on the web-ui."""

    OFF = 0
    WAIT_FOR_FLAME = 1
    POWER_ON = 2
    UNKNOWN_1 = 3
    STABLE_FLAME = 4
    WORK = 5
    BRAZIER_CLEANING = 6
    FINAL_CLEANING = 7
    ECO_STOP = 8
    MODULA = 9
    UNKNOWN_2 = 10
    ALARM = 11
    UNKNOWN = -1

    def get_message(self) -> str:
        """Get a message associated with the enum."""
        if self.name == "OFF":
            return "Off"
        if self.name == "WAIT_FOR_FLAME":
            return "Waiting flame"
        if self.name == "POWER_ON":
            return "Power on"
        if self.name == "UNKNOWN_1":
            return "Unknown"
        if self.name == "STABLE_FLAME":
            return "Stable Flame"
        if self.name == "WORK":
            return "Working"
        if self.name == "BRAZIER_CLEANING":
            return "Brazzier cleaning"
        if self.name == "FINAL_CLEANING":
            return "Final cleaning"
        if self.name == "ECO_STOP":
            return "Eco_Stop"
        if self.name == "ALARM":
            return "Alarm"
        if self.name == "MODULA":
            return "Modula"
        if self.name == "UNKNOWN":
            return "Unknown"
        return f"Unknown status{self.name}"


class CircularDeviceAlarm(Enum):
    """Winet alarm bytes."""

    NO_ALARM = 0
    BLAKC_OUT = 1
    SMOKE_PROBE_FAILURE = 2
    SMOKE_OVERTEMPERATURE = 3
    EXTRACTOR_MALFUNCTION = 4
    FAILED_IGNITION = 5
    NO_PELLETS = 6
    OPEN_PELLET_COMPARTMENT = 7
    LACK_OF_PRESSURE = 8
    EXTRACTOR_TURN = 12
    TARIERE_PHASE = 14
    TARIERE_TRIAC = 15
    CLEANER_FAILURE = 19
    TARIERE_ALARM = 25

    THERMAL_SAFETY = 9  # ???

    def get_message(self) -> str:
        """Get a message associated with the enum."""
        if self.name == "SMOKE_PROBE_FAILURE":
            return "Smoke probe failure !"
        if self.name == "SMOKE_OVERTEMPERATURE":
            return "Smoke over-temperature !"
        if self.name == "EXTRACTOR_MALFUNCTION":
            return "Extractor malfunction !"
        if self.name == "FAILED_IGNITION":
            return "Failed ignition"
        if self.name == "NO_PELLETS":
            return "No pellets"
        if self.name == "LACK_OF_PRESSURE":
            return "Lacks of pressure !"
        if self.name == "THERMAL_SAFETY":
            return "Thermal safety !"
        if self.name == "OPEN_PELLET_COMPARTMENT":
            return "Pellet compartment is open !"
        return "UNKNOWN"


class CircularApiData:
    """Usable api data for the home assistant integration."""

    def __init__(self, host: str):
        """Init unset data."""
        self._rawdata = WinetGetRegisterResult()
        self.signal = self._rawdata.signal
        self.name = self._rawdata.name
        self.alr = self._rawdata.alr
        self.host = host
        self.model = WinetProductModel(self._rawdata.model)
        self.status = CircularDeviceStatus.UNKNOWN
        self.alarms = []
        self.temperature_read = 0.0
        self.temperature_set = 0.0
        self.power_set = 0
        self.fan_speed = 0
        self._delta_ecomode = 0.0
        self._delta_ecomode_ask = False
        self.temperature_ask_by_external_entity = 0.0

    def update(
        self,
        newdata: WinetGetRegisterResult,
        category: WinetRegisterCategory = WinetRegisterCategory.NONE,
    ) -> None:
        """Update or add data to rawdata."""
        # convert actual data to dict
        newparamsdict = {}
        for oldparam in self._rawdata.params:
            key = oldparam[0]
            value = oldparam[1]
            newparamsdict[key] = value

        # overwrite or add new key/values
        for newparam in newdata.params:
            key = newparam[0]
            value = newparam[1]
            newparamsdict[key] = value

        # convert back to list of int,int
        newparams = []
        for key, val in newparamsdict.items():
            newparams.append([key, val])

        # update class data
        self._rawdata.params = newparams
        self._rawdata.cat = newdata.cat
        self._rawdata.signal = newdata.signal
        self._rawdata.alr = newdata.alr
        self._rawdata.authlevel = newdata.authlevel
        self._rawdata.model = newdata.model
        self._rawdata.name = newdata.name

        if category == WinetRegisterCategory.POLL_CATEGORY_2:
            self._decode_temperature_read()
            self._decode_temperature_set()
            self._decode_power_set()
            self._decode_status()

        if category == WinetRegisterCategory.POLL_CATEGORY_6:
            self._decode_alarms()
            self._decode_fan_speed()

        if category != WinetRegisterCategory.NONE:
            self.signal = newdata.signal
            self.alr = newdata.alr
            self.name = newdata.name
            self.model = WinetProductModel(newdata.model)

    def _get_register_value(self, registerid: WinetRegister) -> int:
        """Parse all data (memory banks?) to find a register's value."""
        for param in self._rawdata.params:
            if param[0] == registerid.value:
                return param[1]
        LOGGER.error(f"RegisterId {registerid.value} not found in data")
        LOGGER.debug(self._rawdata)
        msg = "RegisterId not found in data"
        raise WinetAPIError(msg)

    def _decode_status(self) -> None:
        """Decode status register."""
        status = self._get_register_value(WinetRegister.STATUS)
        self.status = CircularDeviceStatus(status)

    def _decode_alarms(self) -> None:
        """Decode alarm register byte into individual alarms."""
        alarmsbyte = self._get_register_value(WinetRegister.ALARMS_BITS)
        LOGGER.debug(f"Alarm byte value is {alarmsbyte}")
        if alarmsbyte < 0:
            LOGGER.error("Cannot decode alarms")
            return
        self.alarms.clear()
        self.alarms.append(CircularDeviceAlarm(alarmsbyte))

    def _decode_temperature_read(self) -> None:
        """Update Temperature read register."""
        param = self._get_register_value(WinetRegister.TEMPERATURE_PROBE)
        self.temperature_read = param

    def _decode_temperature_set(self) -> None:
        """Update Temperature set register."""
        param = self._get_register_value(WinetRegister.TEMPERATURE_SET)
        self.temperature_set = param

    def _decode_power_set(self) -> None:
        """Power set."""
        self.power_set = self._get_register_value(WinetRegister.POWER_SET)

    def _decode_fan_speed(self) -> None:
        """Room vent fan speed."""
        self.fan_speed = self._get_register_value(WinetRegister.FAN_AR_SPEED)

    @property
    def is_on(self) -> bool:
        """Is stove on ?."""
        return self.status not in [
            CircularDeviceStatus.OFF,
        ]

    @property
    def is_heating(self) -> bool:
        """Is heating ?."""
        return self.status in [CircularDeviceStatus.WORK]

    @property
    def is_ecomode_stop(self) -> bool:
        """Is heating ?."""
        return self.status in [CircularDeviceStatus.ECO_STOP]

    @property
    def error_offline(self) -> bool:
        """Is offline ?."""
        return self.status in [
            CircularDeviceStatus.ALARM,
        ]
        return self.status == CircularDeviceStatus.UNKNOWN

    @property
    def alarm_extractor_malfunction(self) -> bool:
        """Alarm bit for extractor malfunction is set ?."""
        return CircularDeviceAlarm.EXTRACTOR_MALFUNCTION in self.alarms

    @property
    def alarm_failed_ignition(self) -> bool:
        """Alarm bit for failed ignition is set ?."""
        return CircularDeviceAlarm.FAILED_IGNITION in self.alarms

    @property
    def alarm_lack_of_pressure(self) -> bool:
        """.alarm bit for lack of pressure is set ?."""
        return CircularDeviceAlarm.LACK_OF_PRESSURE in self.alarms

    @property
    def alarm_no_pellets(self) -> bool:
        """Alarm bit for no pellets is set ?."""
        return CircularDeviceAlarm.NO_PELLETS in self.alarms

    @property
    def alarm_open_pellet_compartment(self) -> bool:
        """Alarm bit for open pellet compartment is set ?."""
        return CircularDeviceAlarm.OPEN_PELLET_COMPARTMENT in self.alarms

    @property
    def alarm_smoke_overtemp(self) -> bool:
        """Alarm bit for smoke temperature is set ?."""
        return CircularDeviceAlarm.SMOKE_OVERTEMPERATURE in self.alarms

    @property
    def alarm_smoke_probe_failure(self) -> bool:
        """Alarm bit for smoke probe failure is set?."""
        return CircularDeviceAlarm.SMOKE_PROBE_FAILURE in self.alarms

    @property
    def alarm_thermal_safety(self) -> bool:
        """Alarm bit for thermal safety is set?."""
        return CircularDeviceAlarm.THERMAL_SAFETY in self.alarms


class CircularApiClient:
    """Circular api client. use winet control api polling as backend."""

    def __init__(self, session: aiohttp.ClientSession | None, host: str) -> None:
        """Init."""
        self._host = host
        self._session = session
        self._data = CircularApiData(host)
        self._winetclient = WinetAPILocal(session, host)
        self.stove_ip = host
        self.delta_ecomode_ask = False

    @property
    def data(self) -> CircularApiData:
        """Returns decoded data from api raw data."""
        if self._data.name == "unset":
            LOGGER.warning("Returning uninitialized data")
        return self._data

    async def set_fan_speed(self, value: float) -> None:
        """Set air room vent fan speed."""
        # ui min value is 0 (OFF) to 5 (HIGH) , 6 = (AUTO)
        value = clamp(int(value), MIN_FAN_SPEED, MAX_FAN_SPEED)
        LOGGER.debug(f"Set fan speed to {value}")
        await self._winetclient.set_register(WinetRegister.FAN_AR_SPEED, int(value))

    async def set_power(self, value: float) -> None:
        """Send set register with key=002&memory=1&regId=51&value={value} ."""
        # ui's min value is 1 and maximum is 5
        value = clamp(int(value), MIN_POWER, MAX_POWER)
        LOGGER.debug(f"Set power to {value}")
        await self._winetclient.set_register(WinetRegister.POWER_SET, int(value))

    async def set_delta_temp(self, value: float) -> None:
        """Set Add temp for wake up stove with eco climat mode ."""
        # ui's min value is 1 and maximum is 5
        value = clamp(int(value), MIN_DELTA_ECOMODE_TEMP, MAX_DELTA_ECOMODE_TEMP)
        LOGGER.debug(f"Set Delta Eco Mode to {value}")
        self._delta_ecomode = value

    async def set_temperature(self, value: float) -> None:
        """Send set register with key=002&memory=1&regId=50&value={value} ."""
        # self defined min/max values
        value = clamp(
            float(value), float(MIN_THERMOSTAT_TEMP), float(MAX_THERMOSTAT_TEMP)
        )
        LOGGER.warning(f"Set temperature to {value}")
        await self._winetclient.set_register(WinetRegister.TEMPERATURE_SET, int(value))

    async def set_temperature_with_delta(self, value: float) -> None:
        """Send set register with key=002&memory=1&regId=50&value={value} ."""
        # self defined min/max values
        value = min(value + self._delta_ecomode, value)
        self.delta_ecomode_ask = True
        value = clamp(
            float(value), float(MIN_THERMOSTAT_TEMP), float(MAX_THERMOSTAT_TEMP)
        )
        LOGGER.warning(f"Set temperature with delta to {value}")
        await self._winetclient.set_register(WinetRegister.TEMPERATURE_SET, int(value))

    async def set_temperature_without_delta(self, value: float) -> None:
        """Send set register with key=002&memory=1&regId=50&value={value} ."""
        # Stop ecomode with real target temperature
        if self.data.is_heating and self.delta_ecomode_ask:
            value = max(value - self._delta_ecomode, value)
            self.delta_ecomode_ask = False
            await self.set_temperature(value)

    async def turn_on(self) -> None:
        """Turn on the stove."""
        if self.data.status != CircularDeviceStatus.OFF:
            return
        LOGGER.debug("Turn stove on")
        await self._winetclient.get_registers(WinetRegisterKey.CHANGE_STATUS)

    async def turn_off(self) -> None:
        """Turn on the stove."""
        if self.data.status == CircularDeviceStatus.OFF:
            return
        LOGGER.debug("Turn stove off")
        await self._winetclient.get_registers(WinetRegisterKey.CHANGE_STATUS)

    async def set_temperature_ask_by_external_entity(self, value: float) -> None:
        """Set temperature ask by external entity."""
        if not self.delta_ecomode_ask and value != self.data.temperature_set:
            await self.set_temperature(value)
            self.data.temperature_ask_by_external_entity = value

    async def update_data(self) -> None:
        """Update data  the Winet module locally."""
        # Update Alarm Temp,Power

        result = await self._winetclient.get_registers(WinetRegisterKey.SUBSCRIBE)
        if result is not None:
            self._data.update(newdata=result, category=WinetRegisterCategory.NONE)

        result = await self._winetclient.get_registers(
            WinetRegisterKey.POLL_DATA, WinetRegisterCategory.POLL_CATEGORY_2
        )
        if result is not None:
            self._data.update(
                newdata=result, category=WinetRegisterCategory.POLL_CATEGORY_2
            )
        # Update Configuration : Fan
        result = await self._winetclient.get_registers(
            WinetRegisterKey.POLL_DATA, WinetRegisterCategory.POLL_CATEGORY_4
        )
        if result is not None:
            self._data.update(
                newdata=result, category=WinetRegisterCategory.POLL_CATEGORY_4
            )
        # Update Alarm
        result = await self._winetclient.get_registers(
            WinetRegisterKey.POLL_DATA, WinetRegisterCategory.POLL_CATEGORY_6
        )
        if result is not None:
            self._data.update(
                newdata=result, category=WinetRegisterCategory.POLL_CATEGORY_6
            )
        # Take account  EcoMode
        await self.set_temperature_without_delta(self._data.temperature_set)
