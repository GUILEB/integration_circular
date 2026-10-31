# AGENTS.md

Guidance for AI coding agents working in this repository.

Home Assistant custom integration (domain `circular`) that drives Ravelli Circular pellet stoves locally over HTTP through their **Winet Control** wifi module. The maintainer writes in French: user-facing answers, commit messages, code comments and docs are in French; code identifiers and docstrings stay in English.

## Commands

```bash
scripts/test                                   # full pytest suite (python3 -m pytest tests)
scripts/test tests/test_eco.py                 # one file
scripts/test tests/test_eco.py::test_name -q   # one test
scripts/lint                                   # ruff format + ruff check --fix
ruff check custom_components                   # lint without auto-fix
scripts/develop                                # run HA with ./config (alternative to the debugger)
```

- Python 3.14 system interpreter (`/usr/local/bin/python3`); packages are installed with `pip --user` into `~/.local` (no venv). `hass` is `~/.local/bin/hass`.
- Home Assistant is normally launched by the user from the VS Code debugger (`.vscode/launch.json`, `python -m homeassistant --debug -c config`). Do not kill it: ask the user to restart HA after code changes.
- A Claude Code PostToolUse hook (`.claude/hooks/run-tests.sh`) runs the test suite after every edit of a `.py` file in `custom_components/circular/` or `tests/`; failures are reported back and must be fixed.
- Ruff uses `select = ALL` (`.ruff.toml`); the existing code has ~37 pre-existing alerts. Don't introduce new ones without a justified `noqa`.
- The repo-root `custom_components/` is what HA loads (namespace package, via the `config` dir). Third-party integrations installed for testing (HACS, versatile_thermostat, vtherm_pellet_stove) live there too but are gitignored; do not put integrations in `config/custom_components`.
- Version bumps: update both `VERSION` in `const.py` and `version` in `manifest.json`.
- Work on `develop`; `master` is the release branch.

## Architecture

Layers, from the stove up:

1. **`winet/`** — low-level Winet HTTP client. `WinetAPILocal.get_registers(key, category)` polls register blocks, `set_register(register, value)` writes one. `HTTPRequestExecutor` handles retries. `winet/const.py` holds the register IDs (`WinetRegister`: STATUS=2, ALARMS_BITS=3, TEMPERATURE_PROBE=6 (integer °C), TEMPERATURE_SET=50, POWER_SET=51, FAN_AR_SPEED=187) and request keys. Errors surface as `WinetAPIError`.
2. **`api.py`** — the business logic.
   - `CircularApiData` decodes the raw register list into typed fields (`status: CircularDeviceStatus`, `temperature_read`, `temperature_set`, `power_set`, alarms…). A field is decoded only if its register is present in the last response.
   - `CircularApiClient` owns one `CircularApiData` and all stove commands. `update_data()` is lock-protected and polls several categories; the hardware block only every `HARDWARE_UPDATE_INTERVAL`. It raises `WinetAPIError` only when every request fails.
   - **On/off is a toggle** (`CHANGE_STATUS` key): `turn_on()` acts only from OFF, `turn_off()` skips OFF/FINAL_CLEANING, and a pending-change guard (`STATUS_CHANGE_TIMEOUT`) prevents double toggles before the status refreshes.
   - **Eco mode**: in ECO_STOP the stove waits until its probe drops below the setpoint minus a delta. `start_eco_mode_heating()` temporarily raises the setpoint (read + delta) to restart heating, and `_end_eco_mode()` restores it once WORK is reached or `ECO_DRIVE_TIMEOUT` expires, but only if nobody changed the setpoint meanwhile.
   - `set_temperature_ask_by_external_entity()` implements "Stop Déviation": it forces the stove setpoint to the rounded value of an external entity (typically the Versatile Thermostat regulated temperature), in every running status, as soon as they differ (target rounded half up and clamped to 5–40), so changes made from the remote/Winet app are overridden. It stays idle when the stove is off, in final cleaning, in alarm or unknown, and during an Eco restart. Enabled by default; the switch restores its last state.
3. **`coordinator.py`** — `CircularDataUpdateCoordinator` polls every `UPDATE_INTERVAL` s, then pushes the optional external sensor value (`CONF_ENTITY`) to the API. It maps `WinetAPIError`/timeout to `UpdateFailed`. It exposes `read_api`/`control_api` (same client) and `device_info`. The type alias `CircularConfigEntry` carries the coordinator in `entry.runtime_data`.
4. **Platforms** (`climate`, `sensor`, `binary_sensor`, `switch`, `number`) — thin entities built on `CircularEntity` (`entity.py`, `has_entity_name` + `translation_key`, unique_id `f"{key}_{model}"`). Command handlers call the client, then `coordinator.async_request_refresh()`. `climate.py` maps stove statuses to HVAC mode/action and exposes power 1–5 as presets (used by Versatile Thermostat / vtherm_pellet_stove). The Eco delta `number` is a `RestoreNumber` that re-applies its value to the client at startup.
5. **`config_flow.py`** — user step and reconfigure step. Both validate the host by polling the stove. The unique_id is the stove model string, so the reconfigure step aborts with `wrong_device` if the IP points to another stove. **`__init__.py`** also implements `async_remove_config_entry_device` and **`diagnostics.py`** dumps the decoded state plus the raw registers.

Translations: entity and config-flow strings live in `translations/fr.json` and `translations/en.json`. Keep both in sync when adding entities, errors or steps.

## Tests

`tests/` uses plain pytest with no HA test harness and no pytest-asyncio: async code runs via `asyncio.run(...)` inside sync tests. The `client` fixture in `tests/conftest.py` builds a `CircularApiClient` whose `_winetclient` is mocked; written setpoints are echoed back into `data.temperature_set`. `writes(api)` lists the written values. Entities are instantiated with `Class.__new__(Class)` plus a `MagicMock` coordinator with an `AsyncMock` `async_request_refresh`.
