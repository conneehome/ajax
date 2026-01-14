"""Constants for Ajax integration."""
DOMAIN = "ajax"
MANUFACTURER = "Ajax Systems"

# Config
CONF_CONNEE_TOKEN = "connee_token"
CONF_HUB_ID = "hub_id"
CONF_POLLING_INTERVAL = "polling_interval"

# Defaults
DEFAULT_POLLING_INTERVAL = 5
DEFAULT_SCAN_INTERVAL = 30

# Valid Connee Token for validation
VALID_CONNEE_TOKEN = "itE4C2xshQiqQWuzwR9cYSfrEad57fAqrefjTJ9V8KS6jzgxUIK6m65KecK8clha1K4yS4FZ7wVpKQRA6sBH4vAGLUEUgSF5SXggPqvU08kRcmtIoXDx3TwiQ4VWqaO6kqzOiv1KBoWycsT7UDJxqa8GUVaQYZMHDRc1XzMjEJJvwZWWOTCK5oBZjYVF8TS4jQ56PpvY065l91puduQvsRPjfjOjpPCXUtOW4UVuDwC3XvoxGP4W01oUdSMifc1pPSGf0DB1zFkwYJXhse38Mpq2q7AJwTUkzvxuzeYbwTFjP5QlUuMYE1ePaM6umYa0Fu7VegF05aaE3walUETBYIqiHTHisdsOX6E31mOX50xQ9b0APQYvzyG9dDTYKyyKURFXAhs9s8SbGq1FMtqtFB5sgtCqqjzfOMTKbI3rWj3UpaYLEx0Xw4fyY5Rek9IoY38q85rUrbEbfbO2jlYqdrJPg1tzX7yirLMT93pFWI9eTRhEjqDPmsIjXjFMlhjW"

# API
AJAX_API_BASE = "https://ajax.systems/api"
API_KEY = "faeb7e1d9bc74bbe9939e5178a0222d2"
TOKEN_REFRESH_INTERVAL = 600

# Device Types
DEVICE_TYPE_MAP = {
    "DoorProtect": "binary_sensor",
    "DoorProtectPlus": "binary_sensor",
    "MotionProtect": "binary_sensor",
    "MotionProtectPlus": "binary_sensor",
    "MotionCam": "binary_sensor",
    "GlassProtect": "binary_sensor",
    "CombiProtect": "binary_sensor",
    "LeaksProtect": "binary_sensor",
    "FireProtect": "binary_sensor",
    "FireProtectPlus": "binary_sensor",
    "SpaceControl": "sensor",
    "Button": "binary_sensor",
    "KeyPad": "sensor",
    "KeyPadPlus": "sensor",
    "Hub": "alarm_control_panel",
    "Hub 2": "alarm_control_panel",
    "Hub 2 Plus": "alarm_control_panel",
    "ReX": "sensor",
    "Socket": "switch",
    "WallSwitch": "switch",
    "Relay": "switch",
    "LightSwitch": "light",
}

DEVICE_CLASS_MAP = {
    "DoorProtect": "door",
    "DoorProtectPlus": "door",
    "MotionProtect": "motion",
    "MotionProtectPlus": "motion",
    "MotionCam": "motion",
    "GlassProtect": "vibration",
    "CombiProtect": "motion",
    "LeaksProtect": "moisture",
    "FireProtect": "smoke",
    "FireProtectPlus": "smoke",
}


def validate_connee_token(token: str) -> bool:
    """Validate a Connee token by direct comparison."""
    return token.strip() == VALID_CONNEE_TOKEN
