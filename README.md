# Gira X1 Controller

A Python API wrapper for the Gira X1 smart home controller, providing easy access to the Gira IoT REST API.

## Requirements

- Python >= 3.13
- [uv](https://github.com/astral-sh/uv) (recommended for package management)

## Installation

### Using uv (recommended)

```bash
# Clone the repository
git clone https://github.com/j-tobias/X1_Controller.git
cd X1_Controller

# Install dependencies
uv sync

# Or install in development mode
uv sync --dev
```

### Using pip

```bash
pip install -e .
```

## Quick Start

```python
from x1_controller import GiraController

# Initialize the controller
controller = GiraController("192.168.1.100")

# Check availability
if controller.check_availability():
    print("X1 is available!")

# Register and authenticate
token = controller.register_client("your_username", "your_password")
print(f"Token: {token}")

# Get all devices
devices = controller.get_devices()
for device in devices:
    print(f"Device: {device.display_name} ({device.uid})")

# Get a specific device
dimmer = controller.get_device(display_name="Living Room Light")
if dimmer:
    # Update values from device
    dimmer.update_values()

    # Control the dimmer
    dimmer.toggle()
    dimmer.dim_to(50)  # Set to 50%
    dimmer.turn_off()

# When done
controller.unregister_client()
```

## Supported Devices

- **KNXDimmer** - Dimmable lights with on/off, brightness, and shift control
- **Switch** - Binary on/off switches
- **BlindWithPos** - Motorized blinds with position control

## API Reference

### GiraController

Main controller class for interacting with the X1.

```python
controller = GiraController(ip="192.168.1.100", client_id="de.myapp.client")
```

#### Methods

- `check_availability()` - Check if the X1 API is reachable
- `register_client(username, password)` - Authenticate and get a token
- `unregister_client(token=None)` - Deregister the client
- `get_uid()` - Get configuration unique identifier
- `get_config(filename=None)` - Get X1 configuration (optionally save to file)
- `get_devices()` - Get all devices as objects
- `get_device(display_name=None, uid=None)` - Get a specific device

### Device Classes

All devices inherit from `GiraDevice` and share common methods:

- `update_values()` - Fetch current values from device
- `set_value(datapoint_name, value)` - Set a datapoint value

#### KNXDimmer

```python
dimmer.toggle()           # Toggle on/off
dimmer.turn_on()          # Turn on
dimmer.turn_off()         # Turn off
dimmer.dim_to(percent)    # Set brightness (0-100)

# Properties
dimmer.on_off             # Current on/off state
dimmer.brightness         # Current brightness
dimmer.has_brightness     # Whether brightness control is available
```

#### Switch

```python
switch.toggle()           # Toggle on/off
switch.turn_on()          # Turn on
switch.turn_off()         # Turn off

# Properties
switch.on_off             # Current on/off state
```

#### BlindWithPos

```python
blind.move_up()           # Move blind up
blind.move_down()         # Move blind down
blind.step_up()           # Small step up
blind.step_down()         # Small step down
blind.set_position(50)    # Set position (0-100)
blind.set_slat_position(30)  # Set slat position (0-100)

# Properties
blind.position            # Current position
blind.slat_position       # Current slat position
blind.has_position        # Whether position control is available
blind.has_slat_position   # Whether slat control is available
```

## Development

### Setup development environment

```bash
uv sync --dev
```

### Run linting

```bash
uv run ruff check .
uv run ruff format .
```

### Run type checking

```bash
uv run mypy src/
```

### Run tests

```bash
uv run pytest
```

## Migration from Old API

If you're updating from the old API, here are the key changes:

| Old | New |
|-----|-----|
| `from X1API import GiraControl` | `from x1_controller import GiraController` |
| `gira.availability_check()` | `controller.check_availability()` |
| `gira.get_uid_config()` | `controller.get_config()` |
| `device.displayName` | `device.display_name` |
| `dimmer.dimm_to(50)` | `dimmer.dim_to(50)` |

## License

MIT License
