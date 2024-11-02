"""API Client."""

import asyncio
from asyncio import Task
from enum import Enum
import time
import aiohttp
from aiohttp import ClientOSError

from custom_components.circular.winet.model import WinetGetRegisterResult
from custom_components.circular.winet.winet import WinetAPILocal
from custom_components.circular.winet.const import (
    WinetRegister,
    WinetRegisterKey,
    WinetRegisterCategory,
    WinetProductModel,
)

from .const import LOGGER


def clamp(value, valuemin, valuemax):
    """clamp value between min and max"""
    return valuemin if value < valuemin else valuemax if value > valuemax else value


class CircularDeviceStatus(Enum):  # type: ignore
    """Status Class based on the web-ui"""

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


class CircularDeviceAlarm(Enum):  # type: ignore
    """Winet alarm bytes"""

    NO_ALARM = 0
    BLAKC_OUT = 1
    SMOKE_PROBE_FAILURE = 2
    SMOKE_OVERTEMPERATURE = 3
    EXTRACTOR_MALFUNCTION = 4
    FAILED_IGNITION = 5
    NO_PELLETS = 6
    THERMAL_SAFETY = 7
    LACK_OF_PRESSURE = 8
    EXTRACTOR_TURN = 12
    TARIERE_PHASE = 14
    TARIERE_TRIAC = 15
    CLEANER_FAILURE = 19
    TARIERE_ALARM = 25

    OPEN_PELLET_COMPARTMENT = 7  # ???

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
    """Usable api data for the home assistant integration"""

    def __init__(self, host: str):
        """init unset data"""
        self._rawdata = WinetGetRegisterResult()
        self.signal = self._rawdata.signal
        self.name = self._rawdata.name
        self.alr = self._rawdata.alr
        self.host = host
        self.model = WinetProductModel(self._rawdata.model).get_message()
        self.status = CircularDeviceStatus.UNKNOWN
        self.alarms = []
        self.temperature_read = 0.0
        self.temperature_set = 0.0
        self.power_set = 0
        self.fan_speed = 0

    def update(self, newdata: WinetGetRegisterResult, decode: bool = True):
        """Update or add data to rawdata"""

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
        self._rawdata.bk = newdata.bk
        self._rawdata.authLevel = newdata.authLevel
        self._rawdata.model = newdata.model
        self._rawdata.name = newdata.name

        if decode:
            self.signal = newdata.signal
            self.alr = newdata.alr
            self.name = newdata.name
            self.model = WinetProductModel(newdata.model)
            self._decode_status()
            self._decode_alarms()
            self._decode_temperature_read()
            self._decode_temperature_set()
            self._decode_power_set()
            self._decode_fan_speed()

    def _get_register_value(self, registerid: WinetRegister) -> int:
        """Parse all data (memory banks?) to find a register's value"""
        for param in self._rawdata.params:
            if param[0] == registerid.value:
                return param[1]
        LOGGER.error(f"RegisterId {registerid.value} not found in data")
        LOGGER.debug(self._rawdata)
        raise Exception("RegisterId not found in data")

    def _decode_status(self) -> None:
        """Decode status register"""
        status = self._get_register_value(WinetRegister.STATUS)
        if status in (1, 2, 3, 4):
            self.status = CircularDeviceStatus.WAIT_FOR_FLAME
        else:
            self.status = CircularDeviceStatus(status)

    def _decode_alarms(self) -> None:
        """Decode alarm register byte into individual alarms"""
        alarmsbyte = self._get_register_value(WinetRegister.ALARMS_BITS)
        LOGGER.debug(f"Alarm byte value is {alarmsbyte}")
        if alarmsbyte < 0:
            LOGGER.error("Cannot decode alarms")
            return
        self.alarms.clear()
        self.alarms.append(CircularDeviceAlarm(alarmsbyte))

    def _decode_temperature_read(self) -> None:
        """
        Decodes Temperature read register
        reg. value is two time the temperature in celsius
        """
        param = self._get_register_value(WinetRegister.TEMPERATURE_PROBE)
        self.temperature_read = param

    def _decode_temperature_set(self) -> None:
        """
        Decodes Temperature set register
        reg. value is two time the temperature in celsius
        """
        param = self._get_register_value(WinetRegister.TEMPERATURE_SET)
        self.temperature_set = param

    def _decode_power_set(self) -> None:
        """Power set"""
        self.power_set = self._get_register_value(WinetRegister.POWER_SET)

    def _decode_fan_speed(self) -> None:
        """Room vent fan speed"""
        self.fan_speed = self._get_register_value(WinetRegister.FAN_AR_SPEED)

    @property
    def is_on(self) -> bool:
        """Is stove on ?"""
        return self.status not in [
            CircularDeviceStatus.OFF,
        ]

    @property
    def is_heating(self) -> bool:
        """Is heating ?"""
        return self.status in [CircularDeviceStatus.WORK]

    @property
    def error_offline(self) -> bool:
        """Is offline ?"""
        return self.status in [
            CircularDeviceStatus.ALARM,
        ]
        return self.status == CircularDeviceStatus.UNKNOWN

    @property
    def alarm_extractor_malfunction(self) -> bool:
        """Alarm bit for extractor malfunction is set ?"""
        return CircularDeviceAlarm.EXTRACTOR_MALFUNCTION in self.alarms

    @property
    def alarm_failed_ignition(self) -> bool:
        """Alarm bit for failed ignition is set ?"""
        return CircularDeviceAlarm.FAILED_IGNITION in self.alarms

    @property
    def alarm_lack_of_pressure(self) -> bool:
        """.alarm bit for lack of pressure is set ?"""
        return CircularDeviceAlarm.LACK_OF_PRESSURE in self.alarms

    @property
    def alarm_no_pellets(self) -> bool:
        """Alarm bit for no pellets is set ?"""
        return CircularDeviceAlarm.NO_PELLETS in self.alarms

    @property
    def alarm_open_pellet_compartment(self) -> bool:
        """Alarm bit for open pellet compartment is set ?"""
        return CircularDeviceAlarm.OPEN_PELLET_COMPARTMENT in self.alarms

    @property
    def alarm_smoke_overtemp(self) -> bool:
        """Alarm bit for smoke temperature is set ?"""
        return CircularDeviceAlarm.SMOKE_OVERTEMPERATURE in self.alarms

    @property
    def alarm_smoke_probe_failure(self) -> bool:
        """Alarm bit for smoke probe failure is set?"""
        return CircularDeviceAlarm.SMOKE_PROBE_FAILURE in self.alarms

    @property
    def alarm_thermal_safety(self) -> bool:
        """Alarm bit for thermal safety is set?"""
        return CircularDeviceAlarm.THERMAL_SAFETY in self.alarms


