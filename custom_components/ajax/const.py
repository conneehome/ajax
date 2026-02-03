"""Constants for Connee Alarm integration."""
DOMAIN = "ajax"
MANUFACTURER = "Ajax Systems by Connee"
VERSION = "2.1.0"  # Used in User-Agent header

# Config
CONF_HUB_ID = "hub_id"
CONF_DEVICE_ID = "device_id"
CONF_POLLING_INTERVAL = "polling_interval"

# Defaults
DEFAULT_POLLING_INTERVAL = 5
DEFAULT_SCAN_INTERVAL = 10

# API - Connee Gateway
CONNEE_GATEWAY_URL = "https://hmxxkxzkovgyzqmrzapz.supabase.co/functions/v1/ajax-api"
TOKEN_REFRESH_INTERVAL = 600

# ==============================================================================
# AJAX FULL DEVICE CATALOG (2024-2025)
# Keep this list updated when Ajax releases new devices.
# If a device type is not here, it will still be created as a generic sensor
# thanks to the fallback logic in sensor.py and binary_sensor.py.
# ==============================================================================

DEVICE_TYPE_MAP = {
    # ─────────────────────────────────────────────────────────────────────────
    # OPENING SENSORS (Door/Window)
    # ─────────────────────────────────────────────────────────────────────────
    "DoorProtect": "binary_sensor",
    "DoorProtect Plus": "binary_sensor",
    "DoorProtectPlus": "binary_sensor",
    "DoorProtect G3": "binary_sensor",
    "DoorProtectG3": "binary_sensor",
    "DoorProtect Fibra": "binary_sensor",
    "DoorProtectFibra": "binary_sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # MOTION SENSORS
    # ─────────────────────────────────────────────────────────────────────────
    "MotionProtect": "binary_sensor",
    "MotionProtect Plus": "binary_sensor",
    "MotionProtectPlus": "binary_sensor",
    "MotionProtect Curtain": "binary_sensor",
    "MotionProtectCurtain": "binary_sensor",
    "MotionProtect Outdoor": "binary_sensor",
    "MotionProtectOutdoor": "binary_sensor",
    "MotionCam": "binary_sensor",
    "MotionCam S": "binary_sensor",
    "MotionCamS": "binary_sensor",
    "MotionCam Outdoor": "binary_sensor",
    "MotionCamOutdoor": "binary_sensor",
    "MotionCamOutdoorPhod": "binary_sensor",
    "MotionCam (PhOD) Jeweller": "binary_sensor",
    "MotionCam S (PhOD) Jeweller": "binary_sensor",
    "MotionCam Outdoor (PhOD) Jeweller": "binary_sensor",
    "MotionProtect Fibra": "binary_sensor",
    "MotionProtectFibra": "binary_sensor",
    "MotionCam Fibra": "binary_sensor",
    "MotionCamFibra": "binary_sensor",
    "DualCurtain Outdoor": "binary_sensor",
    "DualCurtainOutdoor": "binary_sensor",
    "DualCurtainOutdoorPhod": "binary_sensor",
    "Superior MotionProtect": "binary_sensor",
    "SuperiorMotionProtect": "binary_sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # GLASS BREAK SENSORS
    # ─────────────────────────────────────────────────────────────────────────
    "GlassProtect": "binary_sensor",
    "GlassProtect Fibra": "binary_sensor",
    "GlassProtectFibra": "binary_sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # COMBO / MULTI SENSORS
    # ─────────────────────────────────────────────────────────────────────────
    "CombiProtect": "binary_sensor",
    "CombiProtect Fibra": "binary_sensor",
    "CombiProtectFibra": "binary_sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # LEAK / FLOOD SENSORS
    # ─────────────────────────────────────────────────────────────────────────
    "LeaksProtect": "binary_sensor",
    "LeaksProtect Fibra": "binary_sensor",
    "LeaksProtectFibra": "binary_sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # FIRE / SMOKE / HEAT SENSORS
    # ─────────────────────────────────────────────────────────────────────────
    "FireProtect": "binary_sensor",
    "FireProtect Plus": "binary_sensor",
    "FireProtectPlus": "binary_sensor",
    "FireProtect 2": "binary_sensor",
    "FireProtect2": "binary_sensor",
    "FireProtect 2 (Heat)": "binary_sensor",
    "FireProtect 2 (Smoke)": "binary_sensor",
    "FireProtect 2 (Heat/Smoke)": "binary_sensor",
    "FireProtect 2 (Heat/Smoke/CO)": "binary_sensor",
    "FireProtect 2 SB (Heat)": "binary_sensor",
    "FireProtect 2 SB (Smoke)": "binary_sensor",
    "FireProtect 2 SB (Heat/Smoke)": "binary_sensor",
    "FireProtect 2 SB (Heat/Smoke/CO)": "binary_sensor",
    "FireProtect 2 RB (Heat)": "binary_sensor",
    "FireProtect 2 RB (Smoke)": "binary_sensor",
    "FireProtect 2 RB (Heat/Smoke)": "binary_sensor",
    "FireProtect 2 RB (Heat/Smoke/CO)": "binary_sensor",
    "FireProtect Fibra": "binary_sensor",
    "FireProtectFibra": "binary_sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # CO SENSORS
    # ─────────────────────────────────────────────────────────────────────────
    "CoDetect": "binary_sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # BUTTONS / REMOTES
    # ─────────────────────────────────────────────────────────────────────────
    "Button": "binary_sensor",
    "DoubleButton": "binary_sensor",
    "SpaceControl": "sensor",
    "SpaceControl Fibra": "sensor",
    "SpaceControlFibra": "sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # KEYPADS
    # ─────────────────────────────────────────────────────────────────────────
    "KeyPad": "sensor",
    "KeyPad Plus": "sensor",
    "KeyPadPlus": "sensor",
    "KeyPad S Plus": "sensor",
    "KeyPadSPlus": "sensor",
    "KeyPad TouchScreen": "sensor",
    "KeyPadTouchScreen": "sensor",
    "KeyPadTouchscreen": "sensor",
    "KeyPad Fibra": "sensor",
    "KeyPadFibra": "sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # HUBS (alarm_control_panel)
    # ─────────────────────────────────────────────────────────────────────────
    "Hub": "alarm_control_panel",
    "Hub Plus": "alarm_control_panel",
    "HubPlus": "alarm_control_panel",
    "HUB_PLUS": "alarm_control_panel",
    "HUB_2_PLUS": "alarm_control_panel",
    "Hub 2": "alarm_control_panel",
    "Hub2": "alarm_control_panel",
    "HUB_2": "alarm_control_panel",
    "Hub 2 (2G)": "alarm_control_panel",
    "Hub2(2G)": "alarm_control_panel",
    "HUB_2_2G": "alarm_control_panel",
    "Hub 2 (4G)": "alarm_control_panel",
    "Hub2(4G)": "alarm_control_panel",
    "HUB_2_4G": "alarm_control_panel",
    "Hub 2 Plus": "alarm_control_panel",
    "Hub2Plus": "alarm_control_panel",
    "Hub Hybrid": "alarm_control_panel",
    "HubHybrid": "alarm_control_panel",
    "HUB_HYBRID": "alarm_control_panel",
    "Hub Hybrid (2G)": "alarm_control_panel",
    "Hub Hybrid (4G)": "alarm_control_panel",

    # ─────────────────────────────────────────────────────────────────────────
    # RANGE EXTENDERS / RELAYS
    # ─────────────────────────────────────────────────────────────────────────
    "ReX": "sensor",
    "ReX 2": "sensor",
    "ReX2": "sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # WATER VALVES / WATERSTOP
    # ─────────────────────────────────────────────────────────────────────────
    "WaterStop": "valve",
    "WaterStop 1/2": "valve",
    "WaterStop 3/4": "valve",
    "WaterStop 1": "valve",
    "WaterStop Fibra": "valve",
    "WaterStopFibra": "valve",

    # ─────────────────────────────────────────────────────────────────────────
    # SMART POWER / SWITCHES / SOCKETS
    # ─────────────────────────────────────────────────────────────────────────
    "Socket": "switch",
    "WallSwitch": "switch",
    "WallSwitch (2-gang)": "switch",
    "WallSwitch Fibra": "switch",
    "WallSwitchFibra": "switch",
    "Relay": "switch",
    "Relay Fibra": "switch",
    "RelayFibra": "switch",
    "LightSwitch": "light",
    "LightSwitch Fibra": "light",
    "LightSwitchFibra": "light",

    # ─────────────────────────────────────────────────────────────────────────
    # SIRENS
    # ─────────────────────────────────────────────────────────────────────────
    "HomeSiren": "sensor",
    "HomeSiren Fibra": "sensor",
    "HomeSirenFibra": "sensor",
    "StreetSiren": "sensor",
    "StreetSiren DoubleDeck": "sensor",
    "StreetSirenDoubleDeck": "sensor",
    "StreetSiren Fibra": "sensor",
    "StreetSirenFibra": "sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # TRANSMITTERS / BRIDGES
    # ─────────────────────────────────────────────────────────────────────────
    "Transmitter": "sensor",
    "MultiTransmitter": "sensor",
    "MultiTransmitter Fibra": "sensor",
    "MultiTransmitterFibra": "sensor",
    "ocBridge Plus": "sensor",
    "ocBridgePlus": "sensor",
    "uartBridge": "sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # ACCESS / AUTHENTICATION
    # ─────────────────────────────────────────────────────────────────────────
    "Tag": "sensor",
    "Pass": "sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # ENVIRONMENT / AIR QUALITY
    # ─────────────────────────────────────────────────────────────────────────
    "LifeQuality": "sensor",

    # ─────────────────────────────────────────────────────────────────────────
    # MODULES / OTHER
    # ─────────────────────────────────────────────────────────────────────────
    "LineSupply": "sensor",
    "LineSupply Fibra": "sensor",
    "LineSupplyFibra": "sensor",
    "PowerModule": "sensor",
    "PowerModuleFibra": "sensor",
    "DECT Module": "sensor",

    # Fibra variants (generic catch-all if not explicitly above)
    # These will still be mapped; unknown ones hit fallback
}

