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

    entities = [ConneeAlarmControlPanel(coordinator, api, hub_id)]
    # v2.1.9: una entita' di sola lettura per ogni zona (gruppo) della centrale
    for g in (coordinator.data.get("groups") or []):
        gid = g.get("id") or g.get("groupId")
        if gid:
            entities.append(ConneeAlarmGroupPanel(coordinator, hub_id, str(gid), g.get("groupName") or g.get("name") or f"Zona {gid}"))
    async_add_entities(entities)


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
        self._last_valid_state: AlarmControlPanelState | None = None
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

        # v2.1.5: stato sconosciuto/vuoto -> mantieni l'ultimo stato valido (mai falso DISARMED)
        if arm_state in ("UNKNOWN", "NONE", ""):
            return self._last_valid_state

        # Ajax returns various states:
        # ARMED, DISARMED, ARMED_NIGHT_MODE_ON, DISARMED_NIGHT_MODE_ON,
        # DISARMED_NIGHT_MODE_OFF, PARTIAL, etc.

        # Precedence matters:
        # 1) NIGHT_MODE_ON can appear with both ARMED_ and DISARMED_ prefix
        # 2) Any DISARM* state that is NOT NIGHT_MODE_ON must map to DISARMED
        #    (e.g. DISARMED_NIGHT_MODE_OFF)
        # 3) PARTIAL
        # 4) ARMED/ARM
        # 5) NIGHT fallback (but ignore NIGHT_MODE_OFF)
        if "NIGHT_MODE_ON" in arm_state:
            self._last_valid_state = AlarmControlPanelState.ARMED_NIGHT
            return self._last_valid_state
        if "DISARM" in arm_state:
            self._last_valid_state = AlarmControlPanelState.DISARMED
            return self._last_valid_state
        if "PARTIAL" in arm_state:
            self._last_valid_state = AlarmControlPanelState.ARMED_HOME
            return self._last_valid_state
        if arm_state in ("ARM", "ARMED") or ("ARMED" in arm_state and "DISARM" not in arm_state):
            self._last_valid_state = AlarmControlPanelState.ARMED_AWAY
            return self._last_valid_state
        if "NIGHT" in arm_state and "NIGHT_MODE_OFF" not in arm_state:
            self._last_valid_state = AlarmControlPanelState.ARMED_NIGHT
            return self._last_valid_state

        # v2.1.5: stato non riconosciuto -> mantengo l'ultimo stato valido (mai "disarmed" di default)
        return self._last_valid_state

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


class ConneeAlarmGroupPanel(CoordinatorEntity, AlarmControlPanelEntity):
    """Zona (gruppo) Ajax: solo lettura, inserita o disinserita."""

    _attr_has_entity_name = False
    _attr_supported_features = AlarmControlPanelEntityFeature(0)
    _attr_code_arm_required = False

    def __init__(self, coordinator, hub_id: str, group_id: str, name: str):
        super().__init__(coordinator)
        self._hub_id = hub_id
        self._group_id = group_id
        self._attr_unique_id = f"ajax_{hub_id}_group_{group_id}"
        self._attr_name = f"Zona {name}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, hub_id)})

    @property
    def _group(self) -> dict:
        for g in (self.coordinator.data.get("groups") or []):
            if str(g.get("id") or g.get("groupId")) == self._group_id:
                return g
        return {}

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        g = self._group
        raw = g.get("state", g.get("armState", g.get("groupState", g.get("armed"))))
        if isinstance(raw, bool):
            return AlarmControlPanelState.ARMED_AWAY if raw else AlarmControlPanelState.DISARMED
        t = str(raw or "").upper()
        if not t or t in ("UNKNOWN", "NONE"):
            return None
        if "DISARM" in t:
            return AlarmControlPanelState.DISARMED
        if "ARM" in t:
            return AlarmControlPanelState.ARMED_AWAY
        return None

    @property
    def extra_state_attributes(self) -> dict:
        return {"group_id": self._group_id, "dati_zona": self._group}
