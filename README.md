# V4L2 Control UI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Interactive terminal-based UI for managing v4l2-ctl camera settings via SSH/PuTTY.

> 🤖 **Vibe coded with AI:** This project was collaboratively developed with Claude (Anthropic AI). Human creativity meets AI assistance!

## Preview

```
Device: /dev/video0 - UVC Camera (046d:0825)                    [d] Change Device | [r] Refresh | [q] Quit
═══════════════════════════════════════════════════════════════════════════════════════════════════════

User Controls
  brightness                            128  [0-255, step 1]       ◄───────●────────►
  contrast                               32  [0-255, step 1]       ◄─●──────────────►
  saturation                             32  [0-255, step 1]       ◄─●──────────────►
  white_balance_automatic               OFF  [toggle]              [ ] ON  [●] OFF
  gain                                   64  [0-255, step 1]       ◄───●────────────►
  power_line_frequency                60 Hz  [menu]                [Disabled | 50 Hz | 60 Hz]
> white_balance_temperature            4000  [0-10000, step 10]    ◄──────●─────────►
  sharpness                              24  [0-255, step 1]       ◄─●──────────────►
  backlight_compensation                  0  [0-1, step 1]         ◄●───────────────►
Camera Controls
  auto_exposure                  Aperture P  [menu]                [Manual Mode | Aperture Priority Mode]
  exposure_time_absolute                336  [1-10000, step 1]     ◄●───────────────► (inactive)
  exposure_dynamic_framerate            OFF  [toggle]              [ ] ON  [●] OFF

↑↓: Navigate | ←→: Adjust | Enter: Edit | Space: Toggle | 0: Default | s: Save | l: Load
v4l2ctl: white_balance_automatic=0
Set white_balance_temperature = 4000
```

## One-Line Installation

Copy and paste this command to install and run:

```bash
cd ~ && git clone https://github.com/nic335/v4l2-ui.git && cd v4l2-ui && chmod +x v4l2-ui install.sh && ./install.sh
```

Or for standalone mode (no installation):

```bash
cd ~ && git clone https://github.com/nic335/v4l2-ui.git && cd v4l2-ui && chmod +x v4l2-ui && ./v4l2-ui
```

## Quick Start (Already Cloned)

If you already have the repository:

```bash
cd ~/v4l2-ui
./v4l2-ui
```

That's it! The tool runs directly from its directory. No installation required.

**First time?** Make it executable: `chmod +x v4l2-ui v4l2_control.py`

## Features

- **Live List Interface**: View all camera controls in a single scrollable list
- **Real-time Adjustment**: Changes apply immediately as you adjust values
- **Multiple Control Types**: Supports integer sliders, boolean toggles, and menu options
- **Device Selection**: Choose from all available V4L2 video devices
- **Visual Feedback**: Sliders, checkboxes, and status messages for clear feedback

## Requirements

- Python 3.x (built-in on most Linux systems)
- v4l2-ctl (from v4l-utils package)
- Curses library (built-in with Python)

## Installation

### Option 1: Standalone Mode (Recommended)

No installation needed! Just run from the directory:

```bash
cd v4l2-ui
chmod +x v4l2-ui v4l2_control.py  # First time only
./v4l2-ui
```

### Option 2: System-Wide Installation (Optional)

For access from anywhere on your system:

```bash
cd v4l2-ui
./install.sh
```

Then run from anywhere:
```bash
v4l2-ui
```

## Usage

### Run the UI

**Standalone mode:**
```bash
cd v4l2-ui
./v4l2-ui
```

**After installation:**
```bash
v4l2-ui
```

**Direct Python:**
```bash
python3 v4l2_control.py
```

### Navigation

**Device Selection Screen:**
- `↑↓` - Navigate between devices
- `Enter` - Select device
- `q` - Quit

**Control Screen:**
- `↑↓` - Navigate between controls
- `←→` - Adjust selected control value (applies immediately)
  - **Hold ←→** for progressive speed: x1 → x10 → x100
