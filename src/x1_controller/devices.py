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


class DimmerRGBW(GiraDevice):
    """RGBW Dimmer device for controlling colored lights.

    Datapoints:
        - OnOff (M): Binary on/off control
        - Brightness (O): Overall brightness (0-100)
        - Red (M): Red color value (0-100)
        - Green (M): Green color value (0-100)
        - Blue (M): Blue color value (0-100)
        - White (O): White color value (0-100)
    """

    channel_type = "de.gira.schema.channels.DimmerRGBW"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse RGBW dimmer-specific datapoints."""
        for dp in datapoints:
            name = dp["name"]
            if name in ("OnOff", "Brightness", "Red", "Green", "Blue", "White"):
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
    def red(self) -> float | None:
        """Get the current red value (0-100)."""
        dp = self._get_datapoint("Red")
        return dp.value if dp else None

    @property
    def green(self) -> float | None:
        """Get the current green value (0-100)."""
        dp = self._get_datapoint("Green")
        return dp.value if dp else None

    @property
    def blue(self) -> float | None:
        """Get the current blue value (0-100)."""
        dp = self._get_datapoint("Blue")
        return dp.value if dp else None

    @property
    def white(self) -> float | None:
        """Get the current white value (0-100)."""
        dp = self._get_datapoint("White")
        return dp.value if dp else None

    @property
    def has_brightness(self) -> bool:
        """Check if the dimmer supports brightness control."""
        return self._has_datapoint("Brightness")

    @property
    def has_white(self) -> bool:
        """Check if the dimmer supports white control."""
        return self._has_datapoint("White")

    def turn_on(self) -> bool:
        """Turn the light on."""
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def turn_off(self) -> bool:
        """Turn the light off."""
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 0) if dp else False

    def toggle(self) -> bool:
        """Toggle the light on/off."""
        if not self.update_values():
            return False
        dp = self._get_datapoint("OnOff")
        if dp is None:
            return False
        new_value = 0 if dp.value == "1" else 1
        return self._set_value_by_uid(dp.uid, new_value)

    def set_brightness(self, percent: float) -> bool:
        """Set the brightness level (0-100)."""
        if not self.has_brightness:
            return False
        dp = self._get_datapoint("Brightness")
        return self._set_value_by_uid(dp.uid, percent) if dp else False

    def set_color(self, red: float, green: float, blue: float) -> bool:
        """Set RGB color values (each 0-100)."""
        success = True
        for color, value in [("Red", red), ("Green", green), ("Blue", blue)]:
            dp = self._get_datapoint(color)
            if dp:
                if not self._set_value_by_uid(dp.uid, value):
                    success = False
            else:
                success = False
        return success

    def set_white(self, percent: float) -> bool:
        """Set the white value (0-100)."""
        if not self.has_white:
            return False
        dp = self._get_datapoint("White")
        return self._set_value_by_uid(dp.uid, percent) if dp else False


class DimmerWhite(GiraDevice):
    """Tunable white dimmer for controlling color temperature lights.

    Datapoints:
        - OnOff (M): Binary on/off control
        - Brightness (O): Brightness (0-100)
        - Color-Temperature (M): Color temperature in Kelvin
    """

    channel_type = "de.gira.schema.channels.DimmerWhite"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse tunable white dimmer-specific datapoints."""
        for dp in datapoints:
            name = dp["name"]
            if name in ("OnOff", "Brightness", "Color-Temperature"):
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
    def color_temperature(self) -> float | None:
        """Get the current color temperature in Kelvin."""
        dp = self._get_datapoint("Color-Temperature")
        return dp.value if dp else None

    @property
    def has_brightness(self) -> bool:
        """Check if the dimmer supports brightness control."""
        return self._has_datapoint("Brightness")

    def turn_on(self) -> bool:
        """Turn the light on."""
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def turn_off(self) -> bool:
        """Turn the light off."""
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 0) if dp else False

    def toggle(self) -> bool:
        """Toggle the light on/off."""
        if not self.update_values():
            return False
        dp = self._get_datapoint("OnOff")
        if dp is None:
            return False
        new_value = 0 if dp.value == "1" else 1
        return self._set_value_by_uid(dp.uid, new_value)

    def set_brightness(self, percent: float) -> bool:
        """Set the brightness level (0-100)."""
        if not self.has_brightness:
            return False
        dp = self._get_datapoint("Brightness")
        return self._set_value_by_uid(dp.uid, percent) if dp else False

    def set_color_temperature(self, kelvin: float) -> bool:
        """Set the color temperature in Kelvin."""
        dp = self._get_datapoint("Color-Temperature")
        return self._set_value_by_uid(dp.uid, kelvin) if dp else False


