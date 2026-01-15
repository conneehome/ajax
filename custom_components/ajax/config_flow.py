"""Config flow for Ajax integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_HUB_ID
from .api import AjaxApiClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class AjaxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ajax."""

    VERSION = 1

    def __init__(self):
        """Initialize."""
        self._email: Optional[str] = None
        self._password: Optional[str] = None
        self._hubs: list = []

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            
            session = async_get_clientsession(self.hass)
            
            api = AjaxApiClient(
                session=session,
                email=self._email,
                password=self._password,
            )

            if await api.login():
                self._hubs = await api.get_hubs()
                if self._hubs:
                    if len(self._hubs) == 1:
                        hub = self._hubs[0]
                        return self.async_create_entry(
                        title=f"Ajax - {hub.get('name', 'Hub')}",
                            data={
                                CONF_EMAIL: self._email,
                                CONF_PASSWORD: self._password,
                                CONF_HUB_ID: hub.get("id"),
                            },
                        )
                    else:
                        return await self.async_step_select_hub()
                else:
                    errors["base"] = "no_hubs"
            else:
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
                title=f"Ajax - {hub.get('name', 'Hub')}",
                data={
                    CONF_EMAIL: self._email,
                    CONF_PASSWORD: self._password,
                    CONF_HUB_ID: hub_id,
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
