"""Valve entities for Connee Alarm integration (WaterStop).

Apri/chiudi dal comando ufficiale Ajax POST .../devices/{id}/command
(SWITCH_ON / SWITCH_OFF, provato il 3/11/2026).
"""
import asyncio
import logging
from typing import Any

from homeassistant.components.valve import ValveEntity, ValveDeviceClass, ValveEntityFeature
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
    """Set up Connee Alarm valve entities (WaterStop) - read-only."""
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

        if platform == "valve":
            entities.append(ConneeAlarmValve(coordinator, device, api))

    _LOGGER.info("Setting up %d valve entities (read-only)", len(entities))
    async_add_entities(entities)


class ConneeAlarmValve(CoordinatorEntity, ValveEntity):
    """Connee Alarm WaterStop valve (apri/chiudi con il comando ufficiale Ajax)."""

    _attr_has_entity_name = False
    _attr_device_class = ValveDeviceClass.WATER
    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
    _attr_reports_position = False

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, device: dict, api):
        """Initialize."""
        super().__init__(coordinator)
        self._device = device
        self._device_id = device.get("id") or device.get("deviceId")
        self._device_type = _get_device_type(device)
        self._api = api

        display_name = _get_display_name(device, self._device_type)

        self._attr_unique_id = f"ajax_{self._device_id}_valve"
        self._attr_name = display_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=display_name,
            manufacturer=MANUFACTURER,
            model=self._device_type,
        )

    @property
    def is_closed(self) -> bool | None:
        """Return true if valve is closed."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}

        valve_state = state.get("valveState")
        if valve_state is not None:
            return str(valve_state).upper() == "CLOSED"

        return None

    @property
    def is_opening(self) -> bool:
        """Return true if valve is opening."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        motor_state = state.get("motorState", "")
        return str(motor_state).upper() == "OPENING"

    @property
    def is_closing(self) -> bool:
        """Return true if valve is closing."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}
        motor_state = state.get("motorState", "")
        return str(motor_state).upper() == "CLOSING"

    async def _send(self, valve_state: str) -> None:
        ok = await self._api.control_valve(self._device_id, valve_state)
        if not ok:
            raise HomeAssistantError(f"Comando valvola {valve_state} non riuscito")
        # La valvola ci mette qualche secondo: rileggo lo stato dopo 6 e 15 secondi, in background
        self.hass.async_create_task(self._rileggi_stato())

    async def _rileggi_stato(self) -> None:
        for attesa in (6, 9):
            await asyncio.sleep(attesa)
            await self.coordinator.async_request_refresh()

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Apri la valvola."""
        await self._send("OPEN")

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Chiudi la valvola."""
        await self._send("CLOSED")

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        states = self.coordinator.data.get("device_states", {})
        state = states.get(self._device_id, {}) if isinstance(states, dict) else {}

        attrs = {
            "device_type": self._device_type,
            "connee_id": self._device_id,
        }

        # WaterStop specific attributes
        for k in ("valveState", "motorState", "tempProtectState", "extPower", 
                  "preventionEnable", "preventionDaysPeriod", "errorDescriptions",
                  "batteryChargeLevelPercentage", "signalLevel", "firmwareVersion"):
            if k in state:
                attrs[k] = state.get(k)

        return attrs
