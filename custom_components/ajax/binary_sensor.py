"""Binary sensors for Ajax integration."""
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
from .coordinator import AjaxDataCoordinator

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

    return aliases.get(raw, raw)


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
    """Set up Ajax binary sensors."""
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
            entities.append(AjaxBinarySensor(coordinator, device))
            continue

        # Fallback: if state payload contains door-like fields, expose it anyway
        state = states.get(device_id, {}) if isinstance(states, dict) else {}
        if any(k in state for k in ("reedClosed", "openState", "magneticState", "contactState")):
            entities.append(AjaxBinarySensor(coordinator, device))

    async_add_entities(entities)


class AjaxBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Ajax binary sensor."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: AjaxDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)

        display_name = _get_display_name(device, self._device_type)

        self._attr_unique_id = f"ajax_{self._device_id}"
        self._attr_name = display_name
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

        # Pass-through a few useful fields if present
        for k in ("battery", "batteryLevel", "batteryCharge", "signal", "signalLevel", "signalStrength", "online", "isOnline"):
            if k in state:
                attrs[k] = state.get(k)

        return attrs
