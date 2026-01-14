"""Ajax API Client - Connee Gateway."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from aiohttp import ClientSession, ClientTimeout

from .const import CONNEE_GATEWAY_URL, TOKEN_REFRESH_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AjaxApiClient:
    """Client for Ajax Systems via Connee Gateway."""

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
    ) -> Dict[str, Any]:
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
                if resp.status == 200 and result.get("success"):
                    return result.get("data", result)
                else:
                    error_msg = result.get("error", f"HTTP {resp.status}")
                    _LOGGER.error("Gateway error: %s", error_msg)
                    return {"error": resp.status, "message": error_msg}
        except Exception as e:
            _LOGGER.error("Gateway request error: %s", e)
            return {"error": -1, "message": str(e)}

    async def login(self) -> bool:
        """Login via Connee Gateway."""
        result = await self._call_gateway("login", {
            "email": self.email,
            "password": self.password,
        })

        if "error" not in result:
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

        error_msg = result.get("message", "Login failed")
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
        if "error" in result:
            return []
        hubs = result.get("data", result.get("hubs", result if isinstance(result, list) else []))
        return hubs if isinstance(hubs, list) else []

    async def get_hub_devices(self, hub_id: str) -> List[Dict[str, Any]]:
        """Get hub devices."""
        if not self.user_id:
            return []
        result = await self._call_gateway("get-hub-devices", {
            "userId": self.user_id,
            "hubId": hub_id,
        })
        if "error" in result:
            return []
        devices = result.get("data", result.get("devices", result if isinstance(result, list) else []))
        return devices if isinstance(devices, list) else []

    async def get_hub_state(self, hub_id: str) -> Dict[str, Any]:
        """Get hub state."""
        if not self.user_id:
            return {}
        result = await self._call_gateway("get-hub", {
            "userId": self.user_id,
            "hubId": hub_id,
        })
        if "error" in result:
            return {}
        return result.get("data", result)

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
