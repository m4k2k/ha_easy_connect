import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant


"""
EasyBox integration using DataUpdateCoordinator.

"""

_LOGGER = logging.getLogger(__name__)
_LOGGER.debug("START %s", __file__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry, forward to sensor setup"""
    _LOGGER.debug("ENTER async_setup_entry of %s", __file__)
    # forward setup to sensor.py
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True