class Trigger(GiraDevice):
    """Trigger device for on/off and press-and-hold functions.

    Datapoints:
        - Trigger (M): Binary trigger value (write-only with events)
    """

    channel_type = "de.gira.schema.channels.Trigger"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse trigger-specific datapoints."""
        for dp in datapoints:
            if dp["name"] == "Trigger":
                self._datapoints["Trigger"] = DataPoint(uid=dp["uid"], name="Trigger")

    def trigger_on(self) -> bool:
        """Send trigger value 1."""
        dp = self._get_datapoint("Trigger")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def trigger_off(self) -> bool:
        """Send trigger value 0."""
        dp = self._get_datapoint("Trigger")
        return self._set_value_by_uid(dp.uid, 0) if dp else False

    def press(self) -> bool:
        """Press action (set to 1) for press-and-hold functionality."""
        return self.trigger_on()

    def release(self) -> bool:
        """Release action (set to 0) for press-and-hold functionality."""
        return self.trigger_off()


class SceneSet(GiraDevice):
    """Scene set device for executing and learning scenes.

    Datapoints:
        - Execute (M): Scene number to execute (write-only with events)
        - Teach (O): Scene number to learn (write-only with events)
    """

    channel_type = "de.gira.schema.channels.SceneSet"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse scene set-specific datapoints."""
        for dp in datapoints:
            name = dp["name"]
            if name in ("Execute", "Teach"):
                self._datapoints[name] = DataPoint(uid=dp["uid"], name=name)

    @property
    def has_teach(self) -> bool:
        """Check if the scene supports learning."""
        return self._has_datapoint("Teach")

    def execute_scene(self, scene_number: int) -> bool:
        """Execute a specific scene.

        Args:
            scene_number: The scene number to execute.
        """
        dp = self._get_datapoint("Execute")
        return self._set_value_by_uid(dp.uid, scene_number) if dp else False

    def teach_scene(self, scene_number: int) -> bool:
        """Learn/save the current state as a scene.

        Args:
            scene_number: The scene number to save.
        """
        if not self.has_teach:
            return False
        dp = self._get_datapoint("Teach")
        return self._set_value_by_uid(dp.uid, scene_number) if dp else False


