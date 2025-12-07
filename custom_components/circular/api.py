"""API Client."""

from enum import Enum
from threading import Lock

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
        messages = {
            "OFF": "Off",
            "WAIT_FOR_FLAME": "Waiting flame",
            "POWER_ON": "Power on",
            "UNKNOWN_1": "Unknown",
            "STABLE_FLAME": "Stable Flame",
            "WORK": "Working",
            "BRAZIER_CLEANING": "Brazzier cleaning",
            "FINAL_CLEANING": "Final cleaning",
            "ECO_STOP": "Eco_Stop",
            "ALARM": "Alarm",
            "MODULA": "Modula",
            "UNKNOWN": "Unknown",
        }
        return messages.get(self.name, f"Unknown status{self.name}")


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
        messages = {
            "SMOKE_PROBE_FAILURE": "Smoke probe failure !",
            "SMOKE_OVERTEMPERATURE": "Smoke over-temperature !",
            "EXTRACTOR_MALFUNCTION": "Extractor malfunction !",
            "FAILED_IGNITION": "Failed ignition",
            "NO_PELLETS": "No pellets",
            "LACK_OF_PRESSURE": "Lacks of pressure !",
            "THERMAL_SAFETY": "Thermal safety !",
            "OPEN_PELLET_COMPARTMENT": "Pellet compartment is open !",
        }
        return messages.get(self.name, "UNKNOWN")


