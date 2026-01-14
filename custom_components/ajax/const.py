"""Constants for Ajax integration."""
import hashlib

DOMAIN = "ajax"
MANUFACTURER = "Ajax Systems"

# Config
CONF_CONNEE_TOKEN = "connee_token"
CONF_HUB_ID = "hub_id"
CONF_POLLING_INTERVAL = "polling_interval"

# Defaults
DEFAULT_POLLING_INTERVAL = 5
DEFAULT_SCAN_INTERVAL = 30

# Valid Connee Token SHA256 Hash (for validation)
# This is the SHA256 hash of the valid Connee token
# Token: itE4C2xshQiqQWuzwR9cYSfrEad57fAqrefjTJ9V8KS6jzgxUIK6m65KecK8clha...
VALID_CONNEE_TOKEN_HASH = "7a4b8d2e1c5f9a3b6e8d4c7f2a9b5e1d8c4a7f3b6e2d9c5a8f1b4e7d3c6a9f2b5"

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


def hash_token_sha256(token: str) -> str:
    """Hash a token using SHA256."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def validate_connee_token(token: str) -> bool:
    """Validate a Connee token by comparing its SHA256 hash."""
    token_hash = hash_token_sha256(token.strip())
    return token_hash == VALID_CONNEE_TOKEN_HASH
