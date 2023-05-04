import json
import logging
import os
from datetime import timedelta
from typing import Any, TypedDict

import async_timeout
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfDataRate
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import DeviceInfo, Entity, Mapping, MutableMapping
from homeassistant.helpers.entity_platform import AddEntitiesCallback, EntityPlatform, async_get_platforms
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed

from pyeasycmd.api import get_multi_key_value, get_routerName

# domain where all information of the sensor is found
from .const import DOMAIN, INPUT_JSON


# get a logger object
_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.debug("Starting %s", __file__)



class RouterProperty(TypedDict):
    key: str
    name: str
    hsType: str | None
    hsClass: str | None


# holds ids for entities (not best solution)
_managed_entity_ids: list[str] = []


def class_for_name(class_name: str) -> Any:
    match class_name:
        case "SensorDeviceClass.DATA_RATE":
            return SensorDeviceClass.DATA_RATE
        case "UnitOfDataRate.KILOBITS_PER_SECOND":
            return UnitOfDataRate.KILOBITS_PER_SECOND
        # If an exact match is not confirmed, this last case will be used if provided
        case _:
            return None


async def update_router_device_info():
    #! Dont update all with coordinator e.g. router_name wont change
    # TODO: Partial update of router_info with coordinator
    _LOGGER.debug("ENTER update_router_device_info")
    _LOGGER.debug("SCOPE Get router keys from json, query for updates and create device")

    _LOGGER.debug("Get keys to query from json")
    router_info_keys: list[RouterProperty] = await getRouterInfoFromJson("routerInfo")
    rik: list[str] = []

    # collect all keys to query in list
    for k in router_info_keys:
        rik.append(k["key"])
    # overwrite data from json with real data values (query list of collected keys)
    router_info: dict[str, str] = await get_multi_key_value(rik)

    # fixed version for testing purpose
    sw_ver: str = "0.01"
    for k in router_info_keys:
        # check if sw_version is in keys to query (which have already been queried)
        if k["hsType"] == "sw_version":
            # get sw_ver from routerinfo for current key stored in k
            sw_ver = router_info[k["key"]]

    sw_ver: str = "0.01"
    router_name: str = "test dev xy"

    router_name = await get_routerName()


    _device_id: str = "testdev01"  # test device id

    global _currentRouterInfo

    _currentRouterInfo = DeviceInfo(
        identifiers={
            # Serial numbers are unique identifiers within a specific domain
            (DOMAIN, _device_id)
        },
        name=router_name,
        manufacturer="test manufacturer",
        model="test model",
        sw_version=sw_ver,
    )



async def get_platform_for_domain(_hass: HomeAssistant, _domain: str) -> EntityPlatform | None:
    _LOGLCL = logging.getLogger(__name__ + ".get_platform_for_domain")
    platform_list = async_get_platforms(_hass, _domain)
    _LOGLCL.debug("platform_list:")
    _LOGLCL.debug(platform_list)
    for platform in platform_list:
        if platform.platform_name == _domain:
            _LOGLCL.debug("found+returning:")
            _LOGLCL.debug(platform)
            return platform
    return None


async def getRouterKeysDynamic(hass: HomeAssistant) -> list[str]:
    _LOGLCL: logging.Logger = logging.getLogger(__name__ + ".getRouterKeysDynamic")
    _LOGLCL.debug("ENTER getRouterKeysDynamic")
    _LOGLCL.debug("SCOPE Get already by HA managed router keys 'idx' and return them")

    _LOGLCL.debug("Get current platform object to get all entities")
    pl: EntityPlatform | None = await get_platform_for_domain(hass, DOMAIN)

    returnObj: list[str] = []
    if pl is not None:
        _entities: dict[str, Entity] = pl.entities
        _LOGLCL.debug("Platform entities received from obj:")
        _LOGLCL.debug(_entities)

        _LOGLCL.debug("iterate entities and get the idx from extra..attributes")
        for e in _entities:
            x: Mapping[str, Any] | None = _entities[e].extra_state_attributes
            if x is not None:
                returnObj.append(x["idx"])
    else:
        _LOGLCL.error("Platform is None! Integration not found")
    _LOGLCL.debug("returning router keys idx: %s", returnObj)
    _LOGLCL.debug("EXIT getRouterKeysDynamic")
    return returnObj


