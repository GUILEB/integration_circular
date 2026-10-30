"""Platform for shared base classes for sensors."""

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import CircularDataUpdateCoordinator


class CircularEntity(CoordinatorEntity[CircularDataUpdateCoordinator]):
    """Define a generic class for Circular entities."""

    _attr_attribution = "Data provided by unpublished Winet Control API"
    # Nom affiché : nom de l'appareil + nom traduit de l'entité
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CircularDataUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Class initializer."""
        super().__init__(coordinator=coordinator)
        self.entity_description = description

        # no serial number. generate unique id ?
        self._attr_unique_id = f"{description.key}_{coordinator.read_api.data.model}"
        # Configure the Device Info
        self._attr_device_info = self.coordinator.device_info
