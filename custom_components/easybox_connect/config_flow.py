import logging
from typing import Any, Mapping

from homeassistant import config_entries, data_entry_flow

from .const import DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.debug("START %s", __file__)


#! filename needs to be "config_flow.py" (fixed name)
@config_entries.HANDLERS.register(DOMAIN)
class EbcConfigFlow(config_entries.ConfigFlow):
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    # (this is not implemented yet)
    VERSION = 1
    _LOGGER.debug("ENTER EbcConfigFlow of %s", __file__)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> data_entry_flow.FlowResult:
        """Handle a flow, without user interaction"""
        _LOGGER.debug("ENTER async_step_user of EbcConfigFlow in %s", __file__)
        # Set unique ID
        await self.async_set_unique_id("testdev01")
        # If unique ID is already present, abort and exist config setup,
        # message of /translations/en.json is shown (no error)
        self._abort_if_unique_id_configured()
        # create empty config entry
        retval: Mapping[str, Any] = {}
        _LOGGER.debug("Create Config Entry")
        # config entry is found in ha_conf\.storage\core.config_entries
        return self.async_create_entry(title="EasyBox", data=retval)
