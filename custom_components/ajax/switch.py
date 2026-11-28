"""Switch entities for Connee Alarm (Socket, WallSwitch, Relay).

v2.2.1 (27/11/2026): le prese si comandano davvero, con lo stesso comando ufficiale delle valvole
(POST .../devices/{id}/command SWITCH_ON/SWITCH_OFF). Prima erano in sola lettura e in HA
sembravano un pulsante a impulso (ON e subito OFF).
"""
import asyncio
import logging
import time
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
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

    _LOGGER.info("Setting up %d switch entities", len(entities))
    async_add_entities(entities)


class ConneeAlarmSwitch(CoordinatorEntity, SwitchEntity):
    """Connee Alarm Socket/WallSwitch/Relay."""

    _attr_has_entity_name = False
    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict, api):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)
        self._api = api
        # stato atteso dopo un comando: vale finche' Ajax non lo conferma (max 30 s)
        self._atteso: bool | None = None
        self._atteso_t = 0.0

        display_name = _get_display_name(device, self._device_type)

        self._attr_unique_id = f"ajax_{self._device_id}_switch"
        self._attr_name = display_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=display_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

    def _stato_ajax(self) -> bool | None:
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        for key in ("switchState", "powerState", "relayState", "on", "state"):
            val = state.get(key)
            if val is None:
                continue
            if isinstance(val, bool):
                return val
            if isinstance(val, (list, tuple, set)):
                # le prese Ajax mandano un elenco di flag: vuoto = spenta
                flag = {str(x).upper() for x in val}
                return bool(flag & {"SWITCHED_ON", "SWITCH_ON", "ON", "RELAY_ON"})
            if isinstance(val, str):
                v = val.upper()
                if key == "state" and v in ("PASSIVE", "ACTIVE", "ONLINE", "OFFLINE"):
                    continue  # stato del dispositivo, non della presa
                return v in ("ON", "TRUE", "1", "ENABLED", "SWITCHED_ON")
            if isinstance(val, (int, float)):
                return val > 0
        return None

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        reale = self._stato_ajax()
        if self._atteso is not None:
            if reale == self._atteso or time.monotonic() - self._atteso_t > 30:
                self._atteso = None
            else:
                return self._atteso
        return reale

    async def _comando(self, acceso: bool) -> None:
        ok = await self._api.control_switch(self._device_id, acceso, self._device_type)
        if not ok:
            raise HomeAssistantError(f"Comando presa {'ON' if acceso else 'OFF'} non riuscito")
        self._atteso, self._atteso_t = acceso, time.monotonic()
        self.async_write_ha_state()
        self.hass.async_create_task(self._rileggi_stato())

    async def _rileggi_stato(self) -> None:
        for attesa in (4, 8):
            await asyncio.sleep(attesa)
            await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Accendi la presa."""
        await self._comando(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Spegni la presa."""
        await self._comando(False)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}

        attrs = {
            "device_type": self._device_type,
            "connee_id": self._device_id,
        }

        # Socket/Relay specific attributes
        for k in ("switchState", "state", "powerState", "relayState", 
                  "power", "voltage", "current", "energy", "extPower",
                  "batteryChargeLevelPercentage", "signalLevel", "firmwareVersion"):
            if k in state:
                attrs[k] = state.get(k)

        return attrs
