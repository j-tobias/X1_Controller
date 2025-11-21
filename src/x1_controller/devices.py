"""Device classes for Gira X1 smart home devices.

This module contains classes representing different types of KNX devices
that can be controlled through the Gira X1 API.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import requests

# Suppress SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings()


@dataclass
class DataPoint:
    """Represents a data point configuration for a device."""

    uid: str
    name: str
    value: Any = None


class GiraDevice(ABC):
    """Base class for all Gira X1 devices.

    This abstract base class provides common functionality for all device types,
    including API communication and value management.
    """

    channel_type: str = ""

    def __init__(self, ip: str, token: str, config: dict[str, Any]) -> None:
        """Initialize a Gira device.

        Args:
            ip: IP address of the Gira X1 controller.
            token: Authentication token for API access.
            config: Device configuration dictionary from the X1.
        """
        self.ip = ip
        self.token = token
        self.display_name = config["displayName"]
        self.function_type = config["functionType"]
        self.uid = config["uid"]
        self._datapoints: dict[str, DataPoint] = {}

        self._parse_datapoints(config.get("dataPoints", []))

    @abstractmethod
    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse device-specific datapoints from configuration.

        Args:
            datapoints: List of datapoint configurations.
        """
        pass

    def _get_datapoint(self, name: str) -> DataPoint | None:
        """Get a datapoint by name.

        Args:
            name: The name of the datapoint.

        Returns:
            The DataPoint if it exists, None otherwise.
        """
        return self._datapoints.get(name)

    def _has_datapoint(self, name: str) -> bool:
        """Check if a datapoint exists.

        Args:
            name: The name of the datapoint.

        Returns:
            True if the datapoint exists.
        """
        return name in self._datapoints

    def _api_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Make an API request to the Gira X1.

        Args:
            method: HTTP method (GET, PUT, POST, DELETE).
            endpoint: API endpoint path.
            **kwargs: Additional arguments passed to requests.

        Returns:
            The response object.

        Raises:
            requests.RequestException: If the request fails.
        """
        url = f"https://{self.ip}/api/{endpoint}?token={self.token}"
        return requests.request(method, url, verify=False, **kwargs)

    def set_value(self, datapoint_name: str, value: Any) -> bool:
        """Set a value for a specific datapoint.

        Args:
            datapoint_name: Name of the datapoint to set.
            value: The value to set.

        Returns:
            True if successful, False otherwise.

        Raises:
            ValueError: If the datapoint doesn't exist.
        """
        datapoint = self._get_datapoint(datapoint_name)
        if datapoint is None:
            raise ValueError(f"Datapoint '{datapoint_name}' does not exist on this device")

        try:
            response = self._api_request(
                "PUT",
                f"values/{datapoint.uid}",
                json={"value": value},
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _set_value_by_uid(self, uid: str, value: Any) -> bool:
        """Set a value directly by UID.

        Args:
            uid: The datapoint UID.
            value: The value to set.

        Returns:
            True if successful, False otherwise.
        """
        try:
            response = self._api_request(
                "PUT",
                f"values/{uid}",
                json={"value": value},
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def update_values(self) -> bool:
        """Update all datapoint values from the device.

        Returns:
            True if successful, False otherwise.
        """
        try:
            response = self._api_request("GET", f"values/{self.uid}")
            if response.status_code != 200:
                return False

            values = response.json().get("values", [])
            self._update_datapoint_values(values)
            return True
        except (requests.RequestException, KeyError, ValueError):
            return False

    def _update_datapoint_values(self, values: list[dict[str, Any]]) -> None:
        """Update internal datapoint values from API response.

        Args:
            values: List of value dictionaries from the API.
        """
        # Create a mapping of uid to value for efficient lookup
        uid_to_value = {v["uid"]: v["value"] for v in values}

        for datapoint in self._datapoints.values():
            if datapoint.uid in uid_to_value:
                datapoint.value = uid_to_value[datapoint.uid]


class KNXDimmer(GiraDevice):
    """KNX Dimmer device for controlling dimmable lights."""

    channel_type = "de.gira.schema.channels.KNX.Dimmer"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse dimmer-specific datapoints."""
        for dp in datapoints:
            name = dp["name"]
            if name in ("OnOff", "Shift", "Brightness"):
                self._datapoints[name] = DataPoint(uid=dp["uid"], name=name)

    @property
    def on_off(self) -> str | None:
        """Get the current on/off state."""
        dp = self._get_datapoint("OnOff")
        return dp.value if dp else None

    @property
    def brightness(self) -> float | None:
        """Get the current brightness value (0-100)."""
        dp = self._get_datapoint("Brightness")
        return dp.value if dp else None

    @property
    def has_brightness(self) -> bool:
        """Check if the dimmer supports brightness control."""
        return self._has_datapoint("Brightness")

    @property
    def has_shift(self) -> bool:
        """Check if the dimmer supports shift control."""
        return self._has_datapoint("Shift")

    def toggle(self) -> bool:
        """Toggle the dimmer on/off.

        Returns:
            True if successful, False otherwise.
        """
        if not self.update_values():
            return False

        dp = self._get_datapoint("OnOff")
        if dp is None:
            return False

        new_value = 0 if dp.value == "1" else 1
        return self._set_value_by_uid(dp.uid, new_value)

    def dim_to(self, percent: float) -> bool:
        """Dim the light to a specific percentage.

        Args:
            percent: Target brightness (0-100).

        Returns:
            True if successful, False otherwise.
        """
        if not self.has_brightness:
            return False

        dp = self._get_datapoint("Brightness")
        if dp is None:
            return False

        return self._set_value_by_uid(dp.uid, percent)

    def turn_on(self) -> bool:
        """Turn the dimmer on.

        Returns:
            True if successful, False otherwise.
        """
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def turn_off(self) -> bool:
        """Turn the dimmer off.

        Returns:
            True if successful, False otherwise.
        """
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 0) if dp else False


