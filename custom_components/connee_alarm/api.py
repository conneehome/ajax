"""Connee Alarm API Client."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from aiohttp import ClientSession, ClientTimeout

from .const import CONNEE_GATEWAY_URL, TOKEN_REFRESH_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ConneeAlarmApiClient:
    """Client for Connee Alarm API."""

    def __init__(
        self,
        session: ClientSession,
        email: str,
        password: str,
    ):
        """Initialize the API client."""
        self.session = session
        self.email = email
        self.password = password
        self.session_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.hub_id: Optional[str] = None
        self.token_expires: Optional[datetime] = None

    async def _call_gateway(
        self,
        action: str,
        body: Optional[Dict] = None,
    ) -> Any:
        """Call Connee Gateway API."""
        url = f"{CONNEE_GATEWAY_URL}?action={action}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        request_body = body or {}
        if self.session_token:
            request_body["sessionToken"] = self.session_token

        try:
            timeout = ClientTimeout(total=30)
            async with self.session.request(
                "POST", url, json=request_body, headers=headers, timeout=timeout
            ) as resp:
                result = await resp.json()

                if resp.status == 200 and isinstance(result, dict) and result.get("success"):
                    return result.get("data")

                if isinstance(result, dict):
                    error_msg = result.get("error", f"HTTP {resp.status}")
                else:
                    error_msg = f"HTTP {resp.status}"

                _LOGGER.error("Gateway error: %s", error_msg)
                return {"error": resp.status, "message": error_msg}
        except Exception as e:
            _LOGGER.error("Gateway request error: %s", e)
            return {"error": -1, "message": str(e)}

    async def login(self) -> bool:
        """Login via Connee Gateway."""
        result = await self._call_gateway(
            "login",
            {
                "email": self.email,
                "password": self.password,
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
                _LOGGER.info("Login successful via Connee Gateway")
                return True

        error_msg = result.get("message", "Login failed") if isinstance(result, dict) else "Login failed"
        _LOGGER.error("Login failed: %s", error_msg)
        return False

    async def refresh_token(self) -> bool:
        """Refresh session token."""
        return await self.login()

    async def get_hubs(self) -> List[Dict[str, Any]]:
        """Get user hubs."""
        if not self.user_id:
            return []

        result = await self._call_gateway("get-user-hubs", {"userId": self.user_id})

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

