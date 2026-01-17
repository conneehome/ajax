"""Firmware update entities for Connee Alarm integration."""
import logging
from typing import Any

from homeassistant.components.update import (
    UpdateEntity,
    UpdateEntityFeature,
    UpdateDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, DEVICE_TYPE_MAP, CONNEE_LOGO_URL
from .coordinator import ConneeAlarmDataCoordinator

_LOGGER = logging.getLogger(__name__)


def _get_device_id(device: dict) -> str | None:
    """Get device ID from various possible keys."""
    return device.get("id") or device.get("deviceId")


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
    """Set up Connee Alarm update entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = []
    devices = coordinator.data.get("devices", [])
    hub_state = coordinator.data.get("hub_state", {})

    # Add hub update entity
    if hub_state:
        hub_id = data.get("hub_id")
        if hub_id:
            entities.append(ConneeAlarmHubUpdate(coordinator, hub_state, hub_id))

    # Add device update entities
    for device in devices:
        device_id = _get_device_id(device)
        if not device_id:
            continue

        device_type = _get_device_type(device)
        # Skip hubs - they are handled separately above
        if DEVICE_TYPE_MAP.get(device_type) == "alarm_control_panel":
            continue

        entities.append(ConneeAlarmDeviceUpdate(coordinator, device))

    _LOGGER.info("Setting up %d update entities", len(entities))
    async_add_entities(entities)


class ConneeAlarmHubUpdate(CoordinatorEntity, UpdateEntity):
    """Firmware update entity for Connee Alarm hub."""

    _attr_has_entity_name = True
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_supported_features = UpdateEntityFeature(0)  # Read-only, no install

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, hub_state: dict, hub_id: str):
        """Initialize."""
        super().__init__(coordinator)
        self._hub_id = hub_id
        self._hub_state = hub_state

        hub_name = hub_state.get("name") or hub_state.get("hubName") or "Ajax Hub"
        model = hub_state.get("model") or hub_state.get("type") or "Hub"

        self._attr_unique_id = f"ajax_{hub_id}_firmware"
        self._attr_name = "Firmware"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub_id)},
            name=hub_name,
            manufacturer=MANUFACTURER,
            model=model,
        )

    @property
    def entity_picture(self) -> str:
        """Return Connee official logo."""
        return CONNEE_LOGO_URL

    @property
    def installed_version(self) -> str | None:
        """Return the current firmware version."""
        hub_state = self.coordinator.data.get("hub_state", {})
        # Ajax API returns firmware as nested object: { firmware: { version: "..." } }
        firmware_obj = hub_state.get("firmware", {})
        if isinstance(firmware_obj, dict) and firmware_obj.get("version"):
            return firmware_obj.get("version")
        return hub_state.get("firmwareVersion") or hub_state.get("firmware_version")

    @property
    def latest_version(self) -> str | None:
        """Return the latest available version (same as installed for read-only)."""
        return self.installed_version

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        hub_state = self.coordinator.data.get("hub_state", {})
        attrs = {
            "device_type": "Hub",
            "connee_id": self._hub_id,
        }
        
        for key in ("model", "type", "firmwareVersion", "osVersion", "kernelVersion"):
            if key in hub_state:
                attrs[key] = hub_state[key]

        return attrs


class ConneeAlarmDeviceUpdate(CoordinatorEntity, UpdateEntity):
    """Firmware update entity for Connee Alarm devices."""

    _attr_has_entity_name = True
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_supported_features = UpdateEntityFeature(0)  # Read-only, no install

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = _get_device_id(device)
        self._device_type = _get_device_type(device)

        display_name = _get_display_name(device, self._device_type)

        self._attr_unique_id = f"ajax_{self._device_id}_firmware"
        self._attr_name = "Firmware"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=display_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

    @property
    def entity_picture(self) -> str:
        """Return Connee official logo."""
        return CONNEE_LOGO_URL

    @property
    def installed_version(self) -> str | None:
        """Return the current firmware version."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        return state.get("firmwareVersion") or state.get("firmware_version") or self._device.get("firmwareVersion")

    @property
    def latest_version(self) -> str | None:
        """Return the latest available version (same as installed for read-only)."""
        return self.installed_version

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}

        attrs = {
            "device_type": self._device_type,
            "connee_id": self._device_id,
        }

        for key in ("firmwareVersion", "hwVersion", "bootVersion"):
            val = state.get(key)
            if val is not None:
                attrs[key] = val

        return attrs