class SceneControl(GiraDevice):
    """Scene control device for executing scenes (without learn capability).

    Datapoints:
        - Scene (M): Scene number to execute (write-only)
    """

    channel_type = "de.gira.schema.channels.SceneControl"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse scene control-specific datapoints."""
        for dp in datapoints:
            if dp["name"] == "Scene":
                self._datapoints["Scene"] = DataPoint(uid=dp["uid"], name="Scene")

    def execute_scene(self, scene_number: int) -> bool:
        """Execute a specific scene.

        Args:
            scene_number: The scene number to execute.
        """
        dp = self._get_datapoint("Scene")
        return self._set_value_by_uid(dp.uid, scene_number) if dp else False


class RoomTemperatureSwitchable(GiraDevice):
    """Room temperature device with switchable heating (e.g., sauna).

    Datapoints:
        - Current (M): Current temperature (read-only with events)
        - Set-Point (M): Target temperature (read/write with events)
        - OnOff (O): On/off control (read/write with events)
    """

    channel_type = "de.gira.schema.channels.RoomTemperatureSwitchable"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse room temperature-specific datapoints."""
        for dp in datapoints:
            name = dp["name"]
            if name in ("Current", "Set-Point", "OnOff"):
                self._datapoints[name] = DataPoint(uid=dp["uid"], name=name)

    @property
    def current_temperature(self) -> float | None:
        """Get the current temperature."""
        dp = self._get_datapoint("Current")
        return dp.value if dp else None

    @property
    def set_point(self) -> float | None:
        """Get the target temperature."""
        dp = self._get_datapoint("Set-Point")
        return dp.value if dp else None

    @property
    def on_off(self) -> str | None:
        """Get the current on/off state."""
        dp = self._get_datapoint("OnOff")
        return dp.value if dp else None

    @property
    def has_on_off(self) -> bool:
        """Check if the device supports on/off control."""
        return self._has_datapoint("OnOff")

    def set_temperature(self, temperature: float) -> bool:
        """Set the target temperature.

        Args:
            temperature: Target temperature value.
        """
        dp = self._get_datapoint("Set-Point")
        return self._set_value_by_uid(dp.uid, temperature) if dp else False

    def turn_on(self) -> bool:
        """Turn the heating on."""
        if not self.has_on_off:
            return False
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def turn_off(self) -> bool:
        """Turn the heating off."""
        if not self.has_on_off:
            return False
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 0) if dp else False