class Switch(GiraDevice):
    """KNX Switch device for binary on/off control."""

    channel_type = "de.gira.schema.channels.Switch"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse switch-specific datapoints."""
        if datapoints:
            # Switch has a single mandatory OnOff datapoint
            dp = datapoints[0]
            self._datapoints["OnOff"] = DataPoint(uid=dp["uid"], name="OnOff")

    @property
    def on_off(self) -> str | None:
        """Get the current on/off state."""
        dp = self._get_datapoint("OnOff")
        return dp.value if dp else None

    def toggle(self) -> bool:
        """Toggle the switch on/off.

        Returns:
            True if successful, False otherwise.
        """
        if not self.update_values():
            return False

        dp = self._get_datapoint("OnOff")
        if dp is None:
            return False

        new_value = 0 if dp.value == "1" else 1
        return self._set_value_by_uid(dp.uid, new_value)

    def turn_on(self) -> bool:
        """Turn the switch on.

        Returns:
            True if successful, False otherwise.
        """
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def turn_off(self) -> bool:
        """Turn the switch off.

        Returns:
            True if successful, False otherwise.
        """
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 0) if dp else False


class BlindWithPos(GiraDevice):
    """KNX Blind with position control."""

    channel_type = "de.gira.schema.channels.BlindWithPos"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse blind-specific datapoints."""
        for dp in datapoints:
            name = dp["name"]
            if name in ("Step-Up-Down", "Up-Down", "Position", "Slat-Position"):
                self._datapoints[name] = DataPoint(uid=dp["uid"], name=name)

    @property
    def position(self) -> float | None:
        """Get the current blind position (0-100)."""
        dp = self._get_datapoint("Position")
        return dp.value if dp else None

    @property
    def slat_position(self) -> float | None:
        """Get the current slat position (0-100)."""
        dp = self._get_datapoint("Slat-Position")
        return dp.value if dp else None

    @property
    def has_position(self) -> bool:
        """Check if the blind supports position control."""
        return self._has_datapoint("Position")

    @property
    def has_slat_position(self) -> bool:
        """Check if the blind supports slat position control."""
        return self._has_datapoint("Slat-Position")

    def move_up(self) -> bool:
        """Move the blind up.

        Returns:
            True if successful, False otherwise.
        """
        dp = self._get_datapoint("Up-Down")
        return self._set_value_by_uid(dp.uid, 0) if dp else False

    def move_down(self) -> bool:
        """Move the blind down.

        Returns:
            True if successful, False otherwise.
        """
        dp = self._get_datapoint("Up-Down")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def step_up(self) -> bool:
        """Step the blind up (small movement).

        Returns:
            True if successful, False otherwise.
        """
        dp = self._get_datapoint("Step-Up-Down")
        return self._set_value_by_uid(dp.uid, 0) if dp else False

    def step_down(self) -> bool:
        """Step the blind down (small movement).

        Returns:
            True if successful, False otherwise.
        """
        dp = self._get_datapoint("Step-Up-Down")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def set_position(self, percent: float) -> bool:
        """Set the blind position.

        Args:
            percent: Target position (0-100).

        Returns:
            True if successful, False otherwise.
        """
        if not self.has_position:
            return False

        dp = self._get_datapoint("Position")
        return self._set_value_by_uid(dp.uid, percent) if dp else False

    def set_slat_position(self, percent: float) -> bool:
        """Set the slat position.

        Args:
            percent: Target slat position (0-100).

        Returns:
            True if successful, False otherwise.
        """
        if not self.has_slat_position:
            return False

        dp = self._get_datapoint("Slat-Position")
        return self._set_value_by_uid(dp.uid, percent) if dp else False


# Device type registry for easy lookup
DEVICE_REGISTRY: dict[str, type[GiraDevice]] = {
    KNXDimmer.channel_type: KNXDimmer,
    Switch.channel_type: Switch,
    BlindWithPos.channel_type: BlindWithPos,
}


def create_device(ip: str, token: str, config: dict[str, Any]) -> GiraDevice | None:
    """Factory function to create the appropriate device type.

    Args:
        ip: IP address of the Gira X1 controller.
        token: Authentication token for API access.
        config: Device configuration dictionary from the X1.

    Returns:
        A device instance of the appropriate type, or None if unsupported.
    """
    channel_type = config.get("channelType", "")
    device_class = DEVICE_REGISTRY.get(channel_type)

    if device_class is None:
        return None

    return device_class(ip, token, config)
