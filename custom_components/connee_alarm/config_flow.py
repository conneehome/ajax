"""Config flow for Connee Alarm integration."""
import logging
import uuid
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_HUB_ID, CONF_DEVICE_ID
from .api import ConneeAlarmApiClient

_LOGGER = logging.getLogger(__name__)

CONF_ACCEPT_TERMS = "accept_terms"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_ACCEPT_TERMS, default=False): bool,
    }
)


class ConneeAlarmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Connee Alarm."""

    VERSION = 2  # Bumped version for device_id support

    def __init__(self):
        """Initialize."""
        self._email: Optional[str] = None
        self._password: Optional[str] = None
        self._hubs: list = []
        self._device_id: Optional[str] = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Check GDPR acceptance first
            if not user_input.get(CONF_ACCEPT_TERMS):
                errors["base"] = "terms_not_accepted"
                return self.async_show_form(
                    step_id="user",
                    data_schema=STEP_USER_DATA_SCHEMA,
                    errors=errors,
                )
            
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            
            # Generate unique device ID for this installation
            # This ID will be saved and used forever for this account
            self._device_id = str(uuid.uuid4())
            _LOGGER.info("Generated unique device_id for new installation: %s", self._device_id[:8])
            
            session = async_get_clientsession(self.hass)
            
            api = ConneeAlarmApiClient(
                session=session,
                email=self._email,
                password=self._password,
                device_id=self._device_id,
            )

            if await api.login():
                self._hubs = await api.get_hubs()
                _LOGGER.info("Found %d hubs for account %s", len(self._hubs), self._email)
                
                if self._hubs:
                    if len(self._hubs) == 1:
                        hub = self._hubs[0]
                        return self.async_create_entry(
                            title=f"Connee Alarm - {hub.get('name', 'Hub')}",
                            data={
                                CONF_EMAIL: self._email,
                                CONF_PASSWORD: self._password,
                                CONF_HUB_ID: hub.get("id"),
                                CONF_DEVICE_ID: self._device_id,  # Save device_id permanently
                            },
                        )
                    else:
                        return await self.async_step_select_hub()
                else:
                    _LOGGER.warning(
                        "No hubs found for %s. Ensure the account has been invited to the hub.",
                        self._email
                    )
                    errors["base"] = "no_hubs"
            else:
                _LOGGER.error("Login failed for %s", self._email)
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_hub(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle hub selection."""
        if user_input is not None:
            hub_id = user_input[CONF_HUB_ID]
            hub = next((h for h in self._hubs if h.get("id") == hub_id), self._hubs[0])
            
            return self.async_create_entry(
                title=f"Connee Alarm - {hub.get('name', 'Hub')}",
                data={
                    CONF_EMAIL: self._email,
                    CONF_PASSWORD: self._password,
                    CONF_HUB_ID: hub_id,
                    CONF_DEVICE_ID: self._device_id,  # Save device_id permanently
                },
            )

        hub_options = {
            hub.get("id"): hub.get("name", f"Hub {hub.get('id')}")
            for hub in self._hubs
        }

        return self.async_show_form(
            step_id="select_hub",
            data_schema=vol.Schema(
                {vol.Required(CONF_HUB_ID): vol.In(hub_options)}
            ),
        )
