"""Ajax API Client."""
import asyncio
import hashlib
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from aiohttp import ClientSession, ClientTimeout

from .const import AJAX_API_BASE, API_KEY, TOKEN_REFRESH_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AjaxApiClient:
    """Client for Ajax Systems API."""

    def __init__(
        self,
        session: ClientSession,
        email: str,
        password: str,
        connee_token: str = "",
    ):
        """Initialize the API client."""
        self.session = session
        self.email = email
        self.password = password
        self.connee_token = connee_token
        self.session_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.hub_id: Optional[str] = None
        self.token_expires: Optional[datetime] = None

    def _hash_password(self, password: str) -> Dict[str, str]:
        """Hash password for API."""
        password_bytes = password.encode("utf-8")
        hash_bytes = hashlib.sha256(password_bytes).digest()
        return {
            "base64": base64.b64encode(hash_bytes).decode("utf-8"),
            "hex": hash_bytes.hex(),
        }

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        body: Optional[Dict] = None,
        use_token: bool = True,
    ) -> Dict[str, Any]:
        """Make API request."""
        url = f"{AJAX_API_BASE}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Api-Key": API_KEY,
        }

        # Add Connee token for authorization
        if self.connee_token:
            headers["X-Connee-Token"] = self.connee_token

        if use_token and self.session_token:
            headers["X-Session-Token"] = self.session_token

        try:
            timeout = ClientTimeout(total=30)
            async with self.session.request(
                method, url, json=body, headers=headers, timeout=timeout
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    text = await resp.text()
                    _LOGGER.error("API error %s: %s", resp.status, text)
                    return {"error": resp.status, "message": text}
        except Exception as e:
            _LOGGER.error("Request error: %s", e)
            return {"error": -1, "message": str(e)}

    async def login(self) -> bool:
        """Login to Ajax API."""
        password_hashes = self._hash_password(self.password)

        login_attempts = [
            {"login": self.email, "passwordHash": password_hashes["base64"]},
            {"email": self.email, "password": password_hashes["hex"]},
            {"login": self.email, "password": self.password},
        ]

        for attempt in login_attempts:
            result = await self._make_request("login", "POST", attempt, use_token=False)

            if "error" not in result:
                self.session_token = (
                    result.get("sessionToken")
                    or result.get("token")
                    or result.get("session", {}).get("token")
                )
                self.user_id = (
                    result.get("userId")
                    or result.get("user_id")
                    or result.get("user", {}).get("id")
                )

                if self.session_token:
                    self.token_expires = datetime.now() + timedelta(
                        seconds=TOKEN_REFRESH_INTERVAL
                    )
                    _LOGGER.info("Login successful")
                    return True

        _LOGGER.error("Login failed")
        return False

    async def refresh_token(self) -> bool:
        """Refresh session token."""
        return await self.login()

    async def get_hubs(self) -> List[Dict[str, Any]]:
        """Get user hubs."""
        if not self.user_id:
            return []
        result = await self._make_request(f"user/{self.user_id}/hubs")
        if "error" in result:
            return []
        hubs = result.get("data", result.get("hubs", []))
        return hubs if isinstance(hubs, list) else []

    async def get_hub_devices(self, hub_id: str) -> List[Dict[str, Any]]:
        """Get hub devices."""
        result = await self._make_request(f"hub/{hub_id}/devices")
        if "error" in result:
            return []
        devices = result.get("data", result.get("devices", []))
        return devices if isinstance(devices, list) else []

    async def get_hub_state(self, hub_id: str) -> Dict[str, Any]:
        """Get hub state."""
        result = await self._make_request(f"hub/{hub_id}")
        if "error" in result:
            return {}
        return result.get("data", result)

    async def get_device_states(self, hub_id: str) -> List[Dict[str, Any]]:
        """Get device states."""
        result = await self._make_request(f"hub/{hub_id}/deviceStates")
        if "error" in result:
            return []
        return result.get("data", result.get("deviceStates", []))

    async def arm_hub(self, hub_id: str, arm_state: str) -> bool:
        """Arm/disarm hub."""
        result = await self._make_request(
            f"hub/{hub_id}/arm", "POST", {"state": arm_state}
        )
        return "error" not in result