class KNXHeatingCoolingSwitchable(GiraDevice):
    """KNX Heating and cooling device.

    Datapoints:
        - Current (M): Current temperature (read-only with events)
        - Set-Point (M): Target temperature (read/write with events)
        - Mode (O): Operating mode (write-only with events)
        - Status (O): Current status (read-only with events)
        - Presence (O): Presence status (read/write with events)
        - Heating (O): Heating active (read-only with events)
        - Cooling (O): Cooling active (read-only with events)
        - Heat-Cool (O): Heat/cool mode (read/write with events)
        - OnOff (O): On/off control (read/write with events)
    """

    channel_type = "de.gira.schema.channels.KNX.HeatingCoolingSwitchable"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse heating/cooling-specific datapoints."""
        for dp in datapoints:
            name = dp["name"]
            if name in ("Current", "Set-Point", "Mode", "Status", "Presence",
                       "Heating", "Cooling", "Heat-Cool", "OnOff"):
                self._datapoints[name] = DataPoint(uid=dp["uid"], name=name)

    @property
    def current_temperature(self) -> float | None:
        """Get the current temperature."""
        dp = self._get_datapoint("Current")
        return dp.value if dp else None

    @property
    def set_point(self) -> float | None:
        """Get the target temperature."""
        dp = self._get_datapoint("Set-Point")
        return dp.value if dp else None

    @property
    def status(self) -> str | None:
        """Get the current status."""
        dp = self._get_datapoint("Status")
        return dp.value if dp else None

    @property
    def is_heating(self) -> str | None:
        """Get heating active state."""
        dp = self._get_datapoint("Heating")
        return dp.value if dp else None

    @property
    def is_cooling(self) -> str | None:
        """Get cooling active state."""
        dp = self._get_datapoint("Cooling")
        return dp.value if dp else None

    @property
    def on_off(self) -> str | None:
        """Get the current on/off state."""
        dp = self._get_datapoint("OnOff")
        return dp.value if dp else None

    @property
    def presence(self) -> str | None:
        """Get the presence state."""
        dp = self._get_datapoint("Presence")
        return dp.value if dp else None

    def set_temperature(self, temperature: float) -> bool:
        """Set the target temperature."""
        dp = self._get_datapoint("Set-Point")
        return self._set_value_by_uid(dp.uid, temperature) if dp else False

    def set_mode(self, mode: int) -> bool:
        """Set the operating mode."""
        dp = self._get_datapoint("Mode")
        return self._set_value_by_uid(dp.uid, mode) if dp else False

    def set_presence(self, present: bool) -> bool:
        """Set presence status."""
        dp = self._get_datapoint("Presence")
        return self._set_value_by_uid(dp.uid, 1 if present else 0) if dp else False

    def set_heat_cool_mode(self, heat: bool) -> bool:
        """Set heat/cool mode (True for heat, False for cool)."""
        dp = self._get_datapoint("Heat-Cool")
        return self._set_value_by_uid(dp.uid, 1 if heat else 0) if dp else False

    def turn_on(self) -> bool:
        """Turn the system on."""
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def turn_off(self) -> bool:
        """Turn the system off."""
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 0) if dp else False


class KNXFanCoil(GiraDevice):
    """KNX Fan coil / air conditioning device.

    Datapoints:
        - Current (M): Current temperature (read-only with events)
        - Set-Point (M): Target temperature (read/write with events)
        - OnOff (M): On/off control (read/write with events)
        - Mode (M): Operating mode (read/write with events)
        - Fan-Speed (O): Fan speed level (read/write with events)
        - Vanes-UpDown-Level (O): Vertical vane position (read/write with events)
        - Vanes-UpDown-StopMove (O): Vertical vane movement (read/write with events)
        - Vanes-LeftRight-Level (O): Horizontal vane position (read/write with events)
        - Vanes-LeftRight-StopMove (O): Horizontal vane movement (read/write with events)
        - Error (O): Error status (read-only with events)
        - Error-Text (O): Error message (read-only with events)
    """

    channel_type = "de.gira.schema.channels.KNX.FanCoil"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse fan coil-specific datapoints."""
        for dp in datapoints:
            name = dp["name"]
            if name in ("Current", "Set-Point", "OnOff", "Mode", "Fan-Speed",
                       "Vanes-UpDown-Level", "Vanes-UpDown-StopMove",
                       "Vanes-LeftRight-Level", "Vanes-LeftRight-StopMove",
                       "Error", "Error-Text"):
                self._datapoints[name] = DataPoint(uid=dp["uid"], name=name)

    @property
    def current_temperature(self) -> float | None:
        """Get the current temperature."""
        dp = self._get_datapoint("Current")
        return dp.value if dp else None

    @property
    def set_point(self) -> float | None:
        """Get the target temperature."""
        dp = self._get_datapoint("Set-Point")
        return dp.value if dp else None

    @property
    def on_off(self) -> str | None:
        """Get the current on/off state."""
        dp = self._get_datapoint("OnOff")
        return dp.value if dp else None

    @property
    def mode(self) -> str | None:
        """Get the current operating mode."""
        dp = self._get_datapoint("Mode")
        return dp.value if dp else None

    @property
    def fan_speed(self) -> str | None:
        """Get the current fan speed."""
        dp = self._get_datapoint("Fan-Speed")
        return dp.value if dp else None

    @property
    def error(self) -> str | None:
        """Get error status."""
        dp = self._get_datapoint("Error")
        return dp.value if dp else None

    @property
    def error_text(self) -> str | None:
        """Get error message."""
        dp = self._get_datapoint("Error-Text")
        return dp.value if dp else None

    @property
    def has_fan_speed(self) -> bool:
        """Check if fan speed control is available."""
        return self._has_datapoint("Fan-Speed")

    def turn_on(self) -> bool:
        """Turn the fan coil on."""
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def turn_off(self) -> bool:
        """Turn the fan coil off."""
        dp = self._get_datapoint("OnOff")
        return self._set_value_by_uid(dp.uid, 0) if dp else False

    def set_temperature(self, temperature: float) -> bool:
        """Set the target temperature."""
        dp = self._get_datapoint("Set-Point")
        return self._set_value_by_uid(dp.uid, temperature) if dp else False

    def set_mode(self, mode: int) -> bool:
        """Set the operating mode."""
        dp = self._get_datapoint("Mode")
        return self._set_value_by_uid(dp.uid, mode) if dp else False

    def set_fan_speed(self, speed: int) -> bool:
        """Set the fan speed level."""
        if not self.has_fan_speed:
            return False
        dp = self._get_datapoint("Fan-Speed")
        return self._set_value_by_uid(dp.uid, speed) if dp else False


