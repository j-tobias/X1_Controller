"""Enumerations for Gira X1 device states and modes."""

from enum import IntEnum, StrEnum


class OnOff(StrEnum):
    """Binary on/off state returned by the Gira API as '0' or '1'."""

    OFF = "0"
    ON = "1"


class HVACMode(IntEnum):
    """KNX HVAC operating mode (DPT 20.102).

    Used by KNXHeatingCoolingSwitchable.set_mode().
    """

    AUTO = 0
    COMFORT = 1
    STANDBY = 2
    ECONOMY = 3
    BUILDING_PROTECTION = 4


class HeatCoolMode(IntEnum):
    """Heat / cool selection for KNXHeatingCoolingSwitchable."""

    COOL = 0
    HEAT = 1


class FanCoilMode(IntEnum):
    """Operating mode for KNXFanCoil.

    Note: verify these values against the Gira IoT REST API v2 PDF
    (Gira_IoT_REST_API_v2_EN.pdf) before relying on them in production.
    """

    AUTO = 0
    HEATING = 1
    COOLING = 2
    FAN = 3
    DRY = 4
