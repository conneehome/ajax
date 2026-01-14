"""Alarm control panel for Ajax integration."""
import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AjaxDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ajax alarm control panel."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]
    hub_id = data["hub_id"]

    async_add_entities([AjaxAlarmControlPanel(coordinator, api, hub_id)])


class AjaxAlarmControlPanel(CoordinatorEntity, AlarmControlPanelEntity):
    """Ajax alarm control panel."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )

    def __init__(self, coordinator: AjaxDataCoordinator, api, hub_id: str):
        """Initialize."""
        super().__init__(coordinator)
        self._api = api
        self._hub_id = hub_id
        self._attr_unique_id = f"ajax_{hub_id}_alarm"
        self._attr_name = "Ajax Alarm"
        self._attr_manufacturer = MANUFACTURER

    @property
    def state(self) -> str:
        """Return current state."""
        hub_state = self.coordinator.data.get("hub_state", {})
        arm_state = hub_state.get("armState", hub_state.get("state", "unknown"))
        
        state_map = {
            "ARM": STATE_ALARM_ARMED_AWAY,
            "ARMED": STATE_ALARM_ARMED_AWAY,
            "PARTIAL_ARM": STATE_ALARM_ARMED_HOME,
            "NIGHT_ARM": STATE_ALARM_ARMED_NIGHT,
            "DISARM": STATE_ALARM_DISARMED,
            "DISARMED": STATE_ALARM_DISARMED,
        }
        
        return state_map.get(str(arm_state).upper(), STATE_ALARM_DISARMED)

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm the alarm."""
        await self._api.arm_hub(self._hub_id, "DISARM")
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm the alarm in away mode."""
        await self._api.arm_hub(self._hub_id, "ARM")
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Arm the alarm in home mode."""
        await self._api.arm_hub(self._hub_id, "PARTIAL_ARM")
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Arm the alarm in night mode."""
        await self._api.arm_hub(self._hub_id, "NIGHT_ARM")
        await self.coordinator.async_request_refresh()
