# V4L2 Control UI - Installation & Sharing Guide

## Quick Installation Checklist

For your friends to install and use this tool, they need to:

- [ ] **Linux system** (Raspberry Pi, Ubuntu, Debian, etc.)
- [ ] **Python 3** installed
- [ ] **v4l-utils** package installed
- [ ] **USB camera** or built-in camera connected
- [ ] **User in video group** (for camera permissions)
- [ ] **SSH access** (if using remotely)

## Installation Methods

### Method 1: Automated Installation (Recommended)

1. **Download or copy the v4l2-ui folder** to your system
2. **Run the installation script:**
   ```bash
   cd v4l2-ui
   chmod +x install.sh
   ./install.sh
   ```
3. **Follow any warnings** about PATH or video group
4. **Run the tool:**
   ```bash
   v4l2-ui
   ```

### Method 2: Manual Installation

1. **Install dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install python3 v4l-utils
   ```

2. **Copy files to your home directory:**
   ```bash
   mkdir -p ~/v4l2-ui
   cp v4l2_control.py ~/v4l2-ui/
   cp README.md ~/v4l2-ui/
   chmod +x ~/v4l2-ui/v4l2_control.py
   ```

3. **Create launcher (optional but recommended):**
   ```bash
   mkdir -p ~/.local/bin
   echo '#!/bin/bash' > ~/.local/bin/v4l2-ui
   echo 'python3 "$HOME/v4l2-ui/v4l2_control.py" "$@"' >> ~/.local/bin/v4l2-ui
   chmod +x ~/.local/bin/v4l2-ui
   ```

4. **Add to PATH (if not already):**
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

5. **Run the tool:**
   ```bash
   v4l2-ui
   ```

## System Requirements

### Required
- **Operating System:** Linux (tested on Raspberry Pi OS, Ubuntu, Debian)
- **Python:** Version 3.7 or higher
- **v4l-utils:** For v4l2-ctl command
- **Camera:** Any V4L2-compatible USB or built-in camera

### Optional
- **SSH client:** PuTTY (Windows) or terminal (Linux/Mac) for remote access
- **Terminal:** 80x24 minimum, larger recommended for better display

## Pre-Installation Checks

### 1. Check Python Version
```bash
python3 --version
```
Should show Python 3.7 or higher.

### 2. Check for v4l2-ctl
```bash
which v4l2-ctl
```
If not found, install with:
```bash
sudo apt-get install v4l-utils
```

### 3. Check for Camera Devices
```bash
v4l2-ctl --list-devices
```
Should show your camera(s). If empty, check camera connection.

### 4. Check Video Group Membership
```bash
groups
```
Should include "video". If not:
```bash
sudo usermod -a -G video $USER
```
Then log out and back in.

### 5. Test Camera Access
```bash
v4l2-ctl -d /dev/video0 --list-ctrls
```
Should show camera controls. If permission denied, check video group.

## Sharing with Friends

### Option 1: Share as Archive

1. **Create a distributable archive:**
   ```bash
   cd ~
   tar -czf v4l2-ui.tar.gz v4l2-ui/
   ```

2. **Share the file** via USB, email, or file transfer

3. **Friends extract and install:**
   ```bash
   tar -xzf v4l2-ui.tar.gz
   cd v4l2-ui
   ./install.sh
   ```

### Option 2: Share via Git Repository

1. **Create a Git repository:**
   ```bash
   cd ~/v4l2-ui
   git init
   git add .
   git commit -m "Initial commit of V4L2 Control UI"
   ```

2. **Push to GitHub/GitLab** (if you have an account)

3. **Friends clone and install:**
   ```bash
   git clone <your-repo-url>
   cd v4l2-ui
   ./install.sh
   ```

### Option 3: Share Individual Files

Send your friends these files:
- `v4l2_control.py` - Main application
- `install.sh` - Installation script
- `README.md` - User documentation
- `INSTALL.md` - This installation guide

They can then run `./install.sh` or install manually.

## Post-Installation Setup

### 1. Test the Installation
```bash
v4l2-ui
```
Should open the device selection screen.

### 2. Configure for Remote Access (Optional)

If using over SSH/PuTTY:
- **Terminal size:** Resize your terminal to at least 100x30 for best experience
- **Color support:** Ensure your terminal supports colors
- **UTF-8 encoding:** Make sure terminal is set to UTF-8

### 3. Create Your First Preset

1. Run `v4l2-ui`
2. Select your camera
3. Adjust settings to your preference
4. Press `s` to save
5. Name it (e.g., "default", "streaming", "recording")

## Troubleshooting Common Issues

### "No V4L2 devices found"
- **Check camera connection:** `ls /dev/video*`
- **Check USB connection:** Try different USB port
- **Check driver:** `dmesg | grep video`

### "Permission denied" errors
- **Add user to video group:** `sudo usermod -a -G video $USER`
- **Log out and back in** for changes to take effect
- **Check device permissions:** `ls -l /dev/video0`

### "Command not found: v4l2-ui"
- **Check PATH:** `echo $PATH` should include `~/.local/bin`
- **Add to PATH:** `export PATH="$HOME/.local/bin:$PATH"`
- **Or use full path:** `~/.local/bin/v4l2-ui`

### "Failed to set control" messages
- **Some controls are read-only** or depend on other settings
- **Check if control is inactive** (shown in red with "(inactive)")
- **Try toggling related controls** (e.g., auto_exposure affects exposure_time)

### Terminal display issues
- **Resize terminal:** Make it larger (100x30 recommended)
- **Check UTF-8:** Terminal should support UTF-8 encoding
- **Try different terminal:** Some terminals have better curses support

### Controls show as inactive
- **This is normal** for dependent controls
- **Example:** `white_balance_temperature` is inactive when `white_balance_automatic` is ON
- **Toggle the parent control** to make dependent controls active

## Usage Quick Reference

### Navigation
- `↑↓` - Move between controls
- `←→` - Adjust values
- `Enter` - Type exact value
- `Space` - Toggle boolean
- `0` - Reset to default
- `s` - Save preset
- `l` - Load preset
- `d` - Change device
- `r` - Refresh
- `q` - Quit

### Tips for Friends

1. **Start with defaults:** Press `0` on each control to reset to camera defaults
2. **Save often:** Create presets for different scenarios (daylight, lowlight, etc.)
3. **Use crowsnest line:** Copy the bottom line for your crowsnest config
4. **Experiment safely:** All changes are live but can be reset with `0`
5. **Check inactive controls:** Some controls only work when others are set correctly

## Support & Documentation

- **README.md:** Full user guide with examples
- **Crowsnest integration:** Bottom line shows config for crowsnest
- **Presets location:** `~/.config/v4l2-ui/presets/`
- **No internet required:** Works completely offline

## Uninstallation

To remove the tool:
```bash
rm -rf ~/v4l2-ui
rm ~/.local/bin/v4l2-ui
rm -rf ~/.config/v4l2-ui
```

## License & Credits

This tool is free to use, modify, and share.
Created for easy camera control over SSH/PuTTY connections.
