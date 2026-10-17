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
    raw = (
        device.get("type")
        or device.get("deviceType")
        or (device.get("device") or {}).get("type")
        or (device.get("device") or {}).get("deviceType")
        or ""
    )
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

def _get_device_id(device: dict) -> str | None:
    """Extract device id from different Ajax payload shapes."""
    raw_id = (
        device.get("id")
        or device.get("deviceId")
        or device.get("device_id")
        or (device.get("device") or {}).get("id")
        or (device.get("device") or {}).get("deviceId")
        or (device.get("device") or {}).get("device_id")
    )
    if raw_id is None:
        return None
    raw_id = str(raw_id).strip()
    return raw_id or None


EXTRA_CONTACT_KEYS = ("extraContactClosed", "externalContactClosed", "extraContactState", "wiredContactClosed")


def _extra_contact_key(state) -> str | None:
    """v2.1.6: primo campo contatto esterno presente nello stato."""
    if not isinstance(state, dict):
        return None
    for k in EXTRA_CONTACT_KEYS:
        if state.get(k) is not None:
            return k
    return None


def _extra_contact_open(state):
    """v2.1.6: True = aperto, False = chiuso, None = sconosciuto."""
    key = _extra_contact_key(state)
    if key is None:
        return None
    val = state.get(key)
    if key.endswith("State"):
        v = str(val).strip().upper()
        if v in ("OPEN", "OPENED", "TRUE", "1", "ON"):
            return True
        if v in ("CLOSE", "CLOSED", "FALSE", "0", "OFF"):
            return False
        return None
    if isinstance(val, bool):
        return not val
    v = str(val).strip().upper()
    if v in ("TRUE", "1", "CLOSED"):
        return False
    if v in ("FALSE", "0", "OPEN"):
        return True
    return None


def _use_extra_contact(state) -> bool:
    """v2.1.7: contatto esterno abilitato E reed interno disabilitato."""
    if not isinstance(state, dict) or state.get("extraContactAware") is not True:
        return False
    for k in ("reedContactAware", "reedAware", "reedEnabled", "internalReedAware", "reedSwitchAware"):
        if state.get(k) is False:
            return True
    return False


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
        device_id = _get_device_id(device)
        if not device_id:
            continue

        device_type = _get_device_type(device)
        platform = DEVICE_TYPE_MAP.get(device_type)

        # Primary binary-sensor types (door/motion/leak/smoke...)
        state = states.get(device_id, {}) if isinstance(states, dict) else {}

        # v2.1.6: contatto esterno separato (solo DoorProtect*, solo se il campo esiste)
        if "doorprotect" in str(device_type).lower().replace("_", "").replace(" ", "") and _extra_contact_key(state):
            entities.append(ConneeAlarmExtraContactSensor(coordinator, device))

        if platform == "binary_sensor":
            entities.append(ConneeAlarmBinarySensor(coordinator, device))
            continue

        # Fallback: if state payload contains door-like fields, expose it anyway
        if any(k in state for k in ("reedClosed", "openState", "magneticState", "contactState")):
            entities.append(ConneeAlarmBinarySensor(coordinator, device))

    _LOGGER.info("Setting up %d binary_sensor entities (devices=%d)", len(entities), len(devices))
    async_add_entities(entities)


class ConneeAlarmBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Connee Alarm binary sensor."""

    _attr_has_entity_name = True
    _attr_name = "Stato"

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = _get_device_id(device)
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
        if device_class and device_class != "none":
            self._attr_device_class = BinarySensorDeviceClass(device_class)

    @property
    def is_on(self) -> bool:
        """Return true if sensor is on."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}

        # v2.1.6: contatto esterno abilitato e reed interno disabilitato -> usa contatto esterno
        if _use_extra_contact(state):
            extra_open = _extra_contact_open(state)
            if extra_open is not None:
                return extra_open

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

        # v2.1.6 diagnostica: nomi reali dei campi (contatto esterno)
        if isinstance(state, dict):
            attrs["raw_keys"] = sorted(str(k) for k in state.keys())
            attrs["extra_contact_raw"] = {
                str(k): v for k, v in sorted(state.items(), key=lambda kv: str(kv[0]))
                if any(t in str(k).lower() for t in ("extra", "contact", "wired", "aware"))
            }

        return attrs


class ConneeAlarmExtraContactSensor(CoordinatorEntity, BinarySensorEntity):
    """v2.1.6: contatto esterno DoorProtect / DoorProtect Plus (on = aperto)."""

    _attr_has_entity_name = True
    _attr_name = "Contatto esterno"
    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = _get_device_id(device)
        self._device_type = _get_device_type(device)
        display_name = _get_display_name(device, self._device_type)
        self._attr_unique_id = f"ajax_{self._device_id}_extra_contact"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=display_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

    @property
    def is_on(self):
        """Return true if external contact is open."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        return _extra_contact_open(state)
