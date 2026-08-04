"""Connee Alarm API Client - v2.0 (Direct Ajax API)."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import asyncio
import hashlib
import base64

from aiohttp import ClientSession, ClientTimeout

from .const import CONNEE_GATEWAY_URL, AJAX_API_BASE, TOKEN_REFRESH_INTERVAL, VERSION

_LOGGER = logging.getLogger(__name__)

# Backoff settings to avoid Ajax bans
BACKOFF_INITIAL_SECONDS = 60  # 1 minute initial backoff
BACKOFF_MAX_SECONDS = 900  # 15 minutes max backoff
BACKOFF_MULTIPLIER = 2

# Batch size for parallel device state requests
DEVICE_STATE_BATCH_SIZE = 5


class ConneeAlarmApiClient:
    """Client for Connee Alarm API - Direct Ajax communication."""

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
        device_id: str,
    ):
        """Initialize the API client."""
        self.session = session
        self.email = email
        self.password = password
        self.device_id = device_id
        self.session_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.hub_id: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        self._ajax_api_key: Optional[str] = None  # Obtained from gateway at login
        self._login_lock = False
        self._backoff_until: Optional[datetime] = None
        self._consecutive_failures = 0
        self._last_error: Optional[str] = None
        self._connection_status: str = self.STATUS_DISCONNECTED
        self._auth_failed: bool = False

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
            mode = "diretto" if self._ajax_api_key else "gateway"
            return f"Connesso ad Ajax ({mode})"
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
            "Setting backoff for %d seconds (attempt %d)",
            backoff_seconds,
            self._consecutive_failures,
        )

    def _clear_backoff(self) -> None:
        """Clear backoff on success."""
        self._consecutive_failures = 0
        self._backoff_until = None

    # ── Gateway calls (login + token verification only) ──

    async def _call_gateway(self, action: str, body: Optional[Dict] = None) -> Any:
        """Call Connee Gateway for login/auth only."""
        if self._is_in_backoff():
            remaining = (self._backoff_until - datetime.now()).total_seconds()
            return {"error": 429, "message": f"In backoff period. Retry in {int(remaining)}s"}

        url = f"{CONNEE_GATEWAY_URL}?action={action}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"ConneeAlarm/{VERSION} (Device {self.device_id})",
            "X-Device-Id": self.device_id,
        }
        request_body = body or {}
        request_body["deviceId"] = self.device_id

        # Retry on transient network/DNS errors (HA host DNS can fail right after boot)
        NETWORK_RETRIES = 3
        RETRY_DELAYS = [2, 5, 10]
        last_network_error = None

        for attempt in range(NETWORK_RETRIES):
            try:
                timeout = ClientTimeout(total=30)
                async with self.session.request(
                    "POST", url, json=request_body, headers=headers, timeout=timeout
                ) as resp:
                    result = await resp.json()

                    if resp.status in (401, 403):
                        error_msg = result.get("message", f"HTTP {resp.status}") if isinstance(result, dict) else f"HTTP {resp.status}"
                        self._last_error = f"{resp.status}: {error_msg}"
                        self._set_backoff()
                        return {"error": resp.status, "message": error_msg, "auth_failed": True}

                    if resp.status == 429:
                        self._set_backoff()
                        return {"error": 429, "message": "Rate limited"}

                    if resp.status == 200 and isinstance(result, dict) and result.get("success"):
                        self._clear_backoff()
                        self._last_error = None
                        self._auth_failed = False
                        return result.get("data")

                    error_msg = result.get("error", f"HTTP {resp.status}") if isinstance(result, dict) else f"HTTP {resp.status}"
                    self._last_error = str(error_msg)
                    return {"error": resp.status, "message": error_msg}
            except asyncio.TimeoutError:
                last_network_error = "Gateway timeout"
            except Exception as e:
                last_network_error = str(e)

            if attempt < NETWORK_RETRIES - 1:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                _LOGGER.warning(
                    "Gateway network error (%s). Retry %d/%d in %ss...",
                    last_network_error, attempt + 1, NETWORK_RETRIES - 1, delay,
                )
                await asyncio.sleep(delay)

        self._last_error = last_network_error or "Gateway network error"
        return {"error": -1, "message": self._last_error}

    # ── Direct Ajax API calls (all polling) ──

    async def _call_ajax_direct(
        self,
        endpoint: str,
        method: str = "GET",
        body: Optional[Dict] = None,
        retry_count: int = 0,
    ) -> Any:
        """Call Ajax API directly (no cloud proxy)."""
        MAX_RETRIES = 2

        if self._is_in_backoff():
            return {"error": 429, "message": "In backoff period"}

        if not self._ajax_api_key:
            _LOGGER.error("No Ajax API key available. Re-login required.")
            return {"error": 401, "message": "No API key"}

        url = f"{AJAX_API_BASE}{endpoint}"
        headers = {
            "X-Api-Key": self._ajax_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"ConneeAlarm/{VERSION} (Device {self.device_id})",
            "X-Device-Id": self.device_id,
        }
        if self.session_token:
            headers["X-Session-Token"] = self.session_token

        options = {"headers": headers, "timeout": ClientTimeout(total=30)}
        if body and method in ("POST", "PUT"):
            options["json"] = body

        try:
            async with self.session.request(method, url, **options) as resp:
                response_text = await resp.text()

                if resp.status in (500, 504) and retry_count < MAX_RETRIES:
                    delay = (2 ** retry_count)
                    _LOGGER.warning("Ajax API %d, retrying in %ds...", resp.status, delay)
                    await asyncio.sleep(delay)
                    return await self._call_ajax_direct(endpoint, method, body, retry_count + 1)

                if resp.status in (401, 403):
                    self._last_error = f"Ajax {resp.status}"
                    # Try re-login
                    if retry_count == 0:
                        _LOGGER.info("Ajax auth error, attempting re-login...")
                        self.session_token = None
                        self.token_expires = None
                        if await self.login():
                            return await self._call_ajax_direct(endpoint, method, body, retry_count + 1)
                    self._set_backoff()
                    self._auth_failed = True
                    return {"error": resp.status, "message": "Auth failed", "auth_failed": True}

                if resp.status == 429:
                    self._set_backoff()
                    return {"error": 429, "message": "Rate limited by Ajax"}

                if not resp.ok:
                    self._last_error = f"Ajax {resp.status}"
                    return {"error": resp.status, "message": response_text[:200]}

                import json
                try:
                    data = json.loads(response_text)
                except Exception:
                    data = {"raw": response_text}

                self._clear_backoff()
                self._last_error = None
                self._connection_status = self.STATUS_CONNECTED
                return data

        except asyncio.TimeoutError:
            self._last_error = "Ajax request timeout"
            return {"error": -1, "message": "Timeout"}
        except Exception as e:
            self._last_error = str(e)
            return {"error": -1, "message": str(e)}

    # ── Login (via gateway, then switch to direct) ──

    async def login(self) -> bool:
        """Login: verify token via gateway, get API key, then login to Ajax directly."""
        if self.session_token and self.token_expires:
            if datetime.now() < self.token_expires:
                return True

        if self._login_lock:
            await asyncio.sleep(2)
            return self.session_token is not None

        if self._is_in_backoff():
            return False

        self._login_lock = True
        try:
            # Step 1: Get API key from gateway (verifies Connee token)
            if not self._ajax_api_key:
                key_result = await self._call_gateway("get-api-key", {"email": self.email})
                if isinstance(key_result, dict) and "error" not in key_result:
                    self._ajax_api_key = key_result.get("apiKey")
                    _LOGGER.info("API key obtained from gateway")
                else:
                    _LOGGER.error("Failed to get API key: %s", key_result)
                    # Fallback: try login via gateway (backward compatibility)
                    return await self._login_via_gateway()

            # Step 2: Login directly to Ajax API
            password_bytes = self.password.encode("utf-8")
            hash_bytes = hashlib.sha256(password_bytes).digest()
            password_hex = hash_bytes.hex()
            password_b64 = base64.b64encode(hash_bytes).decode("utf-8")

            roles = ["USER", "PRO"]
            formats = [("hex", password_hex), ("base64", password_b64)]

            for role in roles:
                for fmt_name, pwd_hash in formats:
                    try:
                        result = await self._call_ajax_direct(
                            "/login",
                            "POST",
                            {"login": self.email.strip(), "passwordHash": pwd_hash, "userRole": role},
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
                                self.token_expires = datetime.now() + timedelta(seconds=TOKEN_REFRESH_INTERVAL)
                                self._clear_backoff()
                                _LOGGER.info("Direct Ajax login successful (role=%s, hash=%s)", role, fmt_name)
                                return True
                    except Exception as e:
                        _LOGGER.debug("Login attempt failed: role=%s, hash=%s: %s", role, fmt_name, e)

            _LOGGER.error("All direct login attempts failed")
            return False
        finally:
            self._login_lock = False

    async def _login_via_gateway(self) -> bool:
        """Fallback: login via Connee Gateway (backward compatibility)."""
        result = await self._call_gateway("login", {
            "email": self.email,
            "password": self.password,
            "deviceId": self.device_id,
        })
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
                self.token_expires = datetime.now() + timedelta(seconds=TOKEN_REFRESH_INTERVAL)
                self._clear_backoff()
                _LOGGER.info("Gateway login successful (fallback mode)")
                return True
        return False

    async def refresh_token(self) -> bool:
        """Refresh session token."""
        self.session_token = None
        self.token_expires = None
        return await self.login()

    # ── Data fetching (all direct to Ajax) ──

    async def get_hubs(self) -> List[Dict[str, Any]]:
        """Get user hubs (direct Ajax call)."""
        if not self.user_id:
            return []
        result = await self._call_ajax_direct(f"/user/{self.user_id}/hubs")
        if isinstance(result, dict) and "error" in result:
            return []
        hubs_raw = result if isinstance(result, list) else []
        hubs = []
        for h in hubs_raw:
            hub_id = h.get("hubId") or h.get("id") or h.get("deviceId")
            if hub_id:
                hubs.append({"id": hub_id, "hubId": hub_id, "name": h.get("name") or f"Hub {hub_id}", **h})
        return hubs

    async def get_hub_devices(self, hub_id: str) -> List[Dict[str, Any]]:
        """Get hub devices (direct Ajax call)."""
        if not self.user_id:
            return []
        result = await self._call_ajax_direct(f"/user/{self.user_id}/hubs/{hub_id}/devices")
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "error" in result:
            return []
        return []

    async def get_hub_state(self, hub_id: str) -> Dict[str, Any]:
        """Get hub state (direct Ajax call)."""
        if not self.user_id:
            return {}
        result = await self._call_ajax_direct(f"/user/{self.user_id}/hubs/{hub_id}")
        if isinstance(result, dict) and "error" in result:
            return {}
        return result if isinstance(result, dict) else {}

    async def get_device_states(self, hub_id: str) -> List[Dict[str, Any]]:
        """Get all device states (direct Ajax calls, batched)."""
        if not self.user_id:
            return []

        # First get device list
        devices = await self.get_hub_devices(hub_id)
        if not devices:
            return []

        # Fetch individual device states in batches
        device_states = []
        for i in range(0, len(devices), DEVICE_STATE_BATCH_SIZE):
            batch = devices[i:i + DEVICE_STATE_BATCH_SIZE]
            tasks = []
            for device in batch:
                dev_id = device.get("id") or device.get("deviceId")
                if dev_id:
                    tasks.append(self._get_single_device_state(hub_id, dev_id))
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, dict) and "error" not in r:
                        device_states.append(r)
            # Small delay between batches
            if i + DEVICE_STATE_BATCH_SIZE < len(devices):
                await asyncio.sleep(0.1)

        return device_states

    async def _get_single_device_state(self, hub_id: str, device_id: str) -> Dict[str, Any]:
        """Get single device state."""
        result = await self._call_ajax_direct(f"/user/{self.user_id}/hubs/{hub_id}/devices/{device_id}")
        if isinstance(result, dict) and "error" not in result:
            result["id"] = device_id
            return result
        return {"id": device_id, "error": True}

    async def arm_hub(self, hub_id: str, arm_state: str) -> tuple[bool, str]:
        """Arm/disarm hub (direct Ajax call)."""
        if not self.user_id:
            return False, "User ID not set"

        command_map = {
            "ARM": "ARM", "DISARM": "DISARM",
            "ARM_NIGHT": "NIGHT_MODE_ON", "NIGHT_ARM": "NIGHT_MODE_ON",
            "NIGHT_MODE_ON": "NIGHT_MODE_ON", "NIGHT_MODE_OFF": "NIGHT_MODE_OFF",
            "ARM_PARTIAL": "ARM", "PARTIAL_ARM": "ARM",
        }
        command = command_map.get(arm_state, arm_state)

        result = await self._call_ajax_direct(
            f"/user/{self.user_id}/hubs/{hub_id}/commands/arming",
            "PUT",
            {"command": command, "ignoreProblems": True},
        )
        if isinstance(result, dict) and "error" in result:
            return False, result.get("message", "Unknown error")
        return True, ""

    async def control_valve(self, device_id: str, valve_state: str) -> bool:
        """Control WaterStop valve (direct Ajax call)."""
        if not self.user_id or not self.hub_id:
            return False
        result = await self._call_ajax_direct(
            f"/user/{self.user_id}/hubs/{self.hub_id}/devices/{device_id}/commands/automation",
            "PUT",
            {"state": valve_state},
        )
        return not (isinstance(result, dict) and "error" in result)

    async def control_switch(self, device_id: str, switch_state: bool) -> bool:
        """Control Socket/Relay (direct Ajax call)."""
        if not self.user_id or not self.hub_id:
            return False
        state_str = "ON" if switch_state else "OFF"
        result = await self._call_ajax_direct(
            f"/user/{self.user_id}/hubs/{self.hub_id}/devices/{device_id}/commands/switch",
            "PUT",
            {"state": state_str},
        )
        return not (isinstance(result, dict) and "error" in result)
