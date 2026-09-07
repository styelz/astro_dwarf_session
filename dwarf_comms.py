"""Telescope command helpers that the V3 firmware does not always ACK."""

import asyncio

SEND_WITHOUT_RESPONSE_TIMEOUT = 5


def send_without_response(message, command, module_id, timeout=SEND_WITHOUT_RESPONSE_TIMEOUT):
    """Send a protobuf command without waiting for a request response.

    Dwarf 3 / Mini firmware often never ACKs motors, focus, calibration, or
    polar-align start. Waiting on connect_socket then blocks the websocket
    until the long command timeout.
    """
    from dwarf_python_api.lib import websockets_utils as ws

    client = getattr(ws, "client_instance", None)
    if client is None or getattr(client, "task", None) is None:
        return False
    try:
        loop = client.task.get_loop()
    except Exception:
        return False
    try:
        future = asyncio.run_coroutine_threadsafe(
            ws.send_socket(message, command, 0, module_id),
            loop,
        )
        future.result(timeout=timeout)
    except Exception:
        return False
    return True


def start_calibration_without_response():
    from dwarf_python_api.proto import astro_pb2 as astro

    return send_without_response(astro.ReqStartCalibration(), 11000, 3)


def start_autofocus_without_response(infinite=False):
    from dwarf_python_api.proto import focus_pb2 as focus

    message = focus.ReqAstroAutoFocus()
    message.mode = int(bool(infinite))
    return send_without_response(message, 15004, 8)
