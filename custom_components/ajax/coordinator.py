"""Data coordinator for Connee Alarm integration."""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ConneeAlarmApiClient
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ConneeAlarmDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Connee Alarm data."""

    def __init__(self, hass: HomeAssistant, api: ConneeAlarmApiClient, hub_id: str):
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.hub_id = hub_id
        

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API."""
        try:
            # Refresh token if needed
            if self.api.token_expires:
                from datetime import datetime
                if datetime.now() > self.api.token_expires:
                    await self.api.refresh_token()

            # Get hub state
            hub_state = await self.api.get_hub_state(self.hub_id)
            
            # Get devices
            devices = await self.api.get_hub_devices(self.hub_id)
            
            # Get device states
            device_states = await self.api.get_device_states(self.hub_id)
            
            # Map device states by ID (normalize to string to avoid mismatches)
            states_map: Dict[str, Any] = {}
            if isinstance(device_states, list):
                for state in device_states:
                    raw_id = (
                        state.get("deviceId")
                        or state.get("id")
                        or state.get("device_id")
                        or (state.get("device") or {}).get("deviceId")
                        or (state.get("device") or {}).get("id")
                    )
                    if raw_id is None:
                        continue
                    states_map[str(raw_id)] = state

            return {
                "hub_state": hub_state,
                "devices": devices,
                "device_states": states_map,
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
