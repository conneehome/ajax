"""Switch entities for Connee Alarm (Socket, WallSwitch, Relay) - READ-ONLY.

NOTE: The Ajax Enterprise API does NOT support switch control commands (returns 404).
Socket/WallSwitch/Relay devices can only report their state, not be controlled remotely.
These are implemented as SwitchEntity for UI consistency, but control methods log warnings.
"""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, DEVICE_TYPE_MAP
from .coordinator import ConneeAlarmDataCoordinator

_LOGGER = logging.getLogger(__name__)


def _get_device_type(device: dict) -> str:
    """Return a normalized device type string."""
    raw = device.get("type") or device.get("deviceType") or ""
    return str(raw).strip()


def _get_display_name(device: dict, device_type: str) -> str:
    """Best-effort display name."""
    return (
        device.get("deviceName")
        or device.get("name")
        or device.get("label")
        or device_type
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Connee Alarm switch entities (read-only status display)."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    entities = []
    devices = coordinator.data.get("devices", [])

    for device in devices:
        device_id = device.get("id") or device.get("deviceId")
        if not device_id:
            continue

        device_type = _get_device_type(device)
        platform = DEVICE_TYPE_MAP.get(device_type)

        if platform == "switch":
            entities.append(ConneeAlarmSwitch(coordinator, device, api))

    _LOGGER.info("Setting up %d switch entities (read-only)", len(entities))
    async_add_entities(entities)


class ConneeAlarmSwitch(CoordinatorEntity, SwitchEntity):
    """Connee Alarm Socket/WallSwitch/Relay (READ-ONLY - Ajax API does not support control)."""

    _attr_has_entity_name = False
    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict, api):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)
        self._api = api

        display_name = _get_display_name(device, self._device_type)

        self._attr_unique_id = f"ajax_{self._device_id}_switch"
        self._attr_name = display_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=display_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}

        # Try various possible field names for switch state
        for key in ("switchState", "state", "powerState", "relayState", "on"):
            val = state.get(key)
            if val is not None:
                if isinstance(val, bool):
                    return val
                if isinstance(val, str):
                    return val.upper() in ("ON", "TRUE", "1", "ENABLED")
                if isinstance(val, (int, float)):
                    return val > 0

        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on - NOT SUPPORTED by Ajax API."""
        _LOGGER.warning(
            "Cannot turn on switch %s: Ajax Enterprise API does not support remote control. "
            "This switch is read-only.",
            self._device_id
        )
        # Do not call API - it will fail with 404

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off - NOT SUPPORTED by Ajax API."""
        _LOGGER.warning(
            "Cannot turn off switch %s: Ajax Enterprise API does not support remote control. "
            "This switch is read-only.",
            self._device_id
        )
        # Do not call API - it will fail with 404

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}

        attrs = {
            "device_type": self._device_type,
            "connee_id": self._device_id,
            "read_only": True,
            "control_note": "Ajax API does not support remote switch control",
        }

        # Socket/Relay specific attributes
        for k in ("switchState", "state", "powerState", "relayState", 
                  "power", "voltage", "current", "energy", "extPower",
                  "batteryChargeLevelPercentage", "signalLevel", "firmwareVersion"):
            if k in state:
                attrs[k] = state.get(k)

        return attrs