# ─────────────────────────────────────────────────────────────────────────────
# DEVICE CLASS MAPPING (for binary_sensor icons/translations)
# ─────────────────────────────────────────────────────────────────────────────
DEVICE_CLASS_MAP = {
    # Door/Window
    "DoorProtect": "door",
    "DoorProtect Plus": "door",
    "DoorProtectPlus": "door",
    "DoorProtect G3": "door",
    "DoorProtectG3": "door",
    "DoorProtect Fibra": "door",
    "DoorProtectFibra": "door",

    # Motion
    "MotionProtect": "motion",
    "MotionProtect Plus": "motion",
    "MotionProtectPlus": "motion",
    "MotionProtect Curtain": "motion",
    "MotionProtectCurtain": "motion",
    "MotionProtect Outdoor": "motion",
    "MotionProtectOutdoor": "motion",
    "MotionCam": "motion",
    "MotionCam S": "motion",
    "MotionCamS": "motion",
    "MotionCam Outdoor": "motion",
    "MotionCamOutdoor": "motion",
    "MotionCamOutdoorPhod": "motion",
    "MotionCam (PhOD) Jeweller": "motion",
    "MotionCam S (PhOD) Jeweller": "motion",
    "MotionCam Outdoor (PhOD) Jeweller": "motion",
    "MotionProtect Fibra": "motion",
    "MotionProtectFibra": "motion",
    "MotionCam Fibra": "motion",
    "MotionCamFibra": "motion",
    "DualCurtain Outdoor": "motion",
    "DualCurtainOutdoor": "motion",
    "Superior MotionProtect": "motion",
    "SuperiorMotionProtect": "motion",

    # Glass Break
    "GlassProtect": "vibration",
    "GlassProtect Fibra": "vibration",
    "GlassProtectFibra": "vibration",

    # Combo
    "CombiProtect": "motion",
    "CombiProtect Fibra": "motion",
    "CombiProtectFibra": "motion",

    # Leak
    "LeaksProtect": "moisture",
    "LeaksProtect Fibra": "moisture",
    "LeaksProtectFibra": "moisture",

    # Fire/Smoke
    "FireProtect": "smoke",
    "FireProtect Plus": "smoke",
    "FireProtectPlus": "smoke",
    "FireProtect 2": "smoke",
    "FireProtect2": "smoke",
    "FireProtect 2 (Heat)": "heat",
    "FireProtect 2 (Smoke)": "smoke",
    "FireProtect 2 (Heat/Smoke)": "smoke",
    "FireProtect 2 (Heat/Smoke/CO)": "smoke",
    "FireProtect 2 SB (Heat)": "heat",
    "FireProtect 2 SB (Smoke)": "smoke",
    "FireProtect 2 SB (Heat/Smoke)": "smoke",
    "FireProtect 2 SB (Heat/Smoke/CO)": "smoke",
    "FireProtect 2 RB (Heat)": "heat",
    "FireProtect 2 RB (Smoke)": "smoke",
    "FireProtect 2 RB (Heat/Smoke)": "smoke",
    "FireProtect 2 RB (Heat/Smoke/CO)": "smoke",
    "FireProtect Fibra": "smoke",
    "FireProtectFibra": "smoke",

    # CO
    "CoDetect": "gas",

    # Buttons (press-type, no real device_class fits)
    "Button": "none",
    "DoubleButton": "none",
}

