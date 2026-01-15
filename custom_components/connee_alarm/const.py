"""Constants for Connee Alarm integration."""
DOMAIN = "connee_alarm"
MANUFACTURER = "Ajax Systems by Connee"

# Config
CONF_HUB_ID = "hub_id"
CONF_POLLING_INTERVAL = "polling_interval"

# Defaults
DEFAULT_POLLING_INTERVAL = 5
DEFAULT_SCAN_INTERVAL = 10

# API - Connee Gateway
CONNEE_GATEWAY_URL = "https://hmxxkxzkovgyzqmrzapz.supabase.co/functions/v1/ajax-api"
TOKEN_REFRESH_INTERVAL = 600

# Device Types - ALL Ajax Devices
DEVICE_TYPE_MAP = {
    # Door/Window Sensors
    "DoorProtect": "binary_sensor",
    "DoorProtectPlus": "binary_sensor",
    # Motion Sensors
    "MotionProtect": "binary_sensor",
    "MotionProtectPlus": "binary_sensor",
    "MotionProtectCurtain": "binary_sensor",
    "MotionProtectOutdoor": "binary_sensor",
    "MotionCam": "binary_sensor",
    "MotionCamOutdoor": "binary_sensor",
    "DualCurtainOutdoor": "binary_sensor",
    # Glass Break
    "GlassProtect": "binary_sensor",
    # Combo Sensors
    "CombiProtect": "binary_sensor",
    "CombiProtectFibra": "binary_sensor",
    # Leak Sensors
    "LeaksProtect": "binary_sensor",
    # Fire/Smoke Sensors
    "FireProtect": "binary_sensor",
    "FireProtect 2": "binary_sensor",
    "FireProtectPlus": "binary_sensor",
    "FireProtect 2 (Heat/Smoke/CO)": "binary_sensor",
    # CO Sensor
    "CoDetect": "binary_sensor",
    # Buttons/Remotes
    "SpaceControl": "sensor",
    "Button": "binary_sensor",
    "DoubleButton": "binary_sensor",
    # Keypads
    "KeyPad": "sensor",
    "KeyPadPlus": "sensor",
    "KeyPadTouchScreen": "sensor",
    "KeyPadFibra": "sensor",
    # Hubs
    "Hub": "alarm_control_panel",
    "Hub 2": "alarm_control_panel",
    "Hub 2 Plus": "alarm_control_panel",
    "Hub Plus": "alarm_control_panel",
    "Hub Hybrid": "alarm_control_panel",
    # Range Extenders
    "ReX": "sensor",
    "ReX 2": "sensor",
    # Smart Plugs/Switches
    "Socket": "switch",
    "WallSwitch": "switch",
    "Relay": "switch",
    "LightSwitch": "light",
    # Sirens
    "StreetSiren": "sensor",
    "StreetSirenDoubleDeck": "sensor",
    "HomeSiren": "sensor",
    # Transmitters
    "Transmitter": "sensor",
    "MultiTransmitter": "sensor",
    "ocBridge Plus": "sensor",
    # Other
    "Tag": "sensor",
    "Pass": "sensor",
    "LifeQuality": "sensor",
}

DEVICE_CLASS_MAP = {
    "DoorProtect": "door",
    "DoorProtectPlus": "door",
    "MotionProtect": "motion",
    "MotionProtectPlus": "motion",
    "MotionProtectCurtain": "motion",
    "MotionProtectOutdoor": "motion",
    "MotionCam": "motion",
    "MotionCamOutdoor": "motion",
    "DualCurtainOutdoor": "motion",
    "GlassProtect": "vibration",
    "CombiProtect": "motion",
    "CombiProtectFibra": "motion",
    "LeaksProtect": "moisture",
    "FireProtect": "smoke",
    "FireProtect 2": "smoke",
    "FireProtectPlus": "smoke",
    "FireProtect 2 (Heat/Smoke/CO)": "smoke",
    "CoDetect": "gas",
    "Button": "none",
    "DoubleButton": "none",
}

# Devices that have battery (for creating battery sensors)
BATTERY_DEVICES = [
    "DoorProtect", "DoorProtectPlus",
    "MotionProtect", "MotionProtectPlus", "MotionProtectCurtain", "MotionProtectOutdoor",
    "MotionCam", "MotionCamOutdoor", "DualCurtainOutdoor",
    "GlassProtect", "CombiProtect", "CombiProtectFibra",
    "LeaksProtect", "FireProtect", "FireProtect 2", "FireProtectPlus", "CoDetect",
    "SpaceControl", "Button", "DoubleButton",
    "KeyPad", "KeyPadPlus", "KeyPadTouchScreen",
    "StreetSiren", "StreetSirenDoubleDeck", "HomeSiren",
    "Tag", "Pass", "LifeQuality",
]

# Devices that have temperature sensor
TEMPERATURE_DEVICES = [
    "FireProtect", "FireProtect 2", "FireProtectPlus", "FireProtect 2 (Heat/Smoke/CO)",
    "LifeQuality",
]
