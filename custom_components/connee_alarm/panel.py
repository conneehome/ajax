"""Connee Alarm Dashboard Panel."""
import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PANEL_URL = "/connee-alarm-panel"
PANEL_TITLE = "Connee Alarm"
PANEL_ICON = "mdi:shield-home"


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the Connee Alarm panel."""
    try:
        # Get the dashboard yaml path
        dashboard_path = Path(__file__).parent / "lovelace" / "connee_alarm_dashboard.yaml"
        
        if dashboard_path.exists():
            # Register as a lovelace dashboard
            hass.components.lovelace.async_create_dashboard(
                url_path="connee-alarm",
                config={
                    "mode": "yaml",
                    "filename": str(dashboard_path),
                    "title": PANEL_TITLE,
                    "icon": PANEL_ICON,
                    "show_in_sidebar": True,
                    "require_admin": False,
                }
            )
            _LOGGER.info("Connee Alarm dashboard registered")
        else:
            _LOGGER.warning("Dashboard YAML file not found: %s", dashboard_path)
    except Exception as e:
        _LOGGER.error("Failed to register Connee Alarm panel: %s", e)