class CircularApiClient:
    """Circular api client. use winet control api polling as backend"""

    failed_poll_attempts = 0
    is_sending = False
    is_polling_in_background = False
    stove_ip = ""

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        """init"""
        self._host = host
        self._session = session
        self._data = CircularApiData(host)
        self._winetclient = WinetAPILocal(session, host)
        self._should_poll_in_background = False
        self._bg_task: Task | None = None

        self.stove_ip = host
        self.is_polling_in_background = False
        self.is_sending = False
        self.failed_poll_attempts = 0

    @property
    def data(self) -> CircularApiData:
        """Returns decoded data from api raw data"""
        if self._data.name == "unset":
            LOGGER.warning("Returning uninitialized poll data")
        return self._data

    def log_status(self) -> None:
        """Log a status message."""
        LOGGER.info(
            "CircularApiClient Status\n\tis_sending\t[%s]\n\tfailed_polls\t[%d]\n\tBG_Running\t[%s]\n\tBG_ShouldRun\t[%s]",
            self.is_sending,
            self.failed_poll_attempts,
            self.is_polling_in_background,
            self._should_poll_in_background,
        )

    async def start_background_polling(self, minimum_wait_in_seconds: int = 5) -> None:
        """Start an ensure-future background polling loop."""
        if self.is_sending:
            LOGGER.info(
                "!! Suppressing start_background_polling -- sending mode engaged"
            )
            return

        if not self._should_poll_in_background:
            self._should_poll_in_background = True
            # asyncio.ensure_future(self.__background_poll(minimum_wait_in_seconds))
            LOGGER.info("!!  start_background_polling !!")

            self._bg_task = asyncio.create_task(
                self.__background_poll(minimum_wait_in_seconds),
                name="background_polling",
            )

    def stop_background_polling(self) -> bool:
        """Stop background polling - return whether it had been polling."""
        self._should_poll_in_background = False
        was_running = False
        if self._bg_task:
            if not self._bg_task.cancelled():
                was_running = True
                self._bg_task.cancel()
                LOGGER.info("Stopping background task to issue a command")

        return was_running

    async def __background_poll(self, minimum_wait_in_seconds: int = 5) -> None:
        """Perform a polling loop."""
        LOGGER.debug("__background_poll:: Function Called")

        self.failed_poll_attempts = 0

        self.is_polling_in_background = True
        while self._should_poll_in_background:
            start = time.time()
            LOGGER.debug("__background_poll:: Loop start time %f", start)

            try:
                await self.poll()
                self.failed_poll_attempts = 0
                end = time.time()

                duration: float = end - start
                sleep_time: float = minimum_wait_in_seconds - duration

                LOGGER.debug(
                    "__background_poll:: [%f] Sleeping for [%fs]", duration, sleep_time
                )

                LOGGER.debug(
                    "__background_poll:: duration: %f, %f, %.2fs",
                    start,
                    end,
                    (end - start),
                )
                LOGGER.debug(
                    "__background_poll:: Should Sleep For: %f",
                    (minimum_wait_in_seconds - (end - start)),
                )

                await asyncio.sleep(minimum_wait_in_seconds - (end - start))
            except (ConnectionError, ClientOSError):
                self.failed_poll_attempts += 1
                LOGGER.info(
                    "__background_poll:: Polling error [x%d]", self.failed_poll_attempts
                )

        self.is_polling_in_background = False
        LOGGER.info("__background_poll:: Background polling disabled.")

    async def set_fan_speed(self, value):
        """Set air room vent fan speed"""
        # ui min value is 0 (OFF) to 5 (HIGH) , 6 = (AUTO)
        value = clamp(int(value), 0, 6)
        LOGGER.debug(f"Set fan speed to {value}")
        await self._winetclient.set_register(WinetRegister.FAN_AR_SPEED, value)

    async def set_power(self, value):
        """Send set register with key=002&memory=1&regId=51&value={value}"""
        # ui's min value is 2 and maximum is 5
        value = clamp(int(value), 2, 5)
        LOGGER.debug(f"Set power to {value}")
        await self._winetclient.set_register(WinetRegister.POWER_SET, value)

    async def set_temperature(self, value: float):
        """Send set register with key=002&memory=1&regId=50&value={value}"""
        # self defined min/max values
        value = clamp(float(value), 0.0, 40.0)
        LOGGER.warning(f"Set temperature to {value}")
        await self._winetclient.set_register(WinetRegister.TEMPERATURE_SET, int(value))

    async def turn_on(self):
        """Turn on the stove"""
        if self.data.status != CircularDeviceStatus.OFF:
            return
        LOGGER.debug("Turn stove on")
        await self._winetclient.get_registers(WinetRegisterKey.CHANGE_STATUS)

    async def turn_off(self):
        """Turn on the stove"""
        if self.data.status == CircularDeviceStatus.OFF:
            return
        LOGGER.debug("Turn stove off")
        await self._winetclient.get_registers(WinetRegisterKey.CHANGE_STATUS)

    async def poll(self) -> None:
        """Poll the Winet module locally."""
        result = await self._winetclient.get_registers(
            WinetRegisterKey.POLL_DATA, WinetRegisterCategory.POLL_CATEGORY_2
        )
        self._data.update(newdata=result, decode=False)
        result = await self._winetclient.get_registers(
            WinetRegisterKey.POLL_DATA, WinetRegisterCategory.POLL_CATEGORY_4
        )
        self._data.update(newdata=result, decode=False)
        result = await self._winetclient.get_registers(
            WinetRegisterKey.POLL_DATA, WinetRegisterCategory.POLL_CATEGORY_6
        )
        self._data.update(newdata=result)
