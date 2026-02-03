"""Connee Alarm API Client."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import asyncio

from aiohttp import ClientSession, ClientTimeout

from .const import CONNEE_GATEWAY_URL, TOKEN_REFRESH_INTERVAL, VERSION

_LOGGER = logging.getLogger(__name__)

# Backoff settings to avoid Ajax bans
BACKOFF_INITIAL_SECONDS = 60  # 1 minute initial backoff
BACKOFF_MAX_SECONDS = 900  # 15 minutes max backoff
BACKOFF_MULTIPLIER = 2


class ConneeAlarmApiClient:
    """Client for Connee Alarm API."""

    # Connection status constants
    STATUS_CONNECTED = "connected"
    STATUS_BACKOFF = "backoff"
    STATUS_AUTH_ERROR = "auth_error"
    STATUS_DISCONNECTED = "disconnected"

    def __init__(
        self,
        session: ClientSession,
        email: str,
        password: str,
        device_id: str,  # Unique device ID per installation
    ):
        """Initialize the API client."""
        self.session = session
        self.email = email
        self.password = password
        self.device_id = device_id  # Persistent unique ID for this client
        self.session_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.hub_id: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        self._login_lock = False  # Prevent concurrent login attempts
        self._backoff_until: Optional[datetime] = None  # Backoff timer
        self._consecutive_failures = 0  # Track failures for exponential backoff
        self._last_error: Optional[str] = None  # Last error message for diagnostics
        self._connection_status: str = self.STATUS_DISCONNECTED

    @property
    def connection_status(self) -> str:
        """Return current connection status."""
        if self._is_in_backoff():
            return self.STATUS_BACKOFF
        if self._last_error and "401" in str(self._last_error):
            return self.STATUS_AUTH_ERROR
        if self.session_token:
            return self.STATUS_CONNECTED
        return self.STATUS_DISCONNECTED

    @property
    def connection_status_detail(self) -> str:
        """Return detailed status message."""
        if self._is_in_backoff():
            remaining = int((self._backoff_until - datetime.now()).total_seconds())
            return f"Sospeso per sicurezza. Riprovo tra {remaining // 60} min {remaining % 60} sec"
        if self._last_error:
            if "401" in str(self._last_error) or "403" in str(self._last_error):
                return "Errore autenticazione. Verifica le credenziali o la licenza Connee."
            return f"Errore: {self._last_error[:100]}"
        if self.session_token:
            return "Connesso al gateway Connee"
        return "Non connesso"

    @property
    def backoff_remaining_seconds(self) -> int:
        """Return seconds remaining in backoff, or 0 if not in backoff."""
        if not self._is_in_backoff():
            return 0
        return max(0, int((self._backoff_until - datetime.now()).total_seconds()))

    def _is_in_backoff(self) -> bool:
        """Check if we're in backoff period."""
        if self._backoff_until is None:
            return False
        return datetime.now() < self._backoff_until

    def _set_backoff(self) -> None:
        """Set backoff timer with exponential increase."""
        self._consecutive_failures += 1
        backoff_seconds = min(
            BACKOFF_INITIAL_SECONDS * (BACKOFF_MULTIPLIER ** (self._consecutive_failures - 1)),
            BACKOFF_MAX_SECONDS
        )
        self._backoff_until = datetime.now() + timedelta(seconds=backoff_seconds)
        _LOGGER.warning(
            "Setting backoff for %d seconds (attempt %d). Next retry after: %s",
            backoff_seconds,
            self._consecutive_failures,
            self._backoff_until.isoformat()
        )

    def _clear_backoff(self) -> None:
        """Clear backoff on success."""
        self._consecutive_failures = 0
        self._backoff_until = None

    async def _call_gateway(
        self,
        action: str,
        body: Optional[Dict] = None,
    ) -> Any:
        """Call Connee Gateway API."""
        # Check backoff before making requests
        if self._is_in_backoff():
            remaining = (self._backoff_until - datetime.now()).total_seconds()
            _LOGGER.warning(
                "In backoff period. %d seconds remaining. Skipping request: %s",
                int(remaining),
                action
            )
            return {"error": 429, "message": f"In backoff period. Retry in {int(remaining)}s"}

        url = f"{CONNEE_GATEWAY_URL}?action={action}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"ConneeAlarm/{VERSION} (Device {self.device_id})",
            "X-Device-Id": self.device_id,
        }

        request_body = body or {}
        if self.session_token:
            request_body["sessionToken"] = self.session_token
        # Always include deviceId in requests
        request_body["deviceId"] = self.device_id

        try:
            timeout = ClientTimeout(total=30)
            async with self.session.request(
                "POST", url, json=request_body, headers=headers, timeout=timeout
            ) as resp:
                result = await resp.json()

                # Handle rate limiting / auth errors with backoff
                if resp.status in (401, 403, 429):
                    error_msg = result.get("message", f"HTTP {resp.status}") if isinstance(result, dict) else f"HTTP {resp.status}"
                    self._last_error = f"{resp.status}: {error_msg}"
                    _LOGGER.error(
                        "Auth/rate limit error (HTTP %d): %s. Activating backoff.",
                        resp.status,
                        result
                    )
                    self._set_backoff()
                    return {"error": resp.status, "message": error_msg}

                if resp.status == 200 and isinstance(result, dict) and result.get("success"):
                    self._clear_backoff()  # Success - clear any backoff
                    self._last_error = None  # Clear error on success
                    self._connection_status = self.STATUS_CONNECTED
                    return result.get("data")

                if isinstance(result, dict):
                    error_msg = result.get("error", f"HTTP {resp.status}")
                else:
                    error_msg = f"HTTP {resp.status}"

                self._last_error = str(error_msg)
                _LOGGER.error("Gateway error: %s", error_msg)
                return {"error": resp.status, "message": error_msg}
        except asyncio.TimeoutError:
            self._last_error = "Request timeout"
            _LOGGER.error("Gateway request timeout for action: %s", action)
            return {"error": -1, "message": "Request timeout"}
        except Exception as e:
            self._last_error = str(e)
            _LOGGER.error("Gateway request error: %s", e)
            return {"error": -1, "message": str(e)}

    async def login(self) -> bool:
        """Login via Connee Gateway."""
        # If we already have a valid token, skip login
        if self.session_token and self.token_expires:
            if datetime.now() < self.token_expires:
                _LOGGER.debug("Using existing valid session token")
                return True

        # Prevent concurrent login attempts
        if self._login_lock:
            _LOGGER.debug("Login already in progress, waiting...")
            await asyncio.sleep(2)
            return self.session_token is not None

        # Check backoff before attempting login
        if self._is_in_backoff():
            remaining = (self._backoff_until - datetime.now()).total_seconds()
            _LOGGER.error(
                "Cannot login: in backoff period. %d seconds remaining.",
                int(remaining)
            )
            return False

        self._login_lock = True
        try:
            result = await self._call_gateway(
                "login",
                {
                    "email": self.email,
                    "password": self.password,
                    "deviceId": self.device_id,
                },
            )

            if isinstance(result, dict) and "error" not in result:
                self.session_token = (
                    result.get("sessionToken")
                    or result.get("token")
                    or result.get("session", {}).get("token")
                )
                self.user_id = (
                    result.get("userId")
                    or result.get("user_id")
                    or result.get("id")
                    or result.get("user", {}).get("id")
                )

                if self.session_token:
                    self.token_expires = datetime.now() + timedelta(
                        seconds=TOKEN_REFRESH_INTERVAL
                    )
                    self._clear_backoff()
                    _LOGGER.info("Login successful via Connee Gateway (device: %s)", self.device_id[:8])
                    return True

            error_msg = result.get("message", "Login failed") if isinstance(result, dict) else "Login failed"
            _LOGGER.error("Login failed: %s", error_msg)
            return False
        finally:
            self._login_lock = False

    async def refresh_token(self) -> bool:
        """Refresh session token."""
        # Clear current token to force re-login
        self.session_token = None
        self.token_expires = None
        return await self.login()

    async def get_hubs(self) -> List[Dict[str, Any]]:
        """Get user hubs."""
        if not self.user_id:
            return []

        result = await self._call_gateway("get-user-hubs", {
            "userId": self.user_id,
            "email": self.email,  # Pass email to update last_used_at
        })

        if isinstance(result, dict) and "error" in result:
            return []

        hubs_raw = []
        if isinstance(result, list):
            hubs_raw = result
        elif isinstance(result, dict):
            hubs_raw = result.get("hubs") or result.get("data") or []

        hubs = []
        for h in hubs_raw:
            hub_id = h.get("hubId") or h.get("id") or h.get("deviceId")
            if hub_id:
                hubs.append({
                    "id": hub_id,
                    "hubId": hub_id,
                    "name": h.get("name") or h.get("hubName") or f"Hub {hub_id}",
                    **h,
                })
        return hubs

    async def get_hub_devices(self, hub_id: str) -> List[Dict[str, Any]]:
        """Get hub devices."""
        if not self.user_id:
            return []

        result = await self._call_gateway(
            "get-hub-devices",
            {
                "userId": self.user_id,
                "hubId": hub_id,
                "email": self.email,  # Pass email to update last_used_at
            },
        )

        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "error" in result:
            return []

        devices = result.get("devices") or result.get("data") or []
        return devices if isinstance(devices, list) else []

    async def get_hub_state(self, hub_id: str) -> Dict[str, Any]:
        """Get hub state."""
        if not self.user_id:
            return {}

        result = await self._call_gateway(
            "get-hub",
            {
                "userId": self.user_id,
                "hubId": hub_id,
                "email": self.email,  # Pass email to update last_used_at
            },
        )

        if isinstance(result, dict) and "error" in result:
            return {}
        return result if isinstance(result, dict) else {}

    async def get_device_states(self, hub_id: str) -> List[Dict[str, Any]]:
        """Get device states."""
        if not self.user_id:
            return []
        result = await self._call_gateway("get-all-device-states", {
            "userId": self.user_id,
            "hubId": hub_id,
            "email": self.email,  # Pass email to update last_used_at
        })
        if "error" in result:
            return []
        return result if isinstance(result, list) else result.get("data", [])

    async def arm_hub(self, hub_id: str, arm_state: str) -> bool:
        """Arm/disarm hub."""
        if not self.user_id:
            return False
        result = await self._call_gateway("arm-hub", {
            "userId": self.user_id,
            "hubId": hub_id,
            "armState": arm_state,
        })
        return "error" not in result

    async def control_valve(self, device_id: str, valve_state: str) -> bool:
        """Control WaterStop valve (OPEN/CLOSED)."""
        if not self.user_id or not self.hub_id:
            _LOGGER.error("Cannot control valve: user_id or hub_id not set")
            return False
        
        _LOGGER.info("Controlling valve %s: %s", device_id, valve_state)
        
        result = await self._call_gateway("control-valve", {
            "userId": self.user_id,
            "hubId": self.hub_id,
            "targetDeviceId": device_id,
            "valveState": valve_state,
        })
        
        if isinstance(result, dict) and "error" in result:
            _LOGGER.error("Valve control failed: %s", result.get("message", "Unknown error"))
            return False
        
        _LOGGER.info("Valve control successful for %s", device_id)
        return True

    async def control_switch(self, device_id: str, switch_state: bool) -> bool:
        """Control Socket/WallSwitch/Relay (ON/OFF)."""
        if not self.user_id or not self.hub_id:
            _LOGGER.error("Cannot control switch: user_id or hub_id not set")
            return False
        
        state_str = "ON" if switch_state else "OFF"
        _LOGGER.info("Controlling switch %s: %s", device_id, state_str)
        
        result = await self._call_gateway("control-switch", {
            "userId": self.user_id,
            "hubId": self.hub_id,
            "targetDeviceId": device_id,
            "switchState": state_str,
        })
        
        if isinstance(result, dict) and "error" in result:
            _LOGGER.error("Switch control failed: %s", result.get("message", "Unknown error"))
            return False
        
        _LOGGER.info("Switch control successful for %s", device_id)
        return True

