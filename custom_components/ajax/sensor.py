"""Sensors for Connee Alarm integration."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, DEVICE_TYPE_MAP, BATTERY_DEVICES, TEMPERATURE_DEVICES
from .coordinator import ConneeAlarmDataCoordinator

_LOGGER = logging.getLogger(__name__)


def _get_device_type(device: dict) -> str:
    """Return a normalized device type string."""
    raw = device.get("type") or device.get("deviceType") or ""
    raw = str(raw).strip()

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


def get_display_name(device: dict, device_type: str) -> str:
    """Get display name from device."""
    display_name = (
        device.get("deviceName")
        or device.get("name")
        or device.get("label")
        or device.get("device", {}).get("name")
        or device_type
    )
    if display_name == device_type and device.get("deviceName"):
        display_name = device.get("deviceName")
    return str(display_name)


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
    states = coordinator.data.get("device_states", {})

    for device in devices:
        device_id = device.get("id") or device.get("deviceId")
        if not device_id:
            continue

        device_type = _get_device_type(device)
        platform = DEVICE_TYPE_MAP.get(device_type)

        # Skip hub entities here (handled by alarm_control_panel)
        if platform == "alarm_control_panel":
            continue

        # Main sensor: create it for anything that is NOT a binary_sensor
        # (includes sensor types, switches/lights we don't control yet, and unknown devices)
        if platform != "binary_sensor":
            entities.append(ConneeAlarmSensor(coordinator, device))

        # Battery sensor:
        # - always add for battery-powered devices
        # - also add if state shows a battery field (covers new models / variants)
        state = states.get(device_id, {}) if isinstance(states, dict) else {}
        has_battery = (
            device_type in BATTERY_DEVICES
            or any(k in state for k in ("battery", "batteryLevel", "batteryCharge"))
        )
        if has_battery:
            entities.append(ConneeAlarmBatterySensor(coordinator, device))

        # Signal strength sensor: ALWAYS add (this was the main cause of “14 entities”) 
        entities.append(ConneeAlarmSignalSensor(coordinator, device))

        # Temperature sensor:
        has_temp = (
            device_type in TEMPERATURE_DEVICES
            or any(k in state for k in ("temperature", "temp"))
        )
        if has_temp:
            entities.append(ConneeAlarmTemperatureSensor(coordinator, device))

    async_add_entities(entities)


class ConneeAlarmSensor(CoordinatorEntity, SensorEntity):
    """Connee Alarm main sensor (generic status)."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)

        display_name = get_display_name(device, self._device_type)

        self._attr_unique_id = f"connee_alarm_{self._device_id}_status"
        self._attr_name = display_name
        self._attr_manufacturer = MANUFACTURER
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=display_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

    @property
    def native_value(self) -> str:
        """Return sensor value."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}

        if state.get("active", state.get("triggered", False)):
            return "triggered"
        return "ok"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        return {
            "device_type": self._device_type,
            "connee_id": self._device_id,
            "name_candidate_deviceName": self._device.get("deviceName"),
            "name_candidate_name": self._device.get("name"),
        }


class ConneeAlarmBatterySensor(CoordinatorEntity, SensorEntity):
    """Connee Alarm battery sensor."""

    _attr_has_entity_name = True
    _attr_name = "Batteria"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)

        display_name = get_display_name(device, self._device_type)

        self._attr_unique_id = f"connee_alarm_{self._device_id}_battery"
        self._attr_manufacturer = MANUFACTURER
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=display_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

    @property
    def native_value(self) -> int | None:
        """Return battery level."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        battery = state.get("battery", state.get("batteryLevel", state.get("batteryCharge")))
        if battery is not None:
            try:
                return int(battery)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        return {
            "device_type": self._device_type,
            "connee_id": self._device_id,
        }


class ConneeAlarmSignalSensor(CoordinatorEntity, SensorEntity):
    """Connee Alarm signal strength sensor."""

    _attr_has_entity_name = True
    _attr_name = "Segnale"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)

        display_name = get_display_name(device, self._device_type)

        self._attr_unique_id = f"connee_alarm_{self._device_id}_signal"
        self._attr_manufacturer = MANUFACTURER
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=display_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

    @property
    def native_value(self) -> int | None:
        """Return signal strength."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        signal = state.get("signal", state.get("signalLevel", state.get("signalStrength")))
        if signal is not None:
            try:
                return int(signal)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        return {
            "device_type": self._device_type,
            "connee_id": self._device_id,
            "online": state.get("online", state.get("isOnline", True)),
        }


class ConneeAlarmTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Connee Alarm temperature sensor."""

    _attr_has_entity_name = True
    _attr_name = "Temperatura"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer"

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)

        display_name = get_display_name(device, self._device_type)

        self._attr_unique_id = f"connee_alarm_{self._device_id}_temperature"
        self._attr_manufacturer = MANUFACTURER
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=display_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

    @property
    def native_value(self) -> float | None:
        """Return temperature."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        temp = state.get("temperature", state.get("temp"))
        if temp is not None:
            try:
                return round(float(temp), 1)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        return {
            "device_type": self._device_type,
            "connee_id": self._device_id,
        }
