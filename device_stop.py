"""Stop-command selection and UI gating. No hardware or protobuf imports."""

USER_STOP_RESULT_CODES = frozenset({-10, -5})

IDLE_ASTRO_STATES = frozenset({
    "ASTRO_STATE_IDLE",
    "ASTRO_STATE_STOPPED",
    "IDLE",
    "STOPPED",
})


def is_user_stop_result(response):
    """Interrupt (-10) or a short stop-command timeout (-5) is not a real failure."""
    return response in USER_STOP_RESULT_CODES


def should_log_as_error(response, *, stopping=False):
    if is_user_stop_result(response):
        return False
    if stopping and response is False:
        return False
    return True


def stops_for(action_name=None, stop_imaging=False):
    """Return the device stop keys to send for this UI action."""
    if stop_imaging:
        return (
            "stop_astro_photo",
            "stop_wide_astro_photo",
            "stop_calibration",
            "stop_autofocus",
            "stop_eq",
            "stop_goto",
        )
    name = (action_name or "").strip().lower()
    mapping = {
        "calibration": ("stop_calibration",),
        "auto focus": ("stop_autofocus",),
        "eq solving": ("stop_eq",),
        "polar position": ("stop_motors",),
    }
    return mapping.get(name, ("stop_goto",))


def should_send_device_stop(session_running=False, action_name=None):
    """Idle live preview does not need a telescope stop command."""
    return bool(session_running or (action_name or "").strip())


def can_start_action(session_running=False, current_action=None, stop_in_progress=False, action_thread_alive=False):
    """New main-page tasks cannot start while a task or its device-stop is running."""
    if session_running:
        return False, "a session is running"
    if stop_in_progress:
        return False, "a stop is still in progress"
    if current_action or action_thread_alive:
        return False, f"{current_action or 'another task'} is already running"
    return True, None


def keep_action_until_stop_finishes(stop_in_progress, ending_name, current_action):
    """Do not clear the current action while its device-stop thread still owns the socket."""
    return bool(stop_in_progress and ending_name and current_action == ending_name)
