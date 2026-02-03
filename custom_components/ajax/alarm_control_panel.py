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
        
        _LOGGER.debug("Raw arm_state from API: %s", arm_state)
        
        # Ajax returns combined states like:
        # ARMED, DISARMED, ARMED_NIGHT_MODE_ON, ARMED_NIGHT_MODE_OFF, 
        # DISARMED_NIGHT_MODE_ON, DISARMED_NIGHT_MODE_OFF, PARTIAL, etc.
        
        # PRIORITY 1: Check for NIGHT_MODE_ON first (regardless of armed/disarmed prefix)
        # When night mode is ON, we show ARMED_NIGHT in HA
        if "NIGHT_MODE_ON" in arm_state:
            _LOGGER.debug("Detected NIGHT_MODE_ON -> ARMED_NIGHT")
            return AlarmControlPanelState.ARMED_NIGHT
        
        # PRIORITY 2: Check for ARMED states (excluding night mode which was handled above)
        if "ARMED" in arm_state and "DISARM" not in arm_state:
            if "PARTIAL" in arm_state:
                _LOGGER.debug("Detected ARMED_PARTIAL -> ARMED_HOME")
                return AlarmControlPanelState.ARMED_HOME
            else:
                # ARMED, ARMED_NIGHT_MODE_OFF = armed away
                _LOGGER.debug("Detected ARMED -> ARMED_AWAY")
                return AlarmControlPanelState.ARMED_AWAY
        
        # PRIORITY 3: Check for DISARMED states
        if "DISARM" in arm_state:
            _LOGGER.debug("Detected DISARMED -> DISARMED")
            return AlarmControlPanelState.DISARMED
        
        # Fallback checks
        if arm_state in ("ARM", "ARMED"):
            return AlarmControlPanelState.ARMED_AWAY
        
        if "NIGHT" in arm_state:
            return AlarmControlPanelState.ARMED_NIGHT
            
        if "PARTIAL" in arm_state:
            return AlarmControlPanelState.ARMED_HOME
        
        # Default to disarmed for unknown states
        _LOGGER.warning("Unknown arm_state '%s', defaulting to DISARMED", arm_state)
        return AlarmControlPanelState.DISARMED

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm the alarm."""
        _LOGGER.info("Sending DISARM command to hub %s", self._hub_id)
        result = await self._api.arm_hub(self._hub_id, "DISARM")
        _LOGGER.info("DISARM command result: %s", result)
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm the alarm in away mode."""
        _LOGGER.info("Sending ARM command to hub %s", self._hub_id)
        result = await self._api.arm_hub(self._hub_id, "ARM")
        _LOGGER.info("ARM command result: %s", result)
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Arm the alarm in home/partial mode (maps to standard ARM)."""
        _LOGGER.info("Sending ARM (home mode) command to hub %s", self._hub_id)
        result = await self._api.arm_hub(self._hub_id, "ARM")
        _LOGGER.info("ARM (home mode) command result: %s", result)
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Arm the alarm in night mode (uses NIGHT_MODE_ON)."""
        _LOGGER.info("Sending NIGHT_MODE_ON command to hub %s", self._hub_id)
        result = await self._api.arm_hub(self._hub_id, "NIGHT_MODE_ON")
        _LOGGER.info("NIGHT_MODE_ON command result: %s", result)
        await self.coordinator.async_request_refresh()
