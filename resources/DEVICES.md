# Gira X1 Controller - Implemented Devices

This document provides a comprehensive overview of all implemented device classes, their capabilities, and limitations based on the Gira IoT REST API v2 documentation.

## Device Support Summary

| Device Class | Channel Type | Status | Notes |
|-------------|-------------|--------|-------|
| Switch | `de.gira.schema.channels.Switch` | Full Support | |
| KNXDimmer | `de.gira.schema.channels.KNX.Dimmer` | Full Support | |
| DimmerRGBW | `de.gira.schema.channels.DimmerRGBW` | Full Support | |
| DimmerWhite | `de.gira.schema.channels.DimmerWhite` | Full Support | |
| BlindWithPos | `de.gira.schema.channels.BlindWithPos` | Full Support | |
| Trigger | `de.gira.schema.channels.Trigger` | Full Support | |
| SceneSet | `de.gira.schema.channels.SceneSet` | Full Support | |
| SceneControl | `de.gira.schema.channels.SceneControl` | Full Support | |
| RoomTemperatureSwitchable | `de.gira.schema.channels.RoomTemperatureSwitchable` | Full Support | |
| KNXHeatingCoolingSwitchable | `de.gira.schema.channels.KNX.HeatingCoolingSwitchable` | Full Support | |
| KNXFanCoil | `de.gira.schema.channels.KNX.FanCoil` | Full Support | |
| AudioWithPlaylist | `de.gira.schema.channels.AudioWithPlaylist` | Full Support | |
| SonosAudio | `de.gira.schema.channels.Sonos.Audio` | Full Support | |
| Camera | `de.gira.schema.channels.Camera` | Full Support | |
| Link | `de.gira.schema.channels.Link` | Full Support | |
| Binary | `de.gira.schema.channels.Binary` | Full Support | |
| DWord | `de.gira.schema.channels.DWord` | Full Support | |
| Integer | `de.gira.schema.channels.Integer` | Full Support | |
| Float | `de.gira.schema.channels.Float` | Full Support | |
| String | `de.gira.schema.channels.String` | Full Support | |
| Byte | `de.gira.schema.channels.Byte` | Full Support | |
| Percent | `de.gira.schema.channels.Percent` | Full Support | |
| Temperature | `de.gira.schema.channels.Temperature` | Full Support | |

## Detailed Device Documentation

### Lighting Devices

#### Switch
Simple binary on/off control.

**Actions:**
- `turn_on()` - Turn switch on
- `turn_off()` - Turn switch off
- `toggle()` - Toggle current state

**Properties:**
- `on_off` - Current state ("0" or "1")

---

#### KNXDimmer
Dimmable light with optional brightness and shift control.

**Actions:**
- `turn_on()` - Turn light on
- `turn_off()` - Turn light off
- `toggle()` - Toggle current state
- `dim_to(percent)` - Set brightness (0-100)

**Properties:**
- `on_off` - Current state
- `brightness` - Current brightness (0-100)
- `has_brightness` - Whether brightness control is available
- `has_shift` - Whether shift control is available

---

#### DimmerRGBW
RGBW color dimmer for colored lights.

**Actions:**
- `turn_on()` / `turn_off()` / `toggle()`
- `set_brightness(percent)` - Set overall brightness
- `set_color(red, green, blue)` - Set RGB values (each 0-100)
- `set_white(percent)` - Set white channel

**Properties:**
- `on_off`, `brightness`, `red`, `green`, `blue`, `white`
- `has_brightness`, `has_white`

---

#### DimmerWhite
Tunable white dimmer for color temperature control.

**Actions:**
- `turn_on()` / `turn_off()` / `toggle()`
- `set_brightness(percent)`
- `set_color_temperature(kelvin)` - Set color temperature in Kelvin

**Properties:**
- `on_off`, `brightness`, `color_temperature`
- `has_brightness`

---

### Blinds & Shutters

#### BlindWithPos
Motorized blinds/shutters with position control.

**Actions:**
- `move_up()` / `move_down()` - Continuous movement
- `step_up()` / `step_down()` - Small step movement
- `set_position(percent)` - Set blind position (0-100)
- `set_slat_position(percent)` - Set slat angle (0-100)

**Properties:**
- `position`, `slat_position`
- `has_position`, `has_slat_position`

**Note:** Movement datapoints are write-only, so current movement state cannot be read.

---

### Triggers & Scenes

#### Trigger
Simple trigger for on/off or press-and-hold functions.

**Actions:**
- `trigger_on()` - Send trigger value 1
- `trigger_off()` - Send trigger value 0
- `press()` / `release()` - For press-and-hold functionality

**Note:** Trigger is write-only with events. Cannot read current state.

---

#### SceneSet
Scene control with execute and optional learn capability.

**Actions:**
- `execute_scene(scene_number)` - Execute a scene
- `teach_scene(scene_number)` - Learn/save current state as scene