class AudioWithPlaylist(GiraDevice):
    """Audio device with playlist support.

    Datapoints:
        - Play (M): Play/pause state (read/write with events)
        - Volume (M): Volume level (read/write with events)
        - Mute (O): Mute state (read/write with events)
        - Previous (O): Previous track (write-only with events)
        - Next (O): Next track (write-only with events)
        - Title (O): Current track title (read-only with events)
        - Album (O): Current album (read-only with events)
        - Artist (O): Current artist (read-only with events)
        - Playlist (O): Current playlist index (read/write with events)
        - PreviousPlaylist (O): Previous playlist (write-only with events)
        - NextPlaylist (O): Next playlist (write-only with events)
        - PlaylistName (O): Current playlist name (read-only with events)
        - Shuffle (O): Shuffle mode (read/write with events)
        - Repeat (O): Repeat mode (read/write with events)
    """

    channel_type = "de.gira.schema.channels.AudioWithPlaylist"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse audio-specific datapoints."""
        for dp in datapoints:
            name = dp["name"]
            if name in ("Play", "Volume", "Mute", "Previous", "Next", "Title",
                       "Album", "Artist", "Playlist", "PreviousPlaylist",
                       "NextPlaylist", "PlaylistName", "Shuffle", "Repeat"):
                self._datapoints[name] = DataPoint(uid=dp["uid"], name=name)

    @property
    def is_playing(self) -> str | None:
        """Get play state."""
        dp = self._get_datapoint("Play")
        return dp.value if dp else None

    @property
    def volume(self) -> float | None:
        """Get current volume level (0-100)."""
        dp = self._get_datapoint("Volume")
        return dp.value if dp else None

    @property
    def is_muted(self) -> str | None:
        """Get mute state."""
        dp = self._get_datapoint("Mute")
        return dp.value if dp else None

    @property
    def title(self) -> str | None:
        """Get current track title."""
        dp = self._get_datapoint("Title")
        return dp.value if dp else None

    @property
    def album(self) -> str | None:
        """Get current album."""
        dp = self._get_datapoint("Album")
        return dp.value if dp else None

    @property
    def artist(self) -> str | None:
        """Get current artist."""
        dp = self._get_datapoint("Artist")
        return dp.value if dp else None

    @property
    def playlist_name(self) -> str | None:
        """Get current playlist name."""
        dp = self._get_datapoint("PlaylistName")
        return dp.value if dp else None

    @property
    def shuffle(self) -> str | None:
        """Get shuffle state."""
        dp = self._get_datapoint("Shuffle")
        return dp.value if dp else None

    @property
    def repeat(self) -> str | None:
        """Get repeat state."""
        dp = self._get_datapoint("Repeat")
        return dp.value if dp else None

    def play(self) -> bool:
        """Start playback."""
        dp = self._get_datapoint("Play")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def pause(self) -> bool:
        """Pause playback."""
        dp = self._get_datapoint("Play")
        return self._set_value_by_uid(dp.uid, 0) if dp else False

    def set_volume(self, percent: float) -> bool:
        """Set volume level (0-100)."""
        dp = self._get_datapoint("Volume")
        return self._set_value_by_uid(dp.uid, percent) if dp else False

    def mute(self) -> bool:
        """Mute audio."""
        dp = self._get_datapoint("Mute")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def unmute(self) -> bool:
        """Unmute audio."""
        dp = self._get_datapoint("Mute")
        return self._set_value_by_uid(dp.uid, 0) if dp else False

    def next_track(self) -> bool:
        """Skip to next track."""
        dp = self._get_datapoint("Next")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def previous_track(self) -> bool:
        """Go to previous track."""
        dp = self._get_datapoint("Previous")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def select_playlist(self, index: int) -> bool:
        """Select playlist by index."""
        dp = self._get_datapoint("Playlist")
        return self._set_value_by_uid(dp.uid, index) if dp else False

    def next_playlist(self) -> bool:
        """Go to next playlist."""
        dp = self._get_datapoint("NextPlaylist")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def previous_playlist(self) -> bool:
        """Go to previous playlist."""
        dp = self._get_datapoint("PreviousPlaylist")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def set_shuffle(self, enabled: bool) -> bool:
        """Enable/disable shuffle mode."""
        dp = self._get_datapoint("Shuffle")
        return self._set_value_by_uid(dp.uid, 1 if enabled else 0) if dp else False

    def set_repeat(self, enabled: bool) -> bool:
        """Enable/disable repeat mode."""
        dp = self._get_datapoint("Repeat")
        return self._set_value_by_uid(dp.uid, 1 if enabled else 0) if dp else False


class SonosAudio(AudioWithPlaylist):
    """Sonos audio device with extended features.

    Extends AudioWithPlaylist with Sonos-specific datapoints:
        - Shift-Volume (O): Relative volume adjustment (write-only)
        - Playlists (O): Available playlists JSON (read-only with events)
        - Cover (O): Album cover URL (read-only with events)
        - ValidPlayModes (O): Valid play modes (read-only with events)
        - TransportActions (O): Available transport actions (read-only with events)
        - ZoneName (O): Sonos zone name (read-only with events)
    """

    channel_type = "de.gira.schema.channels.Sonos.Audio"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse Sonos-specific datapoints."""
        # First parse the parent class datapoints
        super()._parse_datapoints(datapoints)

        # Then add Sonos-specific ones
        for dp in datapoints:
            name = dp["name"]
            if name in ("Shift-Volume", "Playlists", "Cover", "ValidPlayModes",
                       "TransportActions", "ZoneName"):
                self._datapoints[name] = DataPoint(uid=dp["uid"], name=name)

    @property
    def cover_url(self) -> str | None:
        """Get album cover URL."""
        dp = self._get_datapoint("Cover")
        return dp.value if dp else None

    @property
    def zone_name(self) -> str | None:
        """Get Sonos zone name."""
        dp = self._get_datapoint("ZoneName")
        return dp.value if dp else None

    @property
    def playlists(self) -> str | None:
        """Get available playlists JSON."""
        dp = self._get_datapoint("Playlists")
        return dp.value if dp else None

    @property
    def valid_play_modes(self) -> str | None:
        """Get valid play modes."""
        dp = self._get_datapoint("ValidPlayModes")
        return dp.value if dp else None

    @property
    def transport_actions(self) -> str | None:
        """Get available transport actions."""
        dp = self._get_datapoint("TransportActions")
        return dp.value if dp else None

    def shift_volume(self, delta: float) -> bool:
        """Adjust volume by a relative amount.

        Args:
            delta: Volume adjustment percentage (-100 to 100).
        """
        dp = self._get_datapoint("Shift-Volume")
        return self._set_value_by_uid(dp.uid, delta) if dp else False


