"""X1 Controller - Python API wrapper for Gira X1 smart home controller.

This package provides a Pythonic interface to interact with the Gira X1
IoT REST API, allowing control of KNX devices in a smart home environment.

Example usage:
    >>> from x1_controller import GiraController
    >>> controller = GiraController("192.168.1.100")
    >>> controller.register_client("username", "password")
    >>> devices = controller.get_devices()
    >>> for device in devices:
    ...     print(device.display_name)
"""

from .api import (
    AuthenticationError,
    ConnectionError,
    GiraController,
    GiraControllerError,
)
from .devices import (
    BlindWithPos,
    GiraDevice,
    KNXDimmer,
    Switch,
    create_device,
)

__version__ = "0.1.0"

__all__ = [
    # Main API
    "GiraController",
    # Exceptions
    "GiraControllerError",
    "AuthenticationError",
    "ConnectionError",
    # Device classes
    "GiraDevice",
    "KNXDimmer",
    "Switch",
    "BlindWithPos",
    # Factory
    "create_device",
    # Version
    "__version__",
]
