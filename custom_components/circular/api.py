"""API Client."""

import asyncio
import time
from enum import Enum

import aiohttp

from .const import (
    DEFAULT_NAME,
    ECO_DRIVE_MAX_CYCLES,
    LOGGER,
    MAX_DELTA_ECOMODE_TEMP,
    MAX_FAN_SPEED,
    MAX_POWER,
    MAX_THERMOSTAT_TEMP,
    MIN_DELTA_ECOMODE_TEMP,
    MIN_FAN_SPEED,
    MIN_POWER,
    MIN_THERMOSTAT_TEMP,
    STATUS_CHANGE_TIMEOUT,
)
from .winet.const import (
    WinetProductModel,
    WinetRegister,
    WinetRegisterCategory,
    WinetRegisterKey,
)
from .winet.exceptions import WinetAPIError
from .winet.model import WinetGetRegisterResult
from .winet.winet import WinetAPILocal


def clamp(value: float, valuemin: float, valuemax: float) -> float | int:
    """Clamp value between min and max."""
    return max(valuemin, min(value, valuemax))


def device_name(name: str | None) -> str:
    """Return the stove name, or the default one when Winet gives none."""
    # Sans nom configuré, le module Winet renvoie "NO NAME"
    if not name or name.strip().upper() in ("", "NO NAME"):
        return DEFAULT_NAME
    return name.strip()


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
            "BRAZIER_CLEANING": "Brazier cleaning",
            "FINAL_CLEANING": "Final cleaning",
            "ECO_STOP": "Eco_Stop",
            "ALARM": "Alarm",
            "MODULA": "Modula",
            "UNKNOWN": "Unknown",
        }
        return messages.get(self.name, f"Unknown status {self.name}")