class Camera(GiraDevice):
    """IP Camera device.

    Datapoints:
        - Camera (M): Camera active state (read/write with events)
    """

    channel_type = "de.gira.schema.channels.Camera"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse camera-specific datapoints."""
        for dp in datapoints:
            if dp["name"] == "Camera":
                self._datapoints["Camera"] = DataPoint(uid=dp["uid"], name="Camera")

    @property
    def is_active(self) -> str | None:
        """Get camera active state."""
        dp = self._get_datapoint("Camera")
        return dp.value if dp else None

    def activate(self) -> bool:
        """Activate the camera view."""
        dp = self._get_datapoint("Camera")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def deactivate(self) -> bool:
        """Deactivate the camera view."""
        dp = self._get_datapoint("Camera")
        return self._set_value_by_uid(dp.uid, 0) if dp else False


class Link(GiraDevice):
    """IP Link device for displaying web content.

    Datapoints:
        - Link (M): Link active state (read/write with events)
    """

    channel_type = "de.gira.schema.channels.Link"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse link-specific datapoints."""
        for dp in datapoints:
            if dp["name"] == "Link":
                self._datapoints["Link"] = DataPoint(uid=dp["uid"], name="Link")

    @property
    def is_active(self) -> str | None:
        """Get link active state."""
        dp = self._get_datapoint("Link")
        return dp.value if dp else None

    def activate(self) -> bool:
        """Activate the link view."""
        dp = self._get_datapoint("Link")
        return self._set_value_by_uid(dp.uid, 1) if dp else False

    def deactivate(self) -> bool:
        """Deactivate the link view."""
        dp = self._get_datapoint("Link")
        return self._set_value_by_uid(dp.uid, 0) if dp else False


