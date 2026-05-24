"""Main API module for Gira X1 controller interaction."""

import json
import logging
from pathlib import Path
from typing import Any

import requests

from .devices import GiraDevice, create_device

logger = logging.getLogger(__name__)


class GiraControllerError(Exception):
    """Base exception for GiraController errors."""
    pass


class AuthenticationError(GiraControllerError):
    """Raised when authentication fails."""
    pass


class GiraConnectionError(GiraControllerError):
    """Raised when connection to X1 fails."""
    pass


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
                The X1 ships with a self-signed certificate, so this defaults to True.
                Pass False if you supply a trusted cert via system CA store.

        Raises:
            ValueError: If ip or client_id are not strings.
        """
        if not isinstance(ip, str):
            raise ValueError(f"ip must be a string, got {type(ip).__name__}")
        if not isinstance(client_id, str):
            raise ValueError(f"client_id must be a string, got {type(client_id).__name__}")

        self.ip = ip
        self.client_id = client_id
        self.timeout = timeout
        self.token: str | None = None
        self.uid: str | None = None
        self._uid_config: dict[str, Any] | None = None
        self._devices: list[GiraDevice] = []

        self._session = requests.Session()
        self._session.verify = False

        if suppress_ssl_warnings:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _api_request(
        self,
        method: str,
        endpoint: str,
        auth: tuple[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        url = f"https://{self.ip}/{endpoint}"
        logger.debug("%s %s", method, url)
        return self._session.request(method, url, auth=auth, timeout=self.timeout, **kwargs)

    def check_availability(self) -> bool:
        """Check if the Gira X1 API is available."""
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
            GiraConnectionError: If the device is unreachable.
        """
        if not isinstance(username, str):
            raise ValueError(f"username must be a string, got {type(username).__name__}")
        if not isinstance(password, str):
            raise ValueError(f"password must be a string, got {type(password).__name__}")

        try:
            response = self._api_request(
                "POST",
                "api/v2/clients",
                auth=(username, password),
                json={"client": self.client_id},
            )

            if response.status_code in [200, 201]:
                self.token = response.json()["token"]
                self._session.params = {"token": self.token}
                return self.token
            elif response.status_code == 401:
                raise AuthenticationError("Invalid username or password")
            elif response.status_code == 423:
                raise AuthenticationError("Device is currently locked")
            else:
                raise AuthenticationError(f"Registration failed: {response.text}")

        except requests.RequestException as e:
            raise GiraConnectionError(f"Failed to connect to X1: {e}") from e

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
        token = token or self.token

        if not isinstance(token, str):
            raise ValueError(f"token must be a string, got {type(token).__name__}")

        try:
            # The path identifies the client to remove; ?token= (added by session) is auth.
            response = self._api_request("DELETE", f"api/v2/clients/{token}")

            match response.status_code:
                case 204:
                    if token == self.token:
                        self.token = None
                        self._session.params = {}
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
            raise GiraConnectionError(f"Failed to connect to X1: {e}") from e

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
            GiraConnectionError: If the device is unreachable.
        """
        try:
            response = self._api_request("GET", "api/v2/uiconfig/uid")
            if response.status_code == 200:
                self.uid = response.json()["uid"]
                return self.uid
            else:
                raise GiraControllerError(f"Failed to get UID: {response.text}")
        except requests.RequestException as e:
            raise GiraConnectionError(f"Failed to connect to X1: {e}") from e

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

        try:
            response = self._api_request("GET", "api/v2/uiconfig")
            if response.status_code != 200:
                raise GiraControllerError(f"Failed to get config: {response.text}")

            self._uid_config = response.json()

            if filename is not None:
                Path(filename).write_text(json.dumps(self._uid_config, indent=2))

            return self._uid_config

        except requests.RequestException as e:
            raise GiraConnectionError(f"Failed to connect to X1: {e}") from e

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
            device = create_device(self.ip, self.token or "", config, self._session, self.timeout)
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