**Properties:**
- `has_teach` - Whether scene learning is available

---

#### SceneControl
Scene execution only (no learn capability).

**Actions:**
- `execute_scene(scene_number)` - Execute a scene

---

### Climate Control

#### RoomTemperatureSwitchable
Room temperature control with optional on/off (e.g., sauna).

**Actions:**
- `set_temperature(temperature)` - Set target temperature
- `turn_on()` / `turn_off()` - Switch heating on/off

**Properties:**
- `current_temperature` - Current temperature (read-only)
- `set_point` - Target temperature
- `on_off`, `has_on_off`

---

#### KNXHeatingCoolingSwitchable
Advanced heating and cooling control.

**Actions:**
- `set_temperature(temperature)`
- `set_mode(mode)` - Set operating mode
- `set_presence(present)` - Set presence status
- `set_heat_cool_mode(heat)` - True for heat, False for cool
- `turn_on()` / `turn_off()`

**Properties:**
- `current_temperature`, `set_point`, `status`
- `is_heating`, `is_cooling` (read-only)
- `on_off`, `presence`

**Note:** Mode and presence datapoints may be optional depending on device configuration.

---

#### KNXFanCoil
Air conditioning / fan coil unit control.

**Actions:**
- `turn_on()` / `turn_off()`
- `set_temperature(temperature)`
- `set_mode(mode)`
- `set_fan_speed(speed)`

**Properties:**
- `current_temperature`, `set_point`
- `on_off`, `mode`, `fan_speed`
- `error`, `error_text` (read-only)
- `has_fan_speed`

---

### Audio Devices

#### AudioWithPlaylist
General audio player with playlist support.

**Actions:**
- `play()` / `pause()`
- `set_volume(percent)`
- `mute()` / `unmute()`
- `next_track()` / `previous_track()`
- `select_playlist(index)`
- `next_playlist()` / `previous_playlist()`
- `set_shuffle(enabled)` / `set_repeat(enabled)`

**Properties:**
- `is_playing`, `volume`, `is_muted`
- `title`, `album`, `artist` (read-only)
- `playlist_name`, `shuffle`, `repeat`

---

#### SonosAudio
Extended Sonos audio control (inherits from AudioWithPlaylist).

**Additional Actions:**
- `shift_volume(delta)` - Relative volume adjustment (-100 to 100)

**Additional Properties:**
- `cover_url` - Album cover URL
- `zone_name` - Sonos zone name
- `playlists` - Available playlists (JSON)
- `valid_play_modes`, `transport_actions`

---

### Media Devices

#### Camera
IP camera view control.

**Actions:**
- `activate()` / `deactivate()`

**Properties:**
- `is_active`

**Note:** This controls whether the camera is being shown in the UI, not the camera itself.

---

#### Link
Web content display control.

**Actions:**
- `activate()` / `deactivate()`

**Properties:**
- `is_active`

**Note:** This controls whether the website is being shown in the UI.

---

### Value Type Devices

These are simple single-value devices for generic data handling.

| Class | Value Type | Range |
|-------|-----------|-------|
| Binary | 0 or 1 | Boolean |
| Byte | 0-255 | 8-bit unsigned |
| DWord | 0-4294967295 | 32-bit unsigned |
| Integer | Signed integer | Platform dependent |
| Float | Decimal | IEEE 754 |
| String | Text | UTF-8 |
| Percent | 0-100 or 0-255 | Percentage |
| Temperature | Decimal | Temperature value |

**Common Actions:**
- `set(value)` - Set the value

**Common Properties:**
- `value` - Current value

---

## General Usage Notes

### Value Updates
All devices support:
- `update_values()` - Fetch current values from the device
- Values are returned as strings from the API and need to be converted

### Error Handling
- All action methods return `bool` indicating success
- Methods return `False` if:
  - Datapoint doesn't exist on device
  - Network request fails
  - Device returns error

### Optional Datapoints
Many devices have optional datapoints (marked with "O" in the API documentation). Use the `has_*` properties to check availability before using related methods.

### Callbacks
The `GiraController.register_callbacks()` method allows real-time value updates, but this feature is marked as "untested" in the codebase.

---

## Limitations

### Not Implemented
- Multi-value setting in a single request (`PUT /api/v2/values`)
- Remote Access channel type (`de.gira.schema.channels.RA.RemoteAccess`)

### Read-Only Datapoints
Some datapoints are read-only (e.g., current temperature, error states). These are documented in individual device sections.

### Write-Only Datapoints
Some datapoints are write-only (e.g., Trigger, Step-Up-Down for blinds). These cannot be read back.

---

## Version History

- **v0.2.0** - Complete device implementation covering all Gira IoT REST API v2 channel types
- **v0.1.0** - Initial implementation with Switch, KNXDimmer, BlindWithPos