# ─────────────────────────────────────────────────────────────────────────────
# BATTERY-POWERED DEVICES (create battery sensor)
# ─────────────────────────────────────────────────────────────────────────────
BATTERY_DEVICES = [
    # Door/Window
    "DoorProtect", "DoorProtect Plus", "DoorProtectPlus",
    "DoorProtect G3", "DoorProtectG3",
    # Motion
    "MotionProtect", "MotionProtect Plus", "MotionProtectPlus",
    "MotionProtect Curtain", "MotionProtectCurtain",
    "MotionProtect Outdoor", "MotionProtectOutdoor",
    "MotionCam", "MotionCam S", "MotionCamS",
    "MotionCam Outdoor", "MotionCamOutdoor",
    "MotionCam (PhOD) Jeweller", "MotionCam S (PhOD) Jeweller", "MotionCam Outdoor (PhOD) Jeweller",
    "DualCurtain Outdoor", "DualCurtainOutdoor",
    "Superior MotionProtect", "SuperiorMotionProtect",
    # Glass
    "GlassProtect",
    # Combo
    "CombiProtect",
    # Leak
    "LeaksProtect",
    # Fire
    "FireProtect", "FireProtect Plus", "FireProtectPlus",
    "FireProtect 2", "FireProtect2",
    "FireProtect 2 (Heat)", "FireProtect 2 (Smoke)", "FireProtect 2 (Heat/Smoke)", "FireProtect 2 (Heat/Smoke/CO)",
    "FireProtect 2 SB (Heat)", "FireProtect 2 SB (Smoke)", "FireProtect 2 SB (Heat/Smoke)", "FireProtect 2 SB (Heat/Smoke/CO)",
    "FireProtect 2 RB (Heat)", "FireProtect 2 RB (Smoke)", "FireProtect 2 RB (Heat/Smoke)", "FireProtect 2 RB (Heat/Smoke/CO)",
    # CO
    "CoDetect",
    # Buttons/Remotes
    "SpaceControl", "Button", "DoubleButton",
    # Keypads (battery backup)
    "KeyPad", "KeyPad Plus", "KeyPadPlus", "KeyPad S Plus", "KeyPadSPlus", "KeyPad TouchScreen", "KeyPadTouchScreen", "KeyPadTouchscreen",
    # Sirens (battery)
    "StreetSiren", "StreetSiren DoubleDeck", "StreetSirenDoubleDeck", "HomeSiren",
    # Access
    "Tag", "Pass",
    # LifeQuality
    "LifeQuality",
    # ReX (backup battery)
    "ReX", "ReX 2", "ReX2",
]

# ─────────────────────────────────────────────────────────────────────────────
# TEMPERATURE-CAPABLE DEVICES (create temperature sensor)
# ─────────────────────────────────────────────────────────────────────────────
TEMPERATURE_DEVICES = [
    "FireProtect", "FireProtect Plus", "FireProtectPlus",
    "FireProtect 2", "FireProtect2",
    "FireProtect 2 (Heat)", "FireProtect 2 (Smoke)", "FireProtect 2 (Heat/Smoke)", "FireProtect 2 (Heat/Smoke/CO)",
    "FireProtect 2 SB (Heat)", "FireProtect 2 SB (Smoke)", "FireProtect 2 SB (Heat/Smoke)", "FireProtect 2 SB (Heat/Smoke/CO)",
    "FireProtect 2 RB (Heat)", "FireProtect 2 RB (Smoke)", "FireProtect 2 RB (Heat/Smoke)", "FireProtect 2 RB (Heat/Smoke/CO)",
    "FireProtect Fibra", "FireProtectFibra",
    "LifeQuality",
]
