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

# Connee API for token validation
CONNEE_API_URL = "https://hmxxkxzkovgyzqmrzapz.supabase.co/functions/v1/validate-connee-token"

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


async def validate_connee_token(session, token: str, email: str) -> bool:
    """Validate a Connee token by calling the Connee API."""
    import logging
    _LOGGER = logging.getLogger(__name__)
    
    try:
        async with session.post(
            CONNEE_API_URL,
            json={"token": token, "email": email},
            headers={"Content-Type": "application/json"},
            timeout=10
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("valid"):
                    _LOGGER.info("Connee token validated successfully")
                    return True
                else:
                    _LOGGER.warning("Connee token invalid: %s", data.get("error", "unknown"))
                    return False
            else:
                _LOGGER.error("Connee API error: %s", resp.status)
                return False
    except Exception as e:
        _LOGGER.error("Error validating Connee token: %s", e)
        return False
