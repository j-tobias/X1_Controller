"""Main API module for Gira X1 controller interaction.

This module provides the GiraController class for interacting with
the Gira X1 IoT REST API.
"""

import json
from pathlib import Path
from typing import Any

import requests

from .devices import DEVICE_REGISTRY, GiraDevice, create_device

# Suppress SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings()


class GiraControllerError(Exception):
    """Base exception for GiraController errors."""

    pass


class AuthenticationError(GiraControllerError):
    """Raised when authentication fails."""

    pass


class ConnectionError(GiraControllerError):
    """Raised when connection to X1 fails."""

    pass


class GiraController:
    """Main interface for interacting with the Gira X1 IoT REST API.

    This class provides methods to authenticate, query configuration,
    and control devices connected to a Gira X1 smart home controller.
    """

    def __init__(
        self,
        ip: str,
        client_id: str = "de.GiraControl.defaultclient",
    ) -> None:
        """Initialize the Gira Controller.

        Args:
            ip: IP address of the Gira X1 controller.
            client_id: URN identifier for this client application.

        Raises:
            ValueError: If ip or client_id are not strings.
        """
        if not isinstance(ip, str):
            raise ValueError(f"ip must be a string, got {type(ip).__name__}")

        if not isinstance(client_id, str):
            raise ValueError(f"client_id must be a string, got {type(client_id).__name__}")

        self.ip = ip
        self.client_id = client_id
        self.token: str | None = None
        self.uid: str | None = None
        self._uid_config: dict[str, Any] | None = None
        self._devices: list[GiraDevice] = []

    def _api_request(
        self,
        method: str,
        endpoint: str,
        auth: tuple[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make an API request to the Gira X1.

        Args:
            method: HTTP method (GET, PUT, POST, DELETE).
            endpoint: API endpoint path.
            auth: Optional basic auth tuple (username, password).
            **kwargs: Additional arguments passed to requests.

        Returns:
            The response object.

        Raises:
            requests.RequestException: If the request fails.
        """
        url = f"https://{self.ip}/{endpoint}"
        return requests.request(method, url, auth=auth, verify=False, **kwargs)

    def check_availability(self) -> bool:
        """Check if the Gira X1 API is available.

        Returns:
            True if the API is available, False otherwise.
        """
        try:
            response = self._api_request("GET", "api/v2")
            return response.status_code == 200
        except requests.RequestException:
            return False

    def register_client(self, username: str, password: str) -> str:
        """Register this client with the X1 and obtain an authentication token.

        Args:
            username: Username for an account on the X1.
            password: Password for the account.

        Returns:
            The authentication token.

        Raises:
            ValueError: If username or password are not strings.
            AuthenticationError: If authentication fails.
        """
        if not isinstance(username, str):
            raise ValueError(f"username must be a string, got {type(username).__name__}")

        if not isinstance(password, str):
            raise ValueError(f"password must be a string, got {type(password).__name__}")

        try:
            body = json.dumps({"client": self.client_id})
            response = self._api_request(
                "POST",
                "api/v2/clients",
                auth=(username, password),
                data=body,
            )

            if response.status_code == 200:
                self.token = response.json()["token"]
                return self.token
            elif response.status_code == 401:
                raise AuthenticationError("Invalid username or password")
            elif response.status_code == 423:
                raise AuthenticationError("Device is currently locked")
            else:
                raise AuthenticationError(f"Registration failed: {response.text}")

        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to X1: {e}") from e

    def unregister_client(self, token: str | None = None) -> bool:
        """Unregister this client from the X1.

        Args:
            token: Token to unregister. Uses stored token if not provided.

        Returns:
            True if successfully unregistered.

        Raises:
            ValueError: If no token is available.
            GiraControllerError: If unregistration fails.
        """
        token = token or self.token

        if not isinstance(token, str):
            raise ValueError(f"token must be a string, got {type(token).__name__}")

        try:
            response = self._api_request(
                "DELETE",
                f"api/v2/clients/{token}?token={token}",
            )

            match response.status_code:
                case 204:
                    if token == self.token:
                        self.token = None
                    return True
                case 401:
                    raise GiraControllerError("Token not found")
                case 423:
                    raise GiraControllerError("Device is currently locked")
                case 500:
                    raise GiraControllerError("Failed to remove client")
                case _:
                    raise GiraControllerError(f"Unregistration failed: {response.text}")

        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to X1: {e}") from e

    def register_callbacks(
        self,
        service_callback: str,
        value_callback: str,
        test_callbacks: bool | None = None,
    ) -> requests.Response:
        """Register callback URLs for events.

        Note: This method has not been thoroughly tested.

        Args:
            service_callback: URL for service callbacks.
            value_callback: URL for value change callbacks.
            test_callbacks: Whether to test the callbacks.

        Returns:
            The API response.
        """
        data: dict[str, Any] = {
            "serviceCallback": service_callback,
            "valueCallback": value_callback,
        }

        if test_callbacks is not None:
            data["testCallbacks"] = test_callbacks

        return self._api_request(
            "POST",
            f"api/v2/clients/{self.token}/callbacks",
            json=data,
        )

    def get_uid(self) -> str:
        """Get the unique identifier of the current configuration.

        The UID changes whenever the configuration is modified.

        Returns:
            The configuration UID.

        Raises:
            GiraControllerError: If the request fails.
        """
        try:
            response = self._api_request(
                "GET",
                f"api/v2/uiconfig/uid?token={self.token}",
            )

            if response.status_code == 200:
                self.uid = response.json()["uid"]
                return self.uid
            else:
                raise GiraControllerError(f"Failed to get UID: {response.text}")

        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to X1: {e}") from e

    def get_config(self, filename: str | Path | None = None) -> dict[str, Any]:
        """Load the current X1 configuration.

        Args:
            filename: Optional path to save the configuration as JSON.

        Returns:
            The configuration dictionary.

        Raises:
            ValueError: If filename is invalid.
            GiraControllerError: If the request fails.
        """
        if filename is not None and not isinstance(filename, (str, Path)):
            raise ValueError(f"filename must be a string or Path, got {type(filename).__name__}")

        try:
            response = self._api_request(
                "GET",
                f"api/uiconfig?token={self.token}",
            )

            if response.status_code != 200:
                raise GiraControllerError(f"Failed to get config: {response.text}")

            self._uid_config = response.json()

            if filename is not None:
                path = Path(filename)
                path.write_text(json.dumps(self._uid_config, indent=2))

            return self._uid_config

        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to X1: {e}") from e

    def get_devices(self) -> list[GiraDevice]:
        """Get all devices from the X1 configuration.

        Returns:
            List of device objects.

        Raises:
            GiraControllerError: If configuration cannot be loaded.
        """
        if self._uid_config is None:
            self.get_config()

        if self._uid_config is None:
            raise GiraControllerError("Failed to load configuration")

        devices: list[GiraDevice] = []

        for config in self._uid_config.get("functions", []):
            device = create_device(self.ip, self.token or "", config)
            if device is not None:
                devices.append(device)

        self._devices = devices
        return devices

    def get_device(
        self,
        display_name: str | None = None,
        uid: str | None = None,
    ) -> GiraDevice | None:
        """Get a specific device by display name or UID.

        Args:
            display_name: The display name of the device.
            uid: The UID of the device.

        Returns:
            The device if found, None otherwise.

        Raises:
            ValueError: If neither display_name nor uid is provided.
        """
        if display_name is None and uid is None:
            raise ValueError("Either display_name or uid must be provided")

        if display_name is not None and not isinstance(display_name, str):
            raise ValueError(f"display_name must be a string, got {type(display_name).__name__}")

        if uid is not None and not isinstance(uid, str):
            raise ValueError(f"uid must be a string, got {type(uid).__name__}")

        # Load devices if not already loaded
        if not self._devices:
            self.get_devices()

        # Search by UID first (higher priority)
        if uid is not None:
            for device in self._devices:
                if device.uid == uid:
                    return device

        # Search by display name
        if display_name is not None:
            for device in self._devices:
                if device.display_name == display_name:
                    return device

        return None

    @property
    def devices(self) -> list[GiraDevice]:
        """Get the cached list of devices."""
        return self._devices

    @property
    def config(self) -> dict[str, Any] | None:
        """Get the cached configuration."""
        return self._uid_config