# Value type devices - simple single-datapoint devices

class Binary(GiraDevice):
    """Binary value device for boolean status/control.

    Datapoints:
        - Binary (M): Binary value (read/write with events)
    """

    channel_type = "de.gira.schema.channels.Binary"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse binary-specific datapoints."""
        for dp in datapoints:
            if dp["name"] == "Binary":
                self._datapoints["Binary"] = DataPoint(uid=dp["uid"], name="Binary")

    @property
    def value(self) -> str | None:
        """Get the binary value."""
        dp = self._get_datapoint("Binary")
        return dp.value if dp else None

    def set(self, value: int) -> bool:
        """Set the binary value (0 or 1)."""
        dp = self._get_datapoint("Binary")
        return self._set_value_by_uid(dp.uid, value) if dp else False


class DWord(GiraDevice):
    """Unsigned 32-bit value device.

    Datapoints:
        - DWord (M): Unsigned integer value (read/write with events)
    """

    channel_type = "de.gira.schema.channels.DWord"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse DWord-specific datapoints."""
        for dp in datapoints:
            if dp["name"] == "DWord":
                self._datapoints["DWord"] = DataPoint(uid=dp["uid"], name="DWord")

    @property
    def value(self) -> str | None:
        """Get the unsigned value."""
        dp = self._get_datapoint("DWord")
        return dp.value if dp else None

    def set(self, value: int) -> bool:
        """Set the unsigned value."""
        dp = self._get_datapoint("DWord")
        return self._set_value_by_uid(dp.uid, value) if dp else False


class Integer(GiraDevice):
    """Signed integer value device.

    Datapoints:
        - Integer (M): Signed integer value (read/write with events)
    """

    channel_type = "de.gira.schema.channels.Integer"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse integer-specific datapoints."""
        for dp in datapoints:
            if dp["name"] == "Integer":
                self._datapoints["Integer"] = DataPoint(uid=dp["uid"], name="Integer")

    @property
    def value(self) -> str | None:
        """Get the signed value."""
        dp = self._get_datapoint("Integer")
        return dp.value if dp else None

    def set(self, value: int) -> bool:
        """Set the signed value."""
        dp = self._get_datapoint("Integer")
        return self._set_value_by_uid(dp.uid, value) if dp else False


class Float(GiraDevice):
    """Floating point value device.

    Datapoints:
        - Float (M): Decimal value (read/write with events)
    """

    channel_type = "de.gira.schema.channels.Float"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse float-specific datapoints."""
        for dp in datapoints:
            if dp["name"] == "Float":
                self._datapoints["Float"] = DataPoint(uid=dp["uid"], name="Float")

    @property
    def value(self) -> str | None:
        """Get the decimal value."""
        dp = self._get_datapoint("Float")
        return dp.value if dp else None

    def set(self, value: float) -> bool:
        """Set the decimal value."""
        dp = self._get_datapoint("Float")
        return self._set_value_by_uid(dp.uid, value) if dp else False