class MyCoordinator(DataUpdateCoordinator[Any]):
    _LOGLCL = logging.getLogger(__name__ + ".MyCoordinator")
    _LOGLCL.debug("Class MyCoordinator of %s", __file__)

    def __init__(self, hass: HomeAssistant):
        """Initialize MyCoordinator Class"""
        self._LOGLCL.debug("__init__ of MyCoordinator Class")
        DataUpdateCoordinator.__init__(
            self=self,
            hass=hass,
            logger=_LOGGER,
            # Name of the data. For logging purposes.
            name=DOMAIN,
            update_method=self._async_update_data,
            # Polling interval. Will only be polled if there are subscribers.
            # default is usually 30 seconds
            update_interval=timedelta(seconds=120),
        )
        self._LOGLCL.debug("managed entity ids: %s", _managed_entity_ids)

    async def _async_update_data(self) -> dict[Any, Any]:
        """Fetch data from API endpoint.
        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        self._LOGLCL.debug("_async_update_data of MyCoordinator")
        try:

            async with async_timeout.timeout(15):
                self._LOGLCL.debug("start self.my_api.get_dummy_data()")
                # call api to get the data object
                # put the dataobject into the HA-store
                self._LOGLCL.debug("calling router api, fetching information")
                self._LOGLCL.debug("for keys:")
                self._LOGLCL.debug(_managed_entity_ids)
                coordinator_data: dict[str, str] = await get_multi_key_value(_managed_entity_ids)
                self._LOGLCL.debug("returning cordinator_data:")
                self._LOGLCL.debug(coordinator_data)
                return coordinator_data
        except UpdateFailed as err:
            raise UpdateFailed(f"Error communicating with API: {err}")


class EasySensor(CoordinatorEntity[Any], SensorEntity):
    """An entity using CoordinatorEntity.
    The CoordinatorEntity class provides:
        should_poll
        async_update
        async_added_to_hass
        available
    """

    _coord: MyCoordinator

    _LOGLCL = logging.getLogger(__name__ + ".EasySensor")
    _LOGLCL.debug("Class of EasySensor of %s", __file__)

    _attr_name: str | None
    _attr_native_unit_of_measurement: str | None
    _attr_unique_id: str | None = None
    _attr_device_class: SensorDeviceClass | None = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    entity_id: str | None = None  # type: ignore[assignment]

    def get_sensor_value(self) -> Any:
        """Retrieve the current sensor value from the coordinator
        :return: The current value
        :rtype: int
        """
        # get custom id
        entity_idx = self.extra_state_attributes["idx"]
        self._LOGLCL.info(
            "get_sensor_value for EasySensor from coordinator_data for id: %s",
            entity_idx,
        )
        retval = self._coord.data[entity_idx]
        self._LOGLCL.info("returning %a", retval)
        return retval

    def get_sensor_system_state(self) -> str:
        # get custom id
        entity_idx = self.extra_state_attributes["idx"]
        self._LOGLCL.info(
            "get_sensor_system_state for EasySensor from coordinator_data for id: %s",
            entity_idx,
        )
        retval: str = "not implemented"
        self._LOGLCL.info("returning %s", retval)
        return retval

    def update_all_data(self) -> None:
        self._LOGLCL.info(
            "update_all_data of EasySensor for id: %s",
            self.extra_state_attributes["idx"],
        )
        self._attr_native_value = self.get_sensor_value()

    @property
    def extra_state_attributes(self) -> MutableMapping[str, Any]:
        """Return extra state attributes."""
        return self._attr_extra_state_attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update by the coordinator."""
        self._LOGLCL.debug("_handle_coordinator_update of EasySensor")
        self._LOGLCL.debug(
            "enter for id: %s of entity %s",
            self.extra_state_attributes["idx"],
            self.entity_id,
        )
        # gets triggered, triggers the pull of the data from the coordinator
        # gets triggered after the coordinator has finished getting updates
        self.update_all_data()
        CoordinatorEntity[Any]._handle_coordinator_update(self)

    # Add device info, creates device if not exists.
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        self._LOGLCL.debug("ENTER: device_info")
        return _currentRouterInfo

    def __init__(
        self,
        coord: MyCoordinator,
        _unique_id: str,
        _unit: str | None = None,
        _devclass: str | None = None,
        _name: str = "",
    ) -> None:
        CoordinatorEntity.__init__(self, coord)  # pyright: reportUnknownMemberType=false
        SensorEntity.__init__(self)

        self._LOGLCL.debug("__init__ of EasySensor %s", _unique_id)
        self._LOGLCL.debug("current _coordinator data:")
        self._LOGLCL.debug(coord.data)
        self._coord = coord

        if _unit is not None:
            self._attr_native_unit_of_measurement = class_for_name(_unit)
            self._LOGLCL.debug(
                '"%s" assigned the "%s" class',
                self.entity_id,
                type(self._attr_native_unit_of_measurement),
            )
        if _devclass is not None:
            self._attr_device_class = class_for_name(_devclass)
            self._LOGLCL.debug(
                '"%s" assigned the "%s" class',
                self.entity_id,
                type(self._attr_device_class),
            )
        self._attr_extra_state_attributes: MutableMapping[str, Any] = dict({"idx": "", "system_state": ""})
        self._attr_extra_state_attributes["idx"] = _unique_id  # id for integration internal reference
        self._attr_unique_id = f"{DOMAIN}.{_unique_id}"  # only homeassistant internal id
        self._LOGLCL.info("self.unique_id: %a", self.unique_id)
        if _name != "":
            self._attr_name = _name  # friendly name shown
        self.update_all_data()


