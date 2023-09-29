"""Platform for sensor integration."""
from __future__ import annotations
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from datetime import datetime, timedelta
from .datumOmvandlare import omvandlaTillDatetime, dagarTillDatum
import json
from .const import (
    DOMAIN,
    CONFIG_FILE,
    DEVICE_NAME,
)
from pathlib import Path

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import (
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_NAME,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities: AddEntitiesCallback
) -> None:
    tunnor = fetchData(hass)

    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for tunna, hamtning in tunnor.items():
        if tunna == "last_update":
            continue

        entities.append(Trashcan(hass, coordinator, tunna, hamtning))

    entities.append(NextTrashCan(hass, coordinator))

    async_add_entities(entities)


def fetchData(
    hass: HomeAssistant,
):
    tunnor = {}
    # Skapar filen om den inte finns (Bör aldrig kunna hända)
    jsonFilePath = Path(hass.config.path(CONFIG_FILE))
    jsonFilePath.touch(exist_ok=True)

    jsonFile = open(jsonFilePath, "r", encoding="utf-8")
    jsonFileData = jsonFile.read()
    jsonFile.close()

    # Kollar om vi har skapat filen tidigare
    try:
        jsonFileData = json.loads(jsonFileData)
        tunnor = jsonFileData
        return tunnor
    except:
        return tunnor


class Trashcan(CoordinatorEntity, SensorEntity):
    """En specifik tunna"""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        name,
        hamtning,
    ) -> None:
        super().__init__(coordinator)
        self._attr_native_value = hamtning
        self._name = name
        self._attr_unique_id = "VMEAB " + name
        self._attr_icon = "mdi:trash-can"
        self._hamtning = hamtning
        self._hass = hass
        self._attr_extra_state_attributes = {
            "Datetime": omvandlaTillDatetime(self._attr_native_value),
            "Veckodag": self._attr_native_value.split(" ")[0],
            "Dagar": dagarTillDatum(self._attr_native_value),
            "Uppdaterad": datetime.now() + timedelta(hours=2),
            "friendly_name": name,
        }
        self._attr_device_info = {
            ATTR_IDENTIFIERS: {(DOMAIN, DEVICE_NAME)},
            ATTR_NAME: DEVICE_NAME,
            ATTR_MANUFACTURER: "@nightcbis",
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updates when the coordinator gets new data"""

        print(f"Klockan {datetime.now()+timedelta(hours=2)} uppdateras {self._name} ")

        # Hämtar ny data
        tunnor = fetchData(self._hass)

        self._hamtning = tunnor[self._name]
        self._attr_native_value = self._hamtning
        self._attr_extra_state_attributes = {
            "Datetime": omvandlaTillDatetime(self._attr_native_value),
            "Veckodag": self._attr_native_value.split(" ")[0],
            "Dagar": dagarTillDatum(self._attr_native_value),
            "Uppdaterad": datetime.now() + timedelta(hours=2),
            "friendly_name": self._name,
        }
        self.async_write_ha_state()  # Måste köras för att HA ska förstå att vi uppdaterat allt klart.

    def update(self) -> None:
        """Används ej"""

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> str:
        return self._attr_native_value

    @property
    def device_class(self):
        return f"{DOMAIN}__providersensor"


class NextTrashCan(CoordinatorEntity, SensorEntity):
    """En sensor som säger vilken tunna som hämtas här näst"""

    # Letar reda på tunnan i tunnor-listan

    def hittaTunna(self, tunnor):
        tunnorArray = {}
        for tunna, hamtning in tunnor.items():
            if tunna == "last_update":
                continue
            tunnorArray[tunna] = dagarTillDatum(hamtning)

        return min(tunnorArray, key=tunnorArray.get)

    def __init__(self, hass: HomeAssistant, coordinator) -> None:
        super().__init__(coordinator)

        self._name = "VMEAB Next Pickup"
        self._attr_unique_id = self._name
        self._attr_icon = "mdi:trash-can"
        self._hass = hass
        self._attr_device_info = {
            ATTR_IDENTIFIERS: {(DOMAIN, DEVICE_NAME)},
            ATTR_NAME: DEVICE_NAME,
            ATTR_MANUFACTURER: "@nightcbis",
        }

        # Hämtar rätt tunna till "tunna"
        self._tunnor = fetchData(self._hass)
        self._tunna = self.hittaTunna(self._tunnor)

        self._attr_native_value = self._tunna

        self._attr_extra_state_attributes = {
            "Datetime": omvandlaTillDatetime(self._tunnor[self._attr_native_value]),
            "Veckodag": self._tunnor[self._attr_native_value].split(" ")[0],
            "Dagar": dagarTillDatum(self._tunnor[self._attr_native_value]),
            "Rentext": self._attr_native_value
            + " om "
            + str(dagarTillDatum(self._tunnor[self._attr_native_value]))
            + " dagar",
            "Hämtning": self._tunnor[self._tunna],
            "Uppdaterad": datetime.now() + timedelta(hours=2),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        print(f"Klockan {datetime.now()+timedelta(hours=2)} uppdateras {self._name} ")
        # Hämtar tunnan
        self._tunnor = fetchData(self._hass)
        self._tunna = self.hittaTunna(self._tunnor)
        self._attr_native_value = self._tunna
        self._attr_extra_state_attributes = {
            "Datetime": omvandlaTillDatetime(self._tunnor[self._attr_native_value]),
            "Veckodag": self._tunnor[self._attr_native_value].split(" ")[0],
            "Dagar": dagarTillDatum(self._tunnor[self._attr_native_value]),
            "Rentext": self._attr_native_value
            + " om "
            + str(dagarTillDatum(self._tunnor[self._attr_native_value]))
            + " dagar",
            "Hämtning": self._tunnor[self._tunna],
            "Uppdaterad": datetime.now() + timedelta(hours=2),
        }
        self.async_write_ha_state()

    def update(self) -> None:
        """Används ej"""

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> str:
        return self._attr_native_value
