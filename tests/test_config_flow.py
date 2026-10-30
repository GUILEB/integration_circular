"""Reconfigure step."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.circular import config_flow as cf
from custom_components.circular.winet.exceptions import WinetAPIError


def make_flow():
    flow = cf.ConfigFlow()
    entry = MagicMock(data={"host": "192.168.1.23", "entity": "sensor.a"})
    flow._get_reconfigure_entry = MagicMock(return_value=entry)
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_mismatch = MagicMock()
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.add_suggested_values_to_schema = MagicMock(side_effect=lambda s, _v: s)
    return flow, entry


def test_form_suggests_current_values():
    flow, entry = make_flow()
    assert asyncio.run(flow.async_step_reconfigure())["type"] == "form"
    assert flow.add_suggested_values_to_schema.call_args.args[1] is entry.data


def test_new_host_updates_same_stove():
    flow, _ = make_flow()
    with patch.object(cf, "validate_host_input", AsyncMock(return_value="PNEM00005")):
        asyncio.run(flow.async_step_reconfigure({"host": "192.168.1.50"}))
    flow.async_set_unique_id.assert_awaited_once_with("PNEM00005")
    flow._abort_if_unique_id_mismatch.assert_called_once_with(reason="wrong_device")
    data = flow.async_update_reload_and_abort.call_args.kwargs["data"]
    assert data == {"host": "192.168.1.50", "entity": None}


def test_unreachable_host_shows_error():
    flow, _ = make_flow()
    with patch.object(
        cf, "validate_host_input", AsyncMock(side_effect=WinetAPIError("x"))
    ):
        asyncio.run(flow.async_step_reconfigure({"host": "10.0.0.1"}))
    assert flow.async_show_form.call_args.kwargs["errors"] == {"base": "cannot_connect"}
    flow.async_update_reload_and_abort.assert_not_called()
