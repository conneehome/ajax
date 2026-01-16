"""Alarm control panel for Connee Alarm integration."""
import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, MANUFACTURER
from .coordinator import ConneeAlarmDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Connee Alarm control panel."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]
    hub_id = data["hub_id"]

    async_add_entities([ConneeAlarmControlPanel(coordinator, api, hub_id)])


class ConneeAlarmControlPanel(CoordinatorEntity, AlarmControlPanelEntity):
    """Connee Alarm control panel."""

    _attr_has_entity_name = True
    _attr_code_required = False
    _attr_code_arm_required = False
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )

    def __init__(self, coordinator: ConneeAlarmDataCoordinator, api, hub_id: str):
        """Initialize."""
        super().__init__(coordinator)
        self._api = api
        self._hub_id = hub_id
        self._attr_unique_id = f"ajax_{hub_id}_panel"
        self._attr_name = "Pannello Allarme"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the hub."""
        hub_state = self.coordinator.data.get("hub_state", {})
        hub_name = hub_state.get("name") or hub_state.get("hubName") or "Ajax Hub"
        model = hub_state.get("model") or hub_state.get("type") or "Hub"
        return DeviceInfo(
            identifiers={(DOMAIN, self._hub_id)},
            name=hub_name,
            manufacturer=MANUFACTURER,
            model=model,
        )

    @property
    def code_format(self) -> str | None:
        return None

    @property
    def code_arm_required(self) -> bool:
        return False

    @property
    def code_required(self) -> bool:
        return False

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return current alarm state."""
        hub_state = self.coordinator.data.get("hub_state", {})
        arm_state = str(hub_state.get("armState", hub_state.get("state", "unknown"))).upper()
        
        # Ajax returns various states:
        # ARMED, DISARMED, ARMED_NIGHT_MODE_ON, ARMED_NIGHT_MODE_OFF, PARTIAL, etc.
        
        # Check for ARMED variants (ARMED_NIGHT_MODE_OFF is still armed, just with night mode off)
        if "ARMED" in arm_state and "DISARM" not in arm_state:
            if "NIGHT_MODE_ON" in arm_state:
                return AlarmControlPanelState.ARMED_NIGHT
            elif "PARTIAL" in arm_state:
                return AlarmControlPanelState.ARMED_HOME
            else:
                # ARMED, ARMED_NIGHT_MODE_OFF, etc. = armed away
                return AlarmControlPanelState.ARMED_AWAY
        
        if "DISARM" in arm_state:
            return AlarmControlPanelState.DISARMED
        
        if arm_state in ("ARM", "ARMED"):
            return AlarmControlPanelState.ARMED_AWAY
        
        if "NIGHT" in arm_state:
            return AlarmControlPanelState.ARMED_NIGHT
            
        if "PARTIAL" in arm_state:
            return AlarmControlPanelState.ARMED_HOME
        
        # Default to disarmed for unknown states
        return AlarmControlPanelState.DISARMED

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm the alarm."""
        success, error_msg = await self._api.arm_hub(self._hub_id, "DISARM")
        if not success:
            raise HomeAssistantError(f"Errore Ajax: {error_msg}. Prova a ricaricare l'integrazione.")
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm the alarm in away mode."""
        success, error_msg = await self._api.arm_hub(self._hub_id, "ARM")
        if not success:
            raise HomeAssistantError(f"Errore Ajax: {error_msg}. Prova a ricaricare l'integrazione.")
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Arm the alarm in home mode."""
        success, error_msg = await self._api.arm_hub(self._hub_id, "PARTIAL_ARM")
        if not success:
            raise HomeAssistantError(f"Errore Ajax: {error_msg}. Prova a ricaricare l'integrazione.")
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Arm the alarm in night mode."""
        success, error_msg = await self._api.arm_hub(self._hub_id, "NIGHT_ARM")
        if not success:
            raise HomeAssistantError(f"Errore Ajax: {error_msg}. Prova a ricaricare l'integrazione.")
        await self.coordinator.async_request_refresh()