class CircularDeviceAlarm(Enum):
    """Winet alarm bytes."""

    NO_ALARM = 0
    BLACK_OUT = 1
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
        self.signal = self._rawdata.signal
        self.name = device_name(self._rawdata.name)
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

    def _merge_params_efficiently(self, new_params: list[list[int]]) -> list[list[int]]:
        """Merge new parameters with existing ones efficiently."""
        # Build a dict from existing params for O(1) lookups
        params_dict: dict[int, int] = {k: v for k, v in self._rawdata.params}
        # Update with new values
        for key, value in new_params:
            if key in params_dict and params_dict[key] != value:
                LOGGER.debug(
                    "Register %s changed: %s → %s", key, params_dict[key], value
                )
            params_dict[key] = value

        # Convert back to list format
        return [[key, value] for key, value in params_dict.items()]

    def update(
        self,
        newdata: WinetGetRegisterResult,
        category: WinetRegisterCategory | None = None,
    ) -> None:
        """Update or add data to rawdata."""
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
            self.name = device_name(newdata.name)
            self.model = WinetProductModel(newdata.model)

            # Decode specific categories
            if category == WinetRegisterCategory.POLL_CATEGORY_2:
                self._update_cat2_data()
            elif category == WinetRegisterCategory.POLL_CATEGORY_6:
                self._update_cat6_data()

            # Decode status only if register exists in data
            try:
                self._decode_status()
            except WinetAPIError:
                # Status register not available in this update
                pass

        except WinetAPIError as e:
            LOGGER.error("Error updating data: %s", e)
            raise

    def _update_cat2_data(self) -> None:
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

    def _update_cat6_data(self) -> None:
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
        try:
            self.status = CircularDeviceStatus(status)
        except ValueError:
            LOGGER.warning("Unknown stove status code: %s", status)
            self.status = CircularDeviceStatus.UNKNOWN

    def _decode_alarms(self) -> None:
        """Decode alarm register byte into individual alarms."""
        alarmsbyte = self._get_register_value(WinetRegister.ALARMS_BITS)
        LOGGER.debug(f"Alarm byte value is {alarmsbyte}")
        self.alarms.clear()
        try:
            self.alarms.append(CircularDeviceAlarm(alarmsbyte))
        except ValueError:
            LOGGER.warning("Unknown alarm code: %s", alarmsbyte)

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
    def is_shutting_down(self) -> bool:
        """Is the stove in its final cleaning before stopping ?."""
        return self.status == CircularDeviceStatus.FINAL_CLEANING

    @property
    def error_offline(self) -> bool:
        """Is the stove in alarm state ?.

        Note: ce n'est pas la connexion au module Winet. La perte de connexion
        est signalée par le coordinateur (entités indisponibles).
        """
        return self.status == CircularDeviceStatus.ALARM

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
        self._eco_mode_cycles = 0
        self._update_lock = asyncio.Lock()  # Prevent concurrent update_data calls
        self._delta_ecomode = 0
        # Bascule marche/arrêt en attente : statut au moment de l'envoi
        self._status_change_from: CircularDeviceStatus | None = None
        self._status_change_at = 0.0

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
        LOGGER.debug("Set winet temperature to %s", value)
        await self._winetclient.set_register(WinetRegister.TEMPERATURE_SET, int(value))

    async def start_eco_mode_heating(self) -> None:
        """Start stove in ecoMode State."""
        # Force le démarrage du poele dans le mode EcoMode
        if self._count_delta_ecomode_asked == 0:
            self._eco_mode_cycles = 0
        self._count_delta_ecomode_asked = self._count_delta_ecomode_asked + 1
        LOGGER.debug(f"ECODRIVE - Count asked : {self._count_delta_ecomode_asked}")

    def _reset_eco_mode(self) -> None:
        """Annule la demande de mode éco en cours."""
        self._count_delta_ecomode_asked = 0
        self._eco_mode_cycles = 0

    async def eco_mode_drive(self) -> None:
        """Gestion de l'activation du poele à partir de l'état initiale EcoMode ."""
        # Demande de Chauffe avec un poele en EcoMode
        if self.data.eco_mode_drive_activated and self._count_delta_ecomode_asked > 0:
            self._eco_mode_cycles += 1
            if self._eco_mode_cycles > ECO_DRIVE_MAX_CYCLES:
                LOGGER.warning("ECODRIVE - Délai dépassé, demande abandonnée")
                self._reset_eco_mode()
                return
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
                self._reset_eco_mode()
                await self.set_temperature(temp_value)

    def _status_change_pending(self) -> bool:
        """Is a previous on/off toggle still waiting for the stove status ?."""
        if self._status_change_from is None:
            return False
        if self.data.status != self._status_change_from:
            self._status_change_from = None
            return False
        if time.monotonic() - self._status_change_at > STATUS_CHANGE_TIMEOUT:
            LOGGER.warning("Stove status unchanged after on/off request")
            self._status_change_from = None
            return False
        return True

    async def _toggle_status(self) -> None:
        """Send the on/off toggle and remember it until the status changes."""
        # CHANGE_STATUS est une bascule : un second envoi annulerait le premier
        self._status_change_from = self.data.status
        self._status_change_at = time.monotonic()
        await self._winetclient.get_registers(WinetRegisterKey.CHANGE_STATUS)

    async def turn_on(self) -> None:
        """Turn on the stove."""
        if self.data.status != CircularDeviceStatus.OFF:
            return
        if self._status_change_pending():
            LOGGER.debug("Turn stove on ignored: previous request pending")
            return
        LOGGER.debug("Turn stove on")
        await self._toggle_status()

    async def turn_off(self) -> None:
        """Turn off the stove."""
        if self.data.status == CircularDeviceStatus.OFF or self.data.is_shutting_down:
            return
        if self._status_change_pending():
            LOGGER.debug("Turn stove off ignored: previous request pending")
            return
        LOGGER.debug("Turn stove off")
        await self._toggle_status()

    async def eco_mode_drive_on(self) -> None:
        """Turn on Eco Drive Mode."""
        LOGGER.debug("Regulated Temperature - on")
        self.data.eco_mode_drive_activated = True

    async def eco_mode_drive_off(self) -> None:
        """Turn off Eco Drive Mode."""
        LOGGER.debug("Regulated Temperature - off")
        self.data.eco_mode_drive_activated = False
        self._reset_eco_mode()

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
        # Le poêle n'accepte que des consignes entières : on compare des entiers
        target = round(value)
        if (
            self.data.auto_regulated_temperature
            and self.data.is_heating
            and target != self.data.temperature_set
            and target != self.data.temperature_ask_by_external_entity
        ):
            LOGGER.debug(
                f"Regulated Temperature : winet Temp. {self.data.temperature_set} °C"
                f" vs External Temp. {value} °C"
            )
            await self.set_temperature(target)
            self.data.temperature_ask_by_external_entity = target

    async def update_data(self) -> None:
        """Update data from the Winet module locally with proper conflict handling."""
        # Prevent concurrent update_data calls
        if self._update_lock.locked():
            LOGGER.warning("Update already in progress, skipping duplicate request")
            return
        await self._update_lock.acquire()

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
                    "enabled": False,
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
            successes = 0
            for update_config in updates:
                if not update_config["enabled"]:
                    continue

                try:
                    result = await self._winetclient.get_registers(
                        update_config["key"],
                        update_config.get("category"),
                    )
                    if result is not None:
                        successes += 1  # le module a répondu
                        self._data.update(
                            newdata=result,
                            category=update_config.get("category"),
                        )
                except Exception as e:  # noqa: BLE001
                    LOGGER.error(
                        "Error updating '%s': %s",
                        update_config["name"],
                        e,
                        exc_info=True,
                    )
                    continue

                # Add delay between updates
                await asyncio.sleep(0.5)

            # Aucune requête n'a abouti : le poêle est injoignable
            if successes == 0:
                msg = "Aucune réponse du module Winet"
                raise WinetAPIError(msg)

            # EcoMode Drive handling
            await self.eco_mode_drive()

        finally:
            self._update_lock.release()
