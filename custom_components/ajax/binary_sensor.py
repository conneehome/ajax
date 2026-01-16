"""Binary sensors for Connee Alarm integration."""
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, DEVICE_CLASS_MAP, DEVICE_TYPE_MAP
from .coordinator import ConneeAlarmDataCoordinator

_LOGGER = logging.getLogger(__name__)


def _get_device_type(device: dict) -> str:
    """Return a normalized device type string."""
    raw = device.get("type") or device.get("deviceType") or ""
    raw = str(raw).strip()

    # Common aliases seen in Ajax payloads
    aliases = {
        "DoorProtectG3": "DoorProtect",
        "DoorProtect G3": "DoorProtect",
        "FireProtect2": "FireProtect 2",
        "FireProtect 2": "FireProtect 2",
        "KeyPadTouchscreen": "KeyPadTouchScreen",
        "KeyPadTouchScreen": "KeyPadTouchScreen",
        "ReX2": "ReX 2",
    }

    raw = aliases.get(raw, raw)

    # Normalize common suffixes/variants from API (e.g. "DoorProtect Jeweller")
    raw_clean = raw.replace("(", " ").replace(")", " ").replace("-", " ")
    raw_clean = " ".join(raw_clean.split())
    raw_lower = raw_clean.lower()

    if raw_lower.startswith("doorprotect"):
        if "fibra" in raw_lower:
            return "DoorProtect Fibra"
        if "plus" in raw_lower:
            return "DoorProtect Plus"
        if "g3" in raw_lower:
            return "DoorProtect G3"
        return "DoorProtect"

    return raw_clean


def _get_display_name(device: dict, device_type: str) -> str:
    """Best-effort display name."""
    # Prefer user-assigned name, fallback to model/type
    return (
        device.get("deviceName")
        or device.get("name")
        or device.get("label")
        or device.get("device", {}).get("name")
        or device_type
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Connee Alarm binary sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = []
    devices = coordinator.data.get("devices", [])
    states = coordinator.data.get("device_states", {})

    for device in devices:
        device_id = device.get("id") or device.get("deviceId")
        if not device_id:
            continue

        device_type = _get_device_type(device)
        platform = DEVICE_TYPE_MAP.get(device_type)

        # Primary binary-sensor types (door/motion/leak/smoke...)
        if platform == "binary_sensor":
            entities.append(ConneeAlarmBinarySensor(coordinator, device))
            continue

        # Fallback: if state payload contains door-like fields, expose it anyway
        state = states.get(device_id, {}) if isinstance(states, dict) else {}
        if any(k in state for k in ("reedClosed", "openState", "magneticState", "contactState")):
            entities.append(ConneeAlarmBinarySensor(coordinator, device))

    async_add_entities(entities)


class ConneeAlarmBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Connee Alarm binary sensor."""

    _attr_has_entity_name = True
    _attr_name = "Stato"

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)

        display_name = _get_display_name(device, self._device_type)

        self._attr_unique_id = f"ajax_{self._device_id}_state"
        self._attr_manufacturer = MANUFACTURER
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=display_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

        device_class = DEVICE_CLASS_MAP.get(self._device_type)
        if device_class:
            self._attr_device_class = BinarySensorDeviceClass(device_class)

    @property
    def is_on(self) -> bool:
        """Return true if sensor is on."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}

        # Door sensors: reedClosed=false => OPEN => ON
        reed_closed = state.get("reedClosed")
        if reed_closed is False:
            return True
        if reed_closed is True:
            return False

        # Door sensors: fallback field names (varies by model/API)
        open_state = state.get("openState")
        if open_state is not None:
            if isinstance(open_state, bool):
                return bool(open_state)
            val = str(open_state).strip().upper()
            if val in ("OPEN", "OPENED", "TRUE", "1", "ON"):
                return True
            if val in ("CLOSE", "CLOSED", "FALSE", "0", "OFF"):
                return False

        contact_state = state.get("contactState")
        if contact_state is None:
            contact_state = state.get("magneticState")
        if contact_state is not None:
            val = str(contact_state).strip().upper()
            if val in ("OPEN", "OPENED"):
                return True
            if val in ("CLOSE", "CLOSED"):
                return False

        # Leak sensors (LeaksProtect): various possible field names
        # Check multiple possible field names for leak detection
        for leak_key in ("leakDetected", "leak", "floodDetected", "flood", "waterDetected", "water", "moistureDetected"):
            leak_val = state.get(leak_key)
            if leak_val is True:
                return True
            if leak_val is False:
                return False
        
        # Some LeaksProtect might use state field with specific values
        leak_state = state.get("leakState", state.get("sensorState", ""))
        if str(leak_state).upper() in ("LEAK", "DETECTED", "FLOOD", "WET", "ALARM"):
            return True
        if str(leak_state).upper() in ("DRY", "OK", "NORMAL", "PASSIVE"):
            return False

        # Smoke/Fire sensors: smokeAlarmDetected, temperatureAlarmDetected
        if state.get("smokeAlarmDetected") is True:
            return True
        if state.get("temperatureAlarmDetected") is True:
            return True

        # Glass break sensors
        if state.get("glassBreakDetected") is True:
            return True

        # Motion sensors: check state field
        sensor_state = state.get("state", "")
        if str(sensor_state).upper() == "ALARM":
            return True

        # Generic fallback for motion/alarm-like payloads
        if state.get("active") is True:
            return True
        if state.get("triggered") is True:
            return True
        if state.get("alarm") is True:
            return True
        if str(state.get("alarmState", "")).upper() == "ALARM":
            return True

        return False

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}

        attrs = {
            "device_type": self._device_type,
            "connee_id": self._device_id,
            "name_candidate_deviceName": self._device.get("deviceName"),
            "name_candidate_name": self._device.get("name"),
        }

        # Pass-through ALL useful fields if present
        # Including Ajax-specific field names
        useful_keys = (
            "battery", "batteryLevel", "batteryCharge", "batteryChargeLevelPercentage",
            "signal", "signalLevel", "signalStrength",
            "online", "isOnline", "tampered",
            "leakDetected", "leak", "floodDetected", "leakState", "sensorState",
            "smokeAlarmDetected", "temperatureAlarmDetected", "coAlarmDetected",
            "temperature", "reedClosed", "state",
            "valveState", "switchState", "powerState",
            "estimatedArmingState", "firmwareVersion"
        )
        for k in useful_keys:
            if k in state:
                attrs[k] = state.get(k)
        
        # Log raw state for debugging (only non-empty fields)
        raw_state_summary = {k: v for k, v in state.items() if v is not None}
        if raw_state_summary:
            attrs["_raw_state_keys"] = list(raw_state_summary.keys())

        return attrs
