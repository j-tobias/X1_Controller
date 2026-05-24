"""Low-level HTTP client for the Gira X1 IoT REST API."""

import logging
from typing import Any

import requests

from .errors import AuthenticationError, GiraConnectionError, GiraControllerError

logger = logging.getLogger(__name__)


class GiraClient:
    """Thin HTTP transport layer for the Gira X1 REST API.

    Owns the requests.Session, SSL configuration, timeout, and token lifecycle.
    Has no knowledge of device objects or configuration caching.
    """

    def __init__(
        self,
        ip: str,
        timeout: float = 10.0,
        suppress_ssl_warnings: bool = True,
    ) -> None:
        self.ip = ip
        self.timeout = timeout
        self._token: str | None = None

        self._session = requests.Session()
        self._session.verify = False

        if suppress_ssl_warnings:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @property
    def token(self) -> str | None:
        return self._token

    def _request(
        self,
        method: str,
        path: str,
        auth: tuple[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        url = f"https://{self.ip}/{path}"
        logger.debug("%s %s", method, url)
        return self._session.request(method, url, auth=auth, timeout=self.timeout, **kwargs)

    def check_availability(self) -> bool:
        """Return True if the X1 API is reachable."""
        try:
            return bool(self._request("GET", "api/v2").status_code == 200)
        except requests.RequestException:
            return False

    def register(self, client_id: str, username: str, password: str) -> str:
        """Authenticate and return a token.

        Raises:
            AuthenticationError: On invalid credentials or locked device.
            GiraConnectionError: On network failure.
        """
        try:
            response = self._request(
                "POST",
                "api/v2/clients",
                auth=(username, password),
                json={"client": client_id},
            )
            match response.status_code:
                case 200 | 201:
                    self._token = str(response.json()["token"])
                    self._session.params = {"token": self._token}
                    return self._token
                case 401:
                    raise AuthenticationError("Invalid username or password")
                case 423:
                    raise AuthenticationError("Device is currently locked")
                case _:
                    raise AuthenticationError(f"Registration failed: {response.text}")
        except requests.RequestException as e:
            raise GiraConnectionError(f"Failed to connect to X1: {e}") from e

    def unregister(self, token: str) -> bool:
        """Deregister a client token.

        Raises:
            GiraControllerError: On API-level failure.
            GiraConnectionError: On network failure.
        """
        try:
            response = self._request("DELETE", f"api/v2/clients/{token}")
            match response.status_code:
                case 204:
                    if token == self._token:
                        self._token = None
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

    def get_uid(self) -> str:
        """Return the current configuration UID.

        Raises:
            GiraControllerError: If the request fails.
            GiraConnectionError: On network failure.
        """
        try:
            response = self._request("GET", "api/v2/uiconfig/uid")
            if response.status_code == 200:
                return str(response.json()["uid"])
            raise GiraControllerError(f"Failed to get UID: {response.text}")
        except requests.RequestException as e:
            raise GiraConnectionError(f"Failed to connect to X1: {e}") from e

    def get_config(self) -> dict[str, Any]:
        """Return the full UI configuration dictionary.

        Raises:
            GiraControllerError: If the request fails.
            GiraConnectionError: On network failure.
        """
        try:
            response = self._request("GET", "api/v2/uiconfig")
            if response.status_code == 200:
                result: dict[str, Any] = response.json()
                return result
            raise GiraControllerError(f"Failed to get config: {response.text}")
        except requests.RequestException as e:
            raise GiraConnectionError(f"Failed to connect to X1: {e}") from e

    def get_values(self, uid: str) -> list[dict[str, Any]]:
        """Return the values list for a given function UID.

        Raises:
            GiraConnectionError: On network failure.
        """
        try:
            response = self._request("GET", f"api/values/{uid}")
            if response.status_code == 200:
                values: list[dict[str, Any]] = response.json().get("values", [])
                return values
            return []
        except requests.RequestException as e:
            raise GiraConnectionError(f"Failed to connect to X1: {e}") from e

    def put_value(self, uid: str, value: Any) -> bool:
        """Set a datapoint value by UID. Returns True on success."""
        try:
            response = self._request("PUT", f"api/values/{uid}", json={"value": value})
            return bool(response.status_code == 200)
        except requests.RequestException:
            return False

    def register_callbacks(
        self,
        token: str,
        service_callback: str,
        value_callback: str,
        test_callbacks: bool | None = None,
    ) -> requests.Response:
        """Register callback URLs for service and value events.

        Note: This method has not been thoroughly tested.
        """
        data: dict[str, Any] = {
            "serviceCallback": service_callback,
            "valueCallback": value_callback,
        }
        if test_callbacks is not None:
            data["testCallbacks"] = test_callbacks
        return self._request("POST", f"api/v2/clients/{token}/callbacks", json=data)
