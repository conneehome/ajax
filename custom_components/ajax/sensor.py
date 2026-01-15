"""Sensors for Ajax integration."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, DEVICE_TYPE_MAP, BATTERY_DEVICES, TEMPERATURE_DEVICES
from .coordinator import AjaxDataCoordinator

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
            entities.append(AjaxSensor(coordinator, device))

        # Battery sensor:
        # - always add for battery-powered devices
        # - also add if state shows a battery field (covers new models / variants)
        state = states.get(device_id, {}) if isinstance(states, dict) else {}
        has_battery = (
            device_type in BATTERY_DEVICES
            or any(k in state for k in ("battery", "batteryLevel", "batteryCharge"))
        )
        if has_battery:
            entities.append(AjaxBatterySensor(coordinator, device))

        # Signal strength sensor: ALWAYS add (this was the main cause of “14 entities”) 
        entities.append(AjaxSignalSensor(coordinator, device))

        # Temperature sensor:
        has_temp = (
            device_type in TEMPERATURE_DEVICES
            or any(k in state for k in ("temperature", "temp"))
        )
        if has_temp:
            entities.append(AjaxTemperatureSensor(coordinator, device))

    async_add_entities(entities)


class AjaxSensor(CoordinatorEntity, SensorEntity):
    """Ajax main sensor (generic status)."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: AjaxDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)

        display_name = get_display_name(device, self._device_type)

        self._attr_unique_id = f"ajax_{self._device_id}_status"
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
            "ajax_id": self._device_id,
            "name_candidate_deviceName": self._device.get("deviceName"),
            "name_candidate_name": self._device.get("name"),
        }


class AjaxBatterySensor(CoordinatorEntity, SensorEntity):
    """Ajax battery sensor."""

    _attr_has_entity_name = True
    _attr_name = "Batteria"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: AjaxDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)

        display_name = get_display_name(device, self._device_type)

        self._attr_unique_id = f"ajax_{self._device_id}_battery"
        self._attr_manufacturer = MANUFACTURER
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=display_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

    def _coerce_int(self, val: Any) -> int | None:
        """Try to coerce different value shapes into an int."""
        if val is None:
            return None
        if isinstance(val, bool):
            return None
        if isinstance(val, (int, float)):
            return int(val)
        if isinstance(val, str):
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return None
        if isinstance(val, dict):
            for k in ("value", "percent", "percentage", "level", "charge"):
                if k in val:
                    return self._coerce_int(val.get(k))
        return None

    def _get_battery_value(self, data: dict) -> int | None:
        """Extract battery value from data dict, trying multiple field names."""
        # Try direct fields (different Ajax payload variants)
        for key in (
            "batteryCharge",
            "batteryLevel",
            "batteryPercent",
            "batteryPercentage",
            "battery",
            "battery_charge",
            "battery_level",
        ):
            val = self._coerce_int(data.get(key))
            if val is not None:
                return val

        # Try nested battery object
        batt_obj = data.get("battery")
        if isinstance(batt_obj, dict):
            for key in (
                "charge",
                "level",
                "percent",
                "percentage",
                "value",
                "chargePercentage",
            ):
                val = self._coerce_int(batt_obj.get(key))
                if val is not None:
                    return val

        return None

    @property
    def native_value(self) -> int | None:
        """Return battery level."""
        # First check device_states (updated data)
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        val = self._get_battery_value(state)
        if val is not None:
            return val

        # Fallback to initial device data
        val = self._get_battery_value(self._device)
        if val is not None:
            return val

        # Try to find in devices list (in case device object was updated)
        devices = self.coordinator.data.get("devices", [])
        for d in devices:
            if (d.get("id") or d.get("deviceId")) == self._device_id:
                val = self._get_battery_value(d)
                if val is not None:
                    return val
                break

        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        return {
            "device_type": self._device_type,
            "connee_id": self._device_id,
            "raw_battery_fields": {
                k: state.get(k) for k in ("battery", "batteryCharge", "batteryLevel", "batteryPercent")
                if state.get(k) is not None
            },
        }


class AjaxSignalSensor(CoordinatorEntity, SensorEntity):
    """Ajax signal strength sensor."""

    _attr_has_entity_name = True
    _attr_name = "Segnale"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator: AjaxDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)

        display_name = get_display_name(device, self._device_type)

        self._attr_unique_id = f"ajax_{self._device_id}_signal"
        self._attr_manufacturer = MANUFACTURER
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=display_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

    def _get_signal_value(self, data: dict) -> int | None:
        """Extract signal value from data dict, trying multiple field names."""
        def coerce(val: Any) -> int | None:
            if val is None or isinstance(val, bool):
                return None
            if isinstance(val, (int, float)):
                return int(val)
            if isinstance(val, str):
                try:
                    return int(float(val))
                except (ValueError, TypeError):
                    return None
            if isinstance(val, dict):
                for k in ("value", "level", "signal", "quality", "rssi"):
                    if k in val:
                        return coerce(val.get(k))
            return None

        for key in (
            "signalLevel",
            "signal",
            "signalStrength",
            "rssi",
            "connectionQuality",
            "linkQuality",
        ):
            val = coerce(data.get(key))
            if val is not None:
                return val

        # Try nested connection object
        conn_obj = data.get("connection")
        if isinstance(conn_obj, dict):
            for key in ("signal", "level", "quality", "rssi", "value"):
                val = coerce(conn_obj.get(key))
                if val is not None:
                    return val

        return None

    @property
    def native_value(self) -> int | None:
        """Return signal strength."""
        # First check device_states (updated data)
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        val = self._get_signal_value(state)
        if val is not None:
            return val

        # Fallback to initial device data
        val = self._get_signal_value(self._device)
        if val is not None:
            return val

        # Try to find in devices list
        devices = self.coordinator.data.get("devices", [])
        for d in devices:
            if (d.get("id") or d.get("deviceId")) == self._device_id:
                val = self._get_signal_value(d)
                if val is not None:
                    return val
                break

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
            "raw_signal_fields": {
                k: state.get(k) for k in ("signal", "signalLevel", "signalStrength", "rssi", "connectionQuality")
                if state.get(k) is not None
            },
        }


class AjaxTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Ajax temperature sensor."""

    _attr_has_entity_name = True
    _attr_name = "Temperatura"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer"

    def __init__(self, coordinator: AjaxDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)

        display_name = get_display_name(device, self._device_type)

        self._attr_unique_id = f"ajax_{self._device_id}_temperature"
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
            "ajax_id": self._device_id,
        }
