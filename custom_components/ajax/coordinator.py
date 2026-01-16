"""Data coordinator for Connee Alarm integration."""
import asyncio
import logging
from datetime import timedelta, datetime
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import ConneeAlarmApiClient
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Force re-login every 12 hours as a safety measure
FORCE_RELOGIN_INTERVAL_HOURS = 12


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
        self._last_forced_login: datetime | None = None
        self._consecutive_failures = 0
        

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API."""
        try:
            # Check if auth has permanently failed
            if self.api._auth_failed:
                _LOGGER.error("Authentication permanently failed. Raising ConfigEntryAuthFailed.")
                raise ConfigEntryAuthFailed(
                    "Autenticazione fallita. Ricarica l'integrazione o verifica le credenziali."
                )
            
            # Force re-login every N hours as a safety measure against stale sessions
            now = datetime.now()
            should_force_relogin = (
                self._last_forced_login is None or
                (now - self._last_forced_login).total_seconds() > FORCE_RELOGIN_INTERVAL_HOURS * 3600
            )
            
            if should_force_relogin:
                _LOGGER.info("Forcing periodic re-login (every %d hours)", FORCE_RELOGIN_INTERVAL_HOURS)
                login_success = await self.api.refresh_token()
                if login_success:
                    self._last_forced_login = now
                    _LOGGER.info("Periodic re-login successful")
                else:
                    _LOGGER.warning("Periodic re-login failed, will retry on next update")
            
            # Refresh token if expired
            if self.api.token_expires:
                if datetime.now() > self.api.token_expires:
                    await self.api.refresh_token()

            # Get hub state
            hub_state = await self.api.get_hub_state(self.hub_id)
            
            # Check for auth failure in response
            if isinstance(hub_state, dict) and hub_state.get("auth_failed"):
                self._consecutive_failures += 1
                if self._consecutive_failures >= 3:
                    raise ConfigEntryAuthFailed(
                        "Autenticazione fallita dopo 3 tentativi. Ricarica l'integrazione."
                    )
            else:
                self._consecutive_failures = 0  # Reset on success
            
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
        except ConfigEntryAuthFailed:
            raise  # Re-raise auth failures
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