- `Enter` - Type exact value for integer controls
- `Space` - Toggle boolean controls (ON/OFF)
- `0` - Reset selected control to default value
- `s` - Save current settings as a preset
- `l` - Load settings from a saved preset
- `d` - Change device
- `r` - Refresh all control values
- `q` - Quit application

### Crowsnest Configuration

The bottom line of the screen displays a **crowsnest-compatible configuration string** that updates in real-time as you adjust controls. This line can be copied directly into your crowsnest configuration file.

**Example output:**
```
v4l2ctl: power_line_frequency=2,focus_absolute=250,focus_automatic_continuous=0,brightness=128,contrast=32
```

Simply copy this line and paste it into your crowsnest camera configuration to preserve your current settings.

### Presets

Save and load your favorite camera configurations for quick switching between different setups.

**Saving a Preset:**
1. Adjust controls to your desired settings
2. Press `s` to save
3. Enter a name for the preset (e.g., "daylight", "lowlight", "streaming")
4. Preset is saved to `~/.config/v4l2-ui/presets/`

**Loading a Preset:**
1. Press `l` to load
2. Use `↑↓` to select a preset from the list
3. Press `Enter` to apply the preset
4. All saved control values will be applied immediately

**Reset to Default:**
- Navigate to any control and press `0` to reset it to the camera's default value
- Useful for undoing changes or starting fresh

Presets are stored as JSON files and include:
- Device information
- Timestamp of when saved
- All active control values (inactive controls are not saved)

## Control Types

### Integer Controls
- Examples: brightness, contrast, saturation, gain, white_balance_temperature
- Use `←→` arrows to increment/decrement by step value
- **Progressive Speed:** Hold arrow keys for faster adjustment
  - **First ~5 presses:** Normal speed (x1)
  - **After ~5 presses:** Fast speed (x10)
  - **After ~15 presses:** Very fast speed (x100)
  - Status message shows multiplier: `(x10)` or `(x100)`
- Press `Enter` to type an exact value
- Visual slider shows current position in range
- Perfect for controls with large ranges (e.g., 0-10000)

### Boolean Controls
- Examples: white_balance_automatic, exposure_dynamic_framerate
- Press `Space` to toggle ON/OFF
- Visual checkbox shows current state

### Menu Controls
- Examples: auto_exposure, power_line_frequency
- Use `←→` arrows to cycle through available options
- Shows all available options in brackets

## Examples

### Adjusting Camera Brightness
1. Run `~/v4l2-ui/v4l2-ui`
2. Select your camera device (e.g., `/dev/video0`)
3. Navigate to `brightness` with `↑↓` arrows
4. Use `←→` to adjust, or press `Enter` to type exact value
5. Changes apply immediately

### Toggling Auto Exposure
1. Navigate to `white_balance_automatic` or similar boolean control
2. Press `Space` to toggle ON/OFF
3. Change takes effect immediately

## Troubleshooting

### No devices found
- Check camera connection: `ls /dev/video*`
- Verify v4l2-ctl is installed: `which v4l2-ctl`

### Permission denied
- Add user to video group: `sudo usermod -a -G video $USER`
- Log out and back in for changes to take effect

### Controls inactive
- Some controls depend on others (e.g., `white_balance_temperature` requires `white_balance_automatic` to be OFF)
- Toggle the parent control to activate dependent controls

### Screen flickering
- Update to latest version: `cd ~/v4l2-ui && git pull`
- Try a different terminal emulator
- Ensure terminal supports UTF-8 encoding

## Contributing

We welcome contributions! Whether it's:
- 🐛 Bug fixes
- ✨ New features
- 📝 Documentation improvements
- 🎨 UI enhancements
- 🔧 Performance optimizations

**Pull requests are welcome!** See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

You are free to:
- ✅ Use commercially
- ✅ Modify
- ✅ Distribute
- ✅ Private use

## Acknowledgments

- Built with Python and curses
- Developed collaboratively with Claude AI (Anthropic)
- Inspired by the need for easy camera control over SSH
- Thanks to all contributors!