class CircularApiData:
    """Usable api data for the home assistant integration."""

    def __init__(self, host: str) -> None:
        """Init unset data."""
        self._rawdata = WinetGetRegisterResult()
        self._data_lock = Lock()  # Thread-safe lock for data updates
        self._changed_fields: set[str] = set()  # Track changed fields

        # Metadata for update tracking
        self._last_update_timestamp: dict[str, float] = {}
        self._update_pending: dict[str, bool] = {}
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
        self.delta_ecomode = 0.0
        self.eco_mode_drive_activated = False
        self.temperature_ask_by_external_entity = 0.0
        self.auto_regulated_temperature = False

    def get_changed_fields(self) -> set[str]:
        """Get the set of fields that have changed since last check."""
        with self._data_lock:
            fields = self._changed_fields.copy()
            self._changed_fields.clear()
        return fields

    def _merge_params_efficiently(self, new_params: list[list[int]]) -> list[list[int]]:
        """Merge new parameters with existing ones efficiently."""
        # Build a dict from existing params for O(1) lookups
        params_dict: dict[int, int] = {k: v for k, v in self._rawdata.params}
        # Update with new values
        for key, value in new_params:
            if key in params_dict and params_dict[key] != value:
                LOGGER.debug(f"Register {key} changed: {params_dict[key]} → {value}")
            params_dict[key] = value

        # Convert back to list format
        return [[key, value] for key, value in params_dict.items()]

    def update(
        self,
        newdata: WinetGetRegisterResult,
        category: WinetRegisterCategory | None = None,
    ) -> None:
        """Update or add data to rawdata with thread-safety and conflict detection."""
        with self._data_lock:
            try:
                # Merge parameters efficiently
                merged_params = self._merge_params_efficiently(newdata.params)

                # Update raw data
                self._rawdata.params = merged_params
                self._rawdata.cat = newdata.cat
                self._rawdata.signal = newdata.signal
                self._rawdata.alr = newdata.alr
                self._rawdata.authlevel = newdata.authlevel
                self._rawdata.model = newdata.model
                self._rawdata.name = newdata.name

                # Update public properties
                self.signal = newdata.signal
                self.alr = newdata.alr
                self.name = newdata.name
                self.model = WinetProductModel(newdata.model)

                # Decode specific categories with change tracking
                if category == WinetRegisterCategory.POLL_CATEGORY_2:
                    self._update_temperature_data()
                    self._changed_fields.update(
                        ["temperature_read", "temperature_set", "power_set", "status"]
                    )

                elif category == WinetRegisterCategory.POLL_CATEGORY_6:
                    self._update_alarm_data()
                    self._changed_fields.update(["alarms", "fan_speed"])

                elif category == WinetRegisterCategory.POLL_CATEGORY_4:
                    self._changed_fields.add("fan_configuration")

                # Decode status only if register exists in data
                try:
                    self._decode_status()
                    if "status" not in self._changed_fields:
                        self._changed_fields.add("status")
                except WinetAPIError:
                    # Status register not available in this update
                    pass

            except WinetAPIError as e:
                LOGGER.error(f"Error updating data: {e}")
                raise

    def _update_temperature_data(self) -> None:
        """Update all temperature-related data atomically."""
        temp_threshold = 0.1
        try:
            old_temp_read = self.temperature_read
            old_temp_set = self.temperature_set
            old_power = self.power_set

            self._decode_temperature_read()
            self._decode_temperature_set()
            self._decode_power_set()

            # Log significant changes
            if abs(self.temperature_read - old_temp_read) > temp_threshold:
                LOGGER.debug(
                    f"Temperature read changed: {old_temp_read} → "
                    f"{self.temperature_read}"
                )
            if self.temperature_set != old_temp_set:
                LOGGER.debug(
                    f"Temperature set changed: {old_temp_set} → "
                    f"{self.temperature_set}"
                )
            if self.power_set != old_power:
                LOGGER.debug(f"Power set changed: {old_power} → {self.power_set}")

        except WinetAPIError as e:
            LOGGER.warning(f"Failed to update temperature data: {e}")

    def _update_alarm_data(self) -> None:
        """Update all alarm-related data atomically."""
        try:
            self._decode_alarms()
            self._decode_fan_speed()
        except WinetAPIError as e:
            LOGGER.warning(f"Failed to update alarm data: {e}")

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
        self._count_delta_ecomode_asked = 0
        self._update_lock = Lock()  # Prevent concurrent update_data calls
        self._delta_ecomode = 0

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
        LOGGER.warning(f"Set winet temperature to {value}")
        await self._winetclient.set_register(WinetRegister.TEMPERATURE_SET, int(value))

    async def start_eco_mode_heating(self) -> None:
        """Start stove in ecoMode State."""
        # Force le démarrage du poele dans le mode EcoMode
        self._count_delta_ecomode_asked = self._count_delta_ecomode_asked + 1
        LOGGER.debug(f"ECODRIVE - Count asked : {self._count_delta_ecomode_asked}")

    async def eco_mode_drive(self) -> None:
        """Gestion de l'activation du poele à partir de l'état initiale EcoMode ."""
        # Demande de Chauffe avec un poele en EcoMode
        if self.data.eco_mode_drive_activated and self._count_delta_ecomode_asked > 0:
            temp_value = self.data.temperature_set
            # Demande de Demarrage à partir de Eco Mode : Activation Read + EcoDelta
            if self.data.is_ecomode_stop and self._count_delta_ecomode_asked == 1:
                temp_diff = self.data.temperature_set - self.data.temperature_read
                # Si la différence n'est pas assez grande => force le demarrage
                if temp_diff <= self._delta_ecomode:
                    LOGGER.info("ECODRIVE - Start Begin")
                    temp_value = self.data.temperature_read + self._delta_ecomode
                    await self.set_temperature(temp_value)

            elif self.data.is_heating and self._count_delta_ecomode_asked > 0:
                # Poele en WORK : Fin de l'activation de l'EcoMode
                # Application de la consigne demandée
                LOGGER.info("ECODRIVE - Start Completed")
                self._count_delta_ecomode_asked = 0
                await self.set_temperature(temp_value)

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

    async def eco_mode_drive_on(self) -> None:
        """Turn on Eco Drive Mode."""
        LOGGER.debug("Regulated Temperature - on")
        self.data.eco_mode_drive_activated = True

    async def eco_mode_drive_off(self) -> None:
        """Turn off Eco Drive Mode."""
        LOGGER.debug("Regulated Temperature - off")
        self.data.eco_mode_drive_activated = False

    async def auto_regulated_temperature_on(self) -> None:
        """Turn on automatic temperature regulation for the stove."""
        LOGGER.debug("Regulated Temperature - on")
        self.data.auto_regulated_temperature = True

    async def auto_regulated_temperature_off(self) -> None:
        """Turn off automatic temperature regulation for the stove."""
        LOGGER.debug("Regulated Temperature - off")
        self.data.auto_regulated_temperature = False

    async def set_temperature_ask_by_external_entity(self, value: float) -> None:
        """Set temperature ask by external entity."""
        if (
            self.data.auto_regulated_temperature
            and self.data.is_heating
            and value != self.data.temperature_set
        ):
            LOGGER.warning(
                f"Regulated Temperature : winet Temp. {self.data.temperature_set} °C"
                f" vs External Temp. {value} °C"
            )
            await self.set_temperature(value)
            self.data.temperature_ask_by_external_entity = value

    async def update_data(self) -> None:
        """Update data from the Winet module locally with proper conflict handling."""
        # Prevent concurrent update_data calls
        if not self._update_lock.acquire(blocking=False):
            LOGGER.warning("Update already in progress, skipping duplicate request")
            return

        try:
            LOGGER.debug("Updating data from Winet module")

            # Define update schedule with priorities
            updates = [
                {
                    "name": "hardware",
                    "enabled": True,
                    "key": WinetRegisterKey.UPDATE_HARDWARE,
                    "category": None,
                },
                {
                    "name": "category_2",
                    "enabled": True,
                    "key": WinetRegisterKey.POLL_DATA,
                    "category": WinetRegisterCategory.POLL_CATEGORY_2,
                },
                {
                    "name": "category_4",
                    "enabled": True,
                    "key": WinetRegisterKey.POLL_DATA,
                    "category": WinetRegisterCategory.POLL_CATEGORY_4,
                },
                {
                    "name": "category_6",
                    "enabled": True,
                    "key": WinetRegisterKey.POLL_DATA,
                    "category": WinetRegisterCategory.POLL_CATEGORY_6,
                },
            ]

            # Execute updates in order
            for update_config in updates:
                if not update_config["enabled"]:
                    continue

                try:
                    result = await self._winetclient.get_registers(
                        update_config["key"],
                        update_config.get("category"),
                    )
                    if result is not None:
                        self._data.update(
                            newdata=result,
                            category=update_config.get("category"),
                        )
                        changed_fields = self._data.get_changed_fields()
                        if changed_fields:
                            LOGGER.debug(
                                f"Update '{update_config['name']}' changed fields: "
                                f"{changed_fields}"
                            )
                except Exception as e:  # noqa: BLE001
                    LOGGER.error(
                        f"Error updating '{update_config['name']}': {e}",
                        exc_info=True,
                    )
                    continue

            # EcoMode Drive handling
            await self.eco_mode_drive()

        finally:
            self._update_lock.release()
