"""Constants for Ajax integration."""
DOMAIN = "ajax"
MANUFACTURER = "Ajax Systems"

# Config
CONF_HUB_ID = "hub_id"
CONF_POLLING_INTERVAL = "polling_interval"

# Defaults
DEFAULT_POLLING_INTERVAL = 5
DEFAULT_SCAN_INTERVAL = 10

# API - Connee Gateway (proxies to Ajax with authorization check)
CONNEE_GATEWAY_URL = "https://hmxxkxzkovgyzqmrzapz.supabase.co/functions/v1/ajax-api"
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
