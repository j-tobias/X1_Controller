<p align="center">
  <img src="resources/X1%20Controller%20Title.png" alt="X1 Controller" width="100%">
</p>

<div align="center">

[Quick Start](#quick-start) · [Devices](#supported-devices) · [API Reference](#api-reference) · [Architecture](#architecture)

</div>

---

## What is X1 Controller?

X1 Controller is a Python library for controlling KNX smart home devices through a **Gira X1** hub.

It wraps the Gira IoT REST API v2 in a clean, typed interface — authentication, device discovery, and device control in a few lines of code. The library is split into a thin HTTP client and a higher-level controller so the transport layer is easy to mock and test independently.

---

## Quick Start

**Install:**

```bash
# As a dependency in another project (recommended)
uv add git+https://github.com/j-tobias/Gira_X1_Controller.git

# Clone and develop locally
git clone https://github.com/j-tobias/Gira_X1_Controller.git
cd X1_Controller
uv sync

# Or with pip
pip install git+https://github.com/j-tobias/Gira_X1_Controller.git
```

**Usage:**

```python
from x1_controller import GiraController

controller = GiraController("192.168.1.100")

if controller.check_availability():
    controller.register_client("username", "password")

    # Discover all devices
    devices = controller.get_devices()
    for device in devices:
        print(f"{device.display_name} ({type(device).__name__})")

    # Control a specific device
    dimmer = controller.get_device(display_name="Living Room Light")
    if dimmer:
        dimmer.update_values()
        dimmer.dim_to(75)
        dimmer.turn_off()

    controller.unregister_client()
```

**Using enums for typed control:**

```python
from x1_controller import GiraController, HVACMode, HeatCoolMode, OnOff

controller = GiraController("192.168.1.100")
controller.register_client("username", "password")

thermostat = controller.get_device(display_name="Living Room Thermostat")
thermostat.update_values()

if thermostat.on_off == OnOff.ON:
    thermostat.set_mode(HVACMode.COMFORT)
    thermostat.set_heat_cool_mode(HeatCoolMode.HEAT)
    thermostat.set_temperature(21.5)
```

---

## Supported Devices

23 device types are supported, covering the full Gira IoT REST API v2 channel type list.

### Lighting

| Class | Channel Type | Key Methods |
|---|---|---|
| `KNXDimmer` | `KNX.Dimmer` | `turn_on()`, `turn_off()`, `toggle()`, `dim_to(percent)` |
| `Switch` | `Switch` | `turn_on()`, `turn_off()`, `toggle()` |
| `DimmerRGBW` | `DimmerRGBW` | `set_color(r, g, b)`, `set_brightness(percent)`, `set_white(percent)` |
| `DimmerWhite` | `DimmerWhite` | `set_brightness(percent)`, `set_color_temperature(kelvin)` |

### Blinds & Shutters

| Class | Channel Type | Key Methods |
|---|---|---|
| `BlindWithPos` | `BlindWithPos` | `move_up()`, `move_down()`, `step_up()`, `step_down()`, `set_position(percent)`, `set_slat_position(percent)` |

### Triggers & Scenes

| Class | Channel Type | Key Methods |
|---|---|---|
| `Trigger` | `Trigger` | `press()`, `release()`, `trigger_on()`, `trigger_off()` |
| `SceneSet` | `SceneSet` | `execute_scene(n)`, `teach_scene(n)` |
| `SceneControl` | `SceneControl` | `execute_scene(n)` |

### Climate

| Class | Channel Type | Key Methods |
|---|---|---|
| `RoomTemperatureSwitchable` | `RoomTemperatureSwitchable` | `set_temperature(t)`, `turn_on()`, `turn_off()` |
| `KNXHeatingCoolingSwitchable` | `KNX.HeatingCoolingSwitchable` | `set_temperature(t)`, `set_mode(HVACMode)`, `set_heat_cool_mode(HeatCoolMode)` |
| `KNXFanCoil` | `KNX.FanCoil` | `set_temperature(t)`, `set_mode(FanCoilMode)`, `set_fan_speed(n)` |

### Audio

| Class | Channel Type | Key Methods |
|---|---|---|
| `AudioWithPlaylist` | `AudioWithPlaylist` | `play()`, `pause()`, `set_volume(percent)`, `next_track()`, `select_playlist(n)` |
| `SonosAudio` | `Sonos.Audio` | Extends `AudioWithPlaylist` — adds `shift_volume(delta)`, `zone_name`, `cover_url` |

### Media

| Class | Channel Type | Key Methods |
|---|---|---|
| `Camera` | `Camera` | `activate()`, `deactivate()` |
| `Link` | `Link` | `activate()`, `deactivate()` |

### Value Types

Generic single-value devices for raw data access.

| Class | Value |
|---|---|
| `Binary` | `0` or `1` |
| `Byte` | `0–255` |
| `DWord` | `0–4 294 967 295` |
| `Integer` | Signed integer |
| `Float` | Decimal |
| `String` | Text |
| `Percent` | `0–100` |
| `Temperature` | Decimal (°C) |

All value type devices expose `.value` and `.set(value)`.

---

## API Reference

### `GiraController`

The main entry point. Handles authentication, configuration loading, and device management.

```python
controller = GiraController(
    ip="192.168.1.100",
    client_id="de.myapp.client",   # optional, default provided
    timeout=10.0,                   # optional
    suppress_ssl_warnings=True,     # optional, X1 ships with self-signed cert
)
```

| Method | Returns | Description |
|---|---|---|
| `check_availability()` | `bool` | Ping the API |
| `register_client(username, password)` | `str` | Authenticate, returns token |
| `unregister_client(token=None)` | `bool` | Deregister client |
| `get_config(filename=None)` | `dict` | Load X1 configuration, optionally save to file |
| `get_uid()` | `str` | Get configuration UID (changes on config edits) |
| `get_devices()` | `list[GiraDevice]` | Instantiate all devices from configuration |
| `get_device(display_name=None, uid=None)` | `GiraDevice \| None` | Look up a single device |
| `register_callbacks(service_cb, value_cb)` | `Response` | Register event callback URLs |

### `GiraClient`

The low-level HTTP transport. Available for direct use or mocking in tests.

```python
from x1_controller import GiraClient

client = GiraClient(ip="192.168.1.100", timeout=10.0)
token = client.register("de.myapp.client", "username", "password")
values = client.get_values("some-function-uid")
client.put_value("some-datapoint-uid", 1)
```

### `GiraDevice` (base class)

All device classes share these methods:

| Method | Description |
|---|---|
| `update_values()` | Fetch current datapoint values from the device |
| `set_value(datapoint_name, value)` | Set a named datapoint directly |

### Enums

| Enum | Values | Used by |
|---|---|---|
| `OnOff` | `ON`, `OFF` | All on/off properties (`device.on_off`, `is_playing`, etc.) |
| `HVACMode` | `AUTO`, `COMFORT`, `STANDBY`, `ECONOMY`, `BUILDING_PROTECTION` | `KNXHeatingCoolingSwitchable.set_mode()` |
| `HeatCoolMode` | `HEAT`, `COOL` | `KNXHeatingCoolingSwitchable.set_heat_cool_mode()` |
| `FanCoilMode` | `AUTO`, `HEATING`, `COOLING`, `FAN`, `DRY` | `KNXFanCoil.set_mode()` |

---

## Architecture

```
┌──────────────────────┐     ┌─────────────────┐     ┌──────────────────────┐
│   GiraController     │────>│   GiraClient     │────>│  Gira X1 REST API    │
│   controller.py      │<────│   client.py      │<────│  (HTTPS / KNX)       │
└──────────┬───────────┘     └─────────────────┘     └──────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│                  GiraDevice subclasses                │
│   KNXDimmer · Switch · BlindWithPos · KNXFanCoil ...  │
│                     devices.py                        │
└──────────────────────────────────────────────────────┘
```

| Module | Responsibility |
|---|---|
| `client.py` | `GiraClient` — owns the `requests.Session`, SSL config, token lifecycle, all raw endpoint calls |
| `controller.py` | `GiraController` — delegates HTTP to `GiraClient`, caches config and devices, user-facing API |
| `devices.py` | 23 device classes + factory — device logic only, calls `client.put_value()` / `client.get_values()` |
| `enums.py` | Typed states: `OnOff`, `HVACMode`, `HeatCoolMode`, `FanCoilMode` |
| `errors.py` | `GiraControllerError`, `AuthenticationError`, `GiraConnectionError` |

---

## Development

```bash
uv sync --dev
uv run ruff check .        # lint
uv run ruff format .       # format
uv run mypy src/           # type check
uv run pytest              # tests
```

---

## License

MIT License