class String(GiraDevice):
    """String value device.

    Datapoints:
        - String (M): Text value (read/write with events)
    """

    channel_type = "de.gira.schema.channels.String"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse string-specific datapoints."""
        for dp in datapoints:
            if dp["name"] == "String":
                self._datapoints["String"] = DataPoint(uid=dp["uid"], name="String")

    @property
    def value(self) -> str | None:
        """Get the text value."""
        dp = self._get_datapoint("String")
        return dp.value if dp else None

    def set(self, value: str) -> bool:
        """Set the text value."""
        dp = self._get_datapoint("String")
        return self._set_value_by_uid(dp.uid, value) if dp else False


class Byte(GiraDevice):
    """Unsigned 8-bit value device.

    Datapoints:
        - Byte (M): Unsigned 8-bit value (read/write with events)
    """

    channel_type = "de.gira.schema.channels.Byte"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse byte-specific datapoints."""
        for dp in datapoints:
            if dp["name"] == "Byte":
                self._datapoints["Byte"] = DataPoint(uid=dp["uid"], name="Byte")

    @property
    def value(self) -> str | None:
        """Get the byte value."""
        dp = self._get_datapoint("Byte")
        return dp.value if dp else None

    def set(self, value: int) -> bool:
        """Set the byte value (0-255)."""
        dp = self._get_datapoint("Byte")
        return self._set_value_by_uid(dp.uid, value) if dp else False


class Percent(GiraDevice):
    """Percentage value device.

    Datapoints:
        - Percent (M): Percentage value 0-100 or 0-255 (read/write with events)
    """

    channel_type = "de.gira.schema.channels.Percent"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse percent-specific datapoints."""
        for dp in datapoints:
            if dp["name"] == "Percent":
                self._datapoints["Percent"] = DataPoint(uid=dp["uid"], name="Percent")

    @property
    def value(self) -> str | None:
        """Get the percentage value."""
        dp = self._get_datapoint("Percent")
        return dp.value if dp else None

    def set(self, value: float) -> bool:
        """Set the percentage value."""
        dp = self._get_datapoint("Percent")
        return self._set_value_by_uid(dp.uid, value) if dp else False


class Temperature(GiraDevice):
    """Temperature value device.

    Datapoints:
        - Temperature (M): Temperature value in decimal (read/write with events)
    """

    channel_type = "de.gira.schema.channels.Temperature"

    def _parse_datapoints(self, datapoints: list[dict[str, Any]]) -> None:
        """Parse temperature-specific datapoints."""
        for dp in datapoints:
            if dp["name"] == "Temperature":
                self._datapoints["Temperature"] = DataPoint(uid=dp["uid"], name="Temperature")

    @property
    def value(self) -> str | None:
        """Get the temperature value."""
        dp = self._get_datapoint("Temperature")
        return dp.value if dp else None

    def set(self, value: float) -> bool:
        """Set the temperature value."""
        dp = self._get_datapoint("Temperature")
        return self._set_value_by_uid(dp.uid, value) if dp else False


# Device type registry for easy lookup
DEVICE_REGISTRY: dict[str, type[GiraDevice]] = {
    KNXDimmer.channel_type: KNXDimmer,
    Switch.channel_type: Switch,
    BlindWithPos.channel_type: BlindWithPos,
    DimmerRGBW.channel_type: DimmerRGBW,
    DimmerWhite.channel_type: DimmerWhite,
    Trigger.channel_type: Trigger,
    SceneSet.channel_type: SceneSet,
    SceneControl.channel_type: SceneControl,
    RoomTemperatureSwitchable.channel_type: RoomTemperatureSwitchable,
    KNXHeatingCoolingSwitchable.channel_type: KNXHeatingCoolingSwitchable,
    KNXFanCoil.channel_type: KNXFanCoil,
    AudioWithPlaylist.channel_type: AudioWithPlaylist,
    SonosAudio.channel_type: SonosAudio,
    Camera.channel_type: Camera,
    Link.channel_type: Link,
    Binary.channel_type: Binary,
    DWord.channel_type: DWord,
    Integer.channel_type: Integer,
    Float.channel_type: Float,
    String.channel_type: String,
    Byte.channel_type: Byte,
    Percent.channel_type: Percent,
    Temperature.channel_type: Temperature,
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