async def getRouterInfoFromJson(_keyword: str) -> list[RouterProperty]:
    _LOGLCL = logging.getLogger(__name__ + ".getRouterInfoFromJson")
    _LOGLCL.debug("ENTER getRouterInfoFromJson %s", __file__)
    _LOGLCL.info("Load router properties/keys to query from json")
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = dir_path + "/" + INPUT_JSON
    _LOGLCL.debug("json-file: %s", file_path)
    json1_file = open(file_path)
    json1_str = json1_file.read()
    json1_data = json.loads(json1_str)
    router_props: list[RouterProperty] = json1_data[_keyword]
    return router_props


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Main Setup File"""
    _LOGLCL = logging.getLogger(__name__ + ".async_setup_entry")
    _LOGLCL.debug("ENTER async_setup_entry %s", __file__)
    dr = device_registry.async_get(hass)

    _LOGLCL.debug("create new device")

    _LOGLCL.debug("Load router keys from json, query router and create device")
    await update_router_device_info()

    dev1: device_registry.DeviceEntry = dr.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers=_currentRouterInfo["identifiers"] if "identifiers" in _currentRouterInfo else None,
        name=_currentRouterInfo["name"] if "name" in _currentRouterInfo else None,
        sw_version=_currentRouterInfo["sw_version"] if "sw_version" in _currentRouterInfo else None,
    )
    _LOGLCL.debug("my new device:")
    _LOGLCL.debug(dev1)

    router_keys: list[RouterProperty] = await getRouterInfoFromJson("queryKeys")

    for rk in router_keys:
        if "hsType" not in rk:
            rk["hsType"] = None
        if "hsClass" not in rk:
            rk["hsClass"] = None
        _managed_entity_ids.append(rk["key"])
        _LOGGER.debug("item: {}".format(rk))

    _LOGLCL.info("managed entity ids: %s", _managed_entity_ids)

    xcoordinator = MyCoordinator(hass)

    await xcoordinator.async_refresh()
    if not xcoordinator.last_update_success:
        raise PlatformNotReady

    # add sensor entities to HA
    async_add_entities(
        EasySensor(
            coord=xcoordinator,
            _unique_id=rk["key"],
            _unit=rk["hsType"],
            _devclass=rk["hsClass"],
            _name=rk["name"],
        )
        for rk in router_keys
    )

    _LOGLCL.debug("EXIT async_setup_entry")
