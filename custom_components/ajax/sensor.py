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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Connee Alarm sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    entities = []
    devices = coordinator.data.get("devices", [])
    states = coordinator.data.get("device_states", {})

    # Add diagnostic connection status sensor (always first)
    entities.append(ConneeAlarmConnectionSensor(coordinator, api, entry))
    
    # Add summary/count sensors for dashboard cards
    entities.append(ConneeAlarmSensorCountSensor(coordinator, entry))
    entities.append(ConneeAlarmSensorOkSensor(coordinator, entry))
    entities.append(ConneeAlarmSensorAlarmSensor(coordinator, entry))
    entities.append(ConneeAlarmSensorOfflineSensor(coordinator, entry))


    for device in devices:
        device_id = _get_device_id(device)
        if not device_id:
            continue

        device_type = _get_device_type(device)
        platform = DEVICE_TYPE_MAP.get(device_type)

        # Skip hub entities here (handled by alarm_control_panel)
        if platform == "alarm_control_panel":
            continue

        # Sensore "Stato" descrittivo: SEMPRE per tutti i dispositivi
        # (fornisce stati leggibili: Aperto/Chiuso, Bagnato/Asciutto, ecc.)
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
        pass  # Signal sensor removed - not useful

        # Temperature sensor:
        has_temp = (
            device_type in TEMPERATURE_DEVICES
            or any(k in state for k in ("temperature", "temp"))
        )
        if has_temp:
            entities.append(ConneeAlarmTemperatureSensor(coordinator, device))

    async_add_entities(entities)


class ConneeAlarmSensor(CoordinatorEntity, SensorEntity):
    """Sensore di stato con testi descrittivi in italiano."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = _get_device_id(device)
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
        """Determina lo stato testuale in base al tipo di sensore."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}

        # 1. Controllo Online
        is_online = state.get("online", state.get("isOnline", True))
        if is_online is False:
            return "Scollegato"

        # 2. Sensori Allagamento (Leaks)
        for leak_key in ("leakDetected", "floodDetected", "waterDetected"):
            if state.get(leak_key) is True:
                return "Bagnato"
        if "leakState" in state:
            ls = str(state.get("leakState")).upper()
            if ls in ("LEAK", "FLOOD", "ALARM"):
                return "Bagnato"
            if ls in ("DRY", "OK"):
                return "Asciutto"

        # 3. Sensori Porta/Finestra (Contact)
        reed = state.get("reedClosed")
        if reed is False:
            return "Aperto"
        if reed is True:
            return "Chiuso"
        
        open_st = state.get("openState")
        if open_st is not None:
            return "Aperto" if open_st else "Chiuso"

        # 4. Sensori Fumo/Temperatura (Fire)
        if state.get("smokeAlarmDetected") is True:
            return "Fumo Rilevato"
        if state.get("temperatureAlarmDetected") is True:
            return "Calore Elevato"

        # 5. Sensori Movimento
        if str(state.get("state", "")).upper() == "ALARM":
            return "Movimento"

        # 6. Sensori Rottura Vetro
        if state.get("glassBreakDetected") is True:
            return "Vetro Rotto"

        # 7. Valvole acqua
        valve_state = state.get("valveState")
        if valve_state is not None:
            vs = str(valve_state).upper()
            if vs == "CLOSED":
                return "Valvola Chiusa"
            if vs == "OPEN":
                return "Valvola Aperta"

        # Fallback Generico
        if state.get("triggered") or state.get("alarm") or state.get("active"):
            return "Allarme"
            
        return "OK"

    @property
    def icon(self) -> str:
        """Cambia icona in base allo stato."""
        val = self.native_value
        if val == "Scollegato":
            return "mdi:wifi-off"
        if val == "Bagnato":
            return "mdi:water-alert"
        if val == "Asciutto":
            return "mdi:water-check"
        if val == "Aperto":
            return "mdi:door-open"
        if val == "Chiuso":
            return "mdi:door-closed"
        if val == "Fumo Rilevato":
            return "mdi:fire-alert"
        if val == "Calore Elevato":
            return "mdi:thermometer-alert"
        if val == "Movimento":
            return "mdi:motion-sensor"
        if val == "Vetro Rotto":
            return "mdi:glass-fragile"
        if val == "Valvola Chiusa":
            return "mdi:valve-closed"
        if val == "Valvola Aperta":
            return "mdi:valve-open"
        if val == "Allarme":
            return "mdi:alert-circle"
        return "mdi:check-circle"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        return {
            "device_type": self._device_type,
            "connee_id": self._device_id,
            "raw_state": state,
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
        self._device_id = _get_device_id(device)
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

    def _get_battery_value(self, data: dict) -> int | None:
        """Extract battery value from data dict, trying multiple field names."""
        # Try direct fields - batteryChargeLevelPercentage is what Ajax API uses
        for key in ("batteryChargeLevelPercentage", "batteryCharge", "batteryLevel", "battery", "batteryPercent"):
            val = data.get(key)
            if val is not None:
                try:
                    return int(val)
                except (ValueError, TypeError):
                    pass
        # Try nested battery object
        batt_obj = data.get("battery")
        if isinstance(batt_obj, dict):
            for key in ("charge", "level", "percent", "percentage"):
                val = batt_obj.get(key)
                if val is not None:
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        pass
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
            if _get_device_id(d) == self._device_id:
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
                k: state.get(k) for k in ("batteryChargeLevelPercentage", "battery", "batteryCharge", "batteryLevel", "batteryPercent")
                if state.get(k) is not None
            },
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
        self._device_id = _get_device_id(device)
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
            "connee_id": self._device_id,
        }


class ConneeAlarmConnectionSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor showing connection status to Connee Gateway."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:cloud-check"

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, api, entry: ConfigEntry):
        """Initialize the connection sensor."""
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self._attr_unique_id = f"ajax_{entry.entry_id}_connection_status"
        self._attr_name = "Connee Alarm Stato Connessione"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"connee_gateway_{entry.entry_id}")},
            name="Connee Gateway",
            manufacturer=MANUFACTURER,
            model="Cloud Gateway",
        )

    @property
    def native_value(self) -> str:
        """Return the connection status."""
        status = self._api.connection_status
        status_map = {
            "connected": "Connesso",
            "backoff": "Sospeso",
            "auth_error": "Errore Autenticazione",
            "disconnected": "Disconnesso",
        }
        return status_map.get(status, status)

    @property
    def icon(self) -> str:
        """Return icon based on status."""
        status = self._api.connection_status
        icons = {
            "connected": "mdi:cloud-check",
            "backoff": "mdi:cloud-alert",
            "auth_error": "mdi:cloud-off-outline",
            "disconnected": "mdi:cloud-question",
        }
        return icons.get(status, "mdi:cloud")

    @property
    def extra_state_attributes(self) -> dict:
        """Return detailed status information."""
        attrs = {
            "status_detail": self._api.connection_status_detail,
            "device_id": self._api.device_id[:8] + "...",
            "email": self._api.email,
        }
        
        if self._api.backoff_remaining_seconds > 0:
            attrs["backoff_remaining_seconds"] = self._api.backoff_remaining_seconds
            attrs["backoff_remaining_minutes"] = round(self._api.backoff_remaining_seconds / 60, 1)
        
        if self._api.token_expires:
            attrs["token_expires"] = self._api.token_expires.isoformat()
        
        if self._api._consecutive_failures > 0:
            attrs["consecutive_failures"] = self._api._consecutive_failures
        
        return attrs

    @property
    def available(self) -> bool:
        """Always available so user can see status."""
        return True


class ConneeAlarmSensorCountSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor counting total devices."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, entry: ConfigEntry):
        """Initialize."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"ajax_{entry.entry_id}_total_sensors"
        self._attr_name = "Connee Sensori Totale"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"connee_gateway_{entry.entry_id}")},
            name="Connee Gateway",
            manufacturer=MANUFACTURER,
            model="Cloud Gateway",
        )

    @property
    def native_value(self) -> int:
        """Return total sensor count."""
        devices = self.coordinator.data.get("devices", [])
        # Exclude hubs from count
        return sum(1 for d in devices if DEVICE_TYPE_MAP.get(_get_device_type(d)) != "alarm_control_panel")

    @property
    def extra_state_attributes(self) -> dict:
        """Return device breakdown."""
        devices = self.coordinator.data.get("devices", [])
        type_counts = {}
        for d in devices:
            dtype = _get_device_type(d)
            type_counts[dtype] = type_counts.get(dtype, 0) + 1
        return {"device_types": type_counts}


class ConneeAlarmSensorOkSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor counting devices in OK state."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:check-circle"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, entry: ConfigEntry):
        """Initialize."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"ajax_{entry.entry_id}_sensors_ok"
        self._attr_name = "Connee Sensori OK"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"connee_gateway_{entry.entry_id}")},
            name="Connee Gateway",
            manufacturer=MANUFACTURER,
            model="Cloud Gateway",
        )

    @property
    def native_value(self) -> int:
        """Return count of OK sensors."""
        devices = self.coordinator.data.get("devices", [])
        states = self.coordinator.data.get("device_states", {})
        count = 0
        for d in devices:
            device_id = _get_device_id(d)
            if not device_id:
                continue
            dtype = _get_device_type(d)
            if DEVICE_TYPE_MAP.get(dtype) == "alarm_control_panel":
                continue
            state = states.get(device_id, {}) if isinstance(states, dict) else {}
            # Check online status
            is_online = state.get("online", state.get("isOnline", True))
            if is_online is False:
                continue
            # Check not in alarm
            if state.get("active") or state.get("triggered") or state.get("alarm"):
                continue
            if str(state.get("state", "")).upper() == "ALARM":
                continue
            count += 1
        return count


class ConneeAlarmSensorAlarmSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor counting devices in ALARM state."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:alert-circle"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, entry: ConfigEntry):
        """Initialize."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"ajax_{entry.entry_id}_sensors_alarm"
        self._attr_name = "Connee Sensori Allarme"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"connee_gateway_{entry.entry_id}")},
            name="Connee Gateway",
            manufacturer=MANUFACTURER,
            model="Cloud Gateway",
        )

    @property
    def native_value(self) -> int:
        """Return count of sensors in alarm state."""
        devices = self.coordinator.data.get("devices", [])
        states = self.coordinator.data.get("device_states", {})
        count = 0
        alarmed_devices = []
        for d in devices:
            device_id = _get_device_id(d)
            if not device_id:
                continue
            dtype = _get_device_type(d)
            if DEVICE_TYPE_MAP.get(dtype) == "alarm_control_panel":
                continue
            state = states.get(device_id, {}) if isinstance(states, dict) else {}
            # Check various alarm indicators
            is_alarm = (
                state.get("active") is True
                or state.get("triggered") is True
                or state.get("alarm") is True
                or str(state.get("state", "")).upper() == "ALARM"
                or str(state.get("alarmState", "")).upper() == "ALARM"
                or state.get("reedClosed") is False  # Door open = alarm for door sensors
                or state.get("leakDetected") is True
                or state.get("smokeAlarmDetected") is True
                or state.get("temperatureAlarmDetected") is True
                or state.get("glassBreakDetected") is True
            )
            if is_alarm:
                count += 1
                alarmed_devices.append(d.get("deviceName") or d.get("name") or device_id)
        return count

    @property
    def extra_state_attributes(self) -> dict:
        """Return list of alarmed devices."""
        devices = self.coordinator.data.get("devices", [])
        states = self.coordinator.data.get("device_states", {})
        alarmed = []
        for d in devices:
            device_id = _get_device_id(d)
            if not device_id:
                continue
            state = states.get(device_id, {}) if isinstance(states, dict) else {}
            is_alarm = (
                state.get("active") is True
                or state.get("triggered") is True
                or state.get("alarm") is True
                or str(state.get("state", "")).upper() == "ALARM"
                or state.get("reedClosed") is False
                or state.get("leakDetected") is True
                or state.get("smokeAlarmDetected") is True
            )
            if is_alarm:
                alarmed.append(d.get("deviceName") or d.get("name") or device_id)
        return {"alarmed_devices": alarmed}


class ConneeAlarmSensorOfflineSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor counting OFFLINE devices."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:wifi-off"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, entry: ConfigEntry):
        """Initialize."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"ajax_{entry.entry_id}_sensors_offline"
        self._attr_name = "Connee Sensori Offline"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"connee_gateway_{entry.entry_id}")},
            name="Connee Gateway",
            manufacturer=MANUFACTURER,
            model="Cloud Gateway",
        )

    @property
    def native_value(self) -> int:
        """Return count of offline sensors."""
        devices = self.coordinator.data.get("devices", [])
        states = self.coordinator.data.get("device_states", {})
        count = 0
        for d in devices:
            device_id = _get_device_id(d)
            if not device_id:
                continue
            dtype = _get_device_type(d)
            if DEVICE_TYPE_MAP.get(dtype) == "alarm_control_panel":
                continue
            state = states.get(device_id, {}) if isinstance(states, dict) else {}
            is_online = state.get("online", state.get("isOnline"))
            if is_online is False:
                count += 1
        return count

    @property
    def extra_state_attributes(self) -> dict:
        """Return list of offline devices."""
        devices = self.coordinator.data.get("devices", [])
        states = self.coordinator.data.get("device_states", {})
        offline = []
        for d in devices:
            device_id = _get_device_id(d)
            if not device_id:
                continue
            state = states.get(device_id, {}) if isinstance(states, dict) else {}
            if state.get("online", state.get("isOnline")) is False:
                offline.append(d.get("deviceName") or d.get("name") or device_id)
        return {"offline_devices": offline}
