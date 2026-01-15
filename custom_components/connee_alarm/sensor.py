"""Sensors for Connee Alarm integration."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, DEVICE_TYPE_MAP, BATTERY_DEVICES, TEMPERATURE_DEVICES
from .coordinator import ConneeAlarmDataCoordinator

_LOGGER = logging.getLogger(__name__)


def get_display_name(device: dict, device_type: str) -> str:
    """Get display name from device."""
    display_name = (
        device.get("deviceName")
        or device.get("name")
        or device.get("label")
        or device_type
    )
    if display_name == device_type and device.get("deviceName"):
        display_name = device.get("deviceName")
    return display_name


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
        
        # Main sensor for specific device types (keypads, remotes, etc.)
        if DEVICE_TYPE_MAP.get(device_type) == "sensor":
            entities.append(ConneeAlarmSensor(coordinator, device))
        
        # Battery sensor for all battery-powered devices
        if device_type in BATTERY_DEVICES:
            entities.append(ConneeAlarmBatterySensor(coordinator, device))
        
        # Signal strength sensor for all devices
        if device_type in DEVICE_TYPE_MAP:
            entities.append(ConneeAlarmSignalSensor(coordinator, device))
        
        # Temperature sensor for devices with temperature
        if device_type in TEMPERATURE_DEVICES:
            entities.append(ConneeAlarmTemperatureSensor(coordinator, device))

    async_add_entities(entities)


class ConneeAlarmSensor(CoordinatorEntity, SensorEntity):
    """Connee Alarm main sensor."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = device.get("type", device.get("deviceType", ""))
        
        self._attr_unique_id = f"connee_alarm_{self._device_id}"
        self._attr_name = get_display_name(device, self._device_type)
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
        return {
            "device_type": self._device_type,
            "connee_id": self._device_id,
            "ajax_device_name": self._device.get("deviceName") or self._device.get("name"),
        }


class ConneeAlarmBatterySensor(CoordinatorEntity, SensorEntity):
    """Connee Alarm battery sensor."""

    _attr_has_entity_name = False
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = device.get("type", device.get("deviceType", ""))
        
        base_name = get_display_name(device, self._device_type)
        self._attr_unique_id = f"connee_alarm_{self._device_id}_battery"
        self._attr_name = f"{base_name} Batteria"
        self._attr_manufacturer = MANUFACTURER

    @property
    def native_value(self) -> int | None:
        """Return battery level."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {})
        battery = state.get("battery", state.get("batteryLevel", state.get("batteryCharge")))
        if battery is not None:
            try:
                return int(battery)
            except (ValueError, TypeError):
                pass
        return None

    @property
    def icon(self) -> str:
        """Return battery icon."""
        value = self.native_value
        if value is None:
            return "mdi:battery-unknown"
        if value <= 10:
            return "mdi:battery-10"
        if value <= 20:
            return "mdi:battery-20"
        if value <= 50:
            return "mdi:battery-50"
        if value <= 80:
            return "mdi:battery-80"
        return "mdi:battery"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        return {
            "device_type": self._device_type,
            "connee_id": self._device_id,
            "parent_device": get_display_name(self._device, self._device_type),
        }


class ConneeAlarmSignalSensor(CoordinatorEntity, SensorEntity):
    """Connee Alarm signal strength sensor."""

    _attr_has_entity_name = False
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = device.get("type", device.get("deviceType", ""))
        
        base_name = get_display_name(device, self._device_type)
        self._attr_unique_id = f"connee_alarm_{self._device_id}_signal"
        self._attr_name = f"{base_name} Segnale"
        self._attr_manufacturer = MANUFACTURER

    @property
    def native_value(self) -> int | None:
        """Return signal strength."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {})
        signal = state.get("signal", state.get("signalLevel", state.get("signalStrength")))
        if signal is not None:
            try:
                return int(signal)
            except (ValueError, TypeError):
                pass
        return None

    @property
    def icon(self) -> str:
        """Return signal icon."""
        value = self.native_value
        if value is None:
            return "mdi:wifi-off"
        if value <= 1:
            return "mdi:wifi-strength-1"
        if value <= 2:
            return "mdi:wifi-strength-2"
        if value <= 3:
            return "mdi:wifi-strength-3"
        return "mdi:wifi-strength-4"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {})
        return {
            "device_type": self._device_type,
            "connee_id": self._device_id,
            "online": state.get("online", state.get("isOnline", True)),
        }


class ConneeAlarmTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Connee Alarm temperature sensor."""

    _attr_has_entity_name = False
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer"

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = device.get("type", device.get("deviceType", ""))
        
        base_name = get_display_name(device, self._device_type)
        self._attr_unique_id = f"connee_alarm_{self._device_id}_temperature"
        self._attr_name = f"{base_name} Temperatura"
        self._attr_manufacturer = MANUFACTURER

    @property
    def native_value(self) -> float | None:
        """Return temperature."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {})
        temp = state.get("temperature", state.get("temp"))
        if temp is not None:
            try:
                return round(float(temp), 1)
            except (ValueError, TypeError):
                pass
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        return {
            "device_type": self._device_type,
            "connee_id": self._device_id,
            "parent_device": get_display_name(self._device, self._device_type),
        }
