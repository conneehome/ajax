"""Sensors for Connee Alarm integration."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, DEVICE_TYPE_MAP
from .coordinator import ConneeAlarmDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Connee Alarm sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = []
    devices = coordinator.data.get("devices", [])
    
    for device in devices:
        device_type = device.get("type", device.get("deviceType", ""))
        if DEVICE_TYPE_MAP.get(device_type) == "sensor":
            entities.append(ConneeAlarmSensor(coordinator, device))

    async_add_entities(entities)


class ConneeAlarmSensor(CoordinatorEntity, SensorEntity):
    """Connee Alarm sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = device.get("type", device.get("deviceType", ""))
        
        self._attr_unique_id = f"connee_alarm_{self._device_id}"
        # Usa il nome esatto dall'app Ajax (es. "Sensore porta Aldo")
        self._attr_name = device.get("name") or device.get("deviceName") or self._device_type
        self._attr_manufacturer = MANUFACTURER

    @property
    def native_value(self) -> str:
        """Return sensor value."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {})
        
        if state.get("active", state.get("triggered", False)):
            return "triggered"
        return "ok"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {})
        
        attrs = {
            "device_type": self._device_type,
            "connee_id": self._device_id,
        }
        
        if "battery" in state or "batteryLevel" in state:
            attrs["battery_level"] = state.get("battery", state.get("batteryLevel"))
        if "signal" in state or "signalLevel" in state:
            attrs["signal_strength"] = state.get("signal", state.get("signalLevel"))
        
        return attrs
