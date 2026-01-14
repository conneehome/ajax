"""
Connee Enterprise - Ajax Systems Integration for Home Assistant
Custom Component per HACS

Repository: https://github.com/conneehome/ajax
"""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_CONNEE_TOKEN
from .coordinator import AjaxDataCoordinator
from .api import AjaxApiClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ajax from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    session = async_get_clientsession(hass)
    api = AjaxApiClient(
        session=session,
        email=entry.data["email"],
        password=entry.data["password"],
        connee_token=entry.data.get(CONF_CONNEE_TOKEN, ""),
    )
    
    # Login
    if not await api.login():
        _LOGGER.error("Failed to login to Ajax API")
        return False
    
    # Get hubs
    hubs = await api.get_hubs()
    if not hubs:
        _LOGGER.error("No hubs found")
        return False
    
    # Use first hub or configured hub
    hub_id = entry.data.get("hub_id") or hubs[0].get("id")
    api.hub_id = hub_id
    
    # Create coordinator
    coordinator = AjaxDataCoordinator(hass, api, hub_id)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "hub_id": hub_id,
    }
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok
