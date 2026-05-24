"""GiraController — high-level orchestration for the Gira X1 smart home controller."""

import json
import logging
from pathlib import Path
from typing import Any

import requests

from .client import GiraClient
from .devices import GiraDevice, create_device
from .errors import GiraControllerError

logger = logging.getLogger(__name__)


class GiraController:
    """Main interface for interacting with the Gira X1 IoT REST API."""

    def __init__(
        self,
        ip: str,
        client_id: str = "de.GiraControl.defaultclient",
        timeout: float = 10.0,
        suppress_ssl_warnings: bool = True,
    ) -> None:
        """Initialize the Gira Controller.

        Args:
            ip: IP address of the Gira X1 controller.
            client_id: URN identifier for this client application.
            timeout: Request timeout in seconds.
            suppress_ssl_warnings: Suppress InsecureRequestWarning for self-signed certs.

        Raises:
            ValueError: If ip or client_id are not strings.
        """
        if not isinstance(ip, str):
            raise ValueError(f"ip must be a string, got {type(ip).__name__}")
        if not isinstance(client_id, str):
            raise ValueError(f"client_id must be a string, got {type(client_id).__name__}")

        self.ip = ip
        self.client_id = client_id
        self.uid: str | None = None
        self._uid_config: dict[str, Any] | None = None
        self._devices: list[GiraDevice] = []
        self._client = GiraClient(ip, timeout, suppress_ssl_warnings)

    @property
    def token(self) -> str | None:
        """The current authentication token."""
        return self._client.token

    def check_availability(self) -> bool:
        """Check if the Gira X1 API is available."""
        return self._client.check_availability()

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
            GiraConnectionError: If the device is unreachable.
        """
        if not isinstance(username, str):
            raise ValueError(f"username must be a string, got {type(username).__name__}")
        if not isinstance(password, str):
            raise ValueError(f"password must be a string, got {type(password).__name__}")
        return self._client.register(self.client_id, username, password)

    def unregister_client(self, token: str | None = None) -> bool:
        """Unregister this client from the X1.

        Args:
            token: Token to unregister. Uses stored token if not provided.

        Returns:
            True if successfully unregistered.

        Raises:
            ValueError: If no token is available.
            GiraControllerError: If unregistration fails.
            GiraConnectionError: If the device is unreachable.
        """
        token = token or self._client.token
        if not isinstance(token, str):
            raise ValueError(f"token must be a string, got {type(token).__name__}")
        return self._client.unregister(token)

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
            test_callbacks: Whether to test the callbacks immediately.

        Returns:
            The API response.
        """
        token = self._client.token or ""
        return self._client.register_callbacks(token, service_callback, value_callback, test_callbacks)

    def get_uid(self) -> str:
        """Get the unique identifier of the current configuration.

        Returns:
            The configuration UID.

        Raises:
            GiraControllerError: If the request fails.
            GiraConnectionError: If the device is unreachable.
        """
        self.uid = self._client.get_uid()
        return self.uid

    def get_config(self, filename: str | Path | None = None) -> dict[str, Any]:
        """Load the current X1 configuration.

        Args:
            filename: Optional path to save the configuration as JSON.

        Returns:
            The configuration dictionary.

        Raises:
            ValueError: If filename is invalid.
            GiraControllerError: If the request fails.
            GiraConnectionError: If the device is unreachable.
        """
        if filename is not None and not isinstance(filename, (str, Path)):
            raise ValueError(f"filename must be a string or Path, got {type(filename).__name__}")

        self._uid_config = self._client.get_config()

        if filename is not None:
            Path(filename).write_text(json.dumps(self._uid_config, indent=2))

        return self._uid_config

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
            device = create_device(self._client, config)
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

        if not self._devices:
            self.get_devices()

        if uid is not None:
            for device in self._devices:
                if device.uid == uid:
                    return device

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
