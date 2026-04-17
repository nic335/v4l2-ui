# V4L2 Control UI - Quick Start

## Standalone Usage (No Installation Required!)

You can run this tool directly from its directory without installing anything.

### 1. Get the Files

Extract the archive or copy the v4l2-ui folder:
```bash
tar -xzf v4l2-ui.tar.gz
cd v4l2-ui
```

### 2. Run It

```bash
./v4l2-ui
```

That's it! No installation needed.

### 3. First Time Setup

If you get a permission error:
```bash
chmod +x v4l2-ui
chmod +x v4l2_control.py
./v4l2-ui
```

## Requirements Check

Before running, make sure you have:

**Check Python 3:**
```bash
python3 --version
```
Should show Python 3.7+. If not: `sudo apt-get install python3`

**Check v4l2-ctl:**
```bash
v4l2-ctl --list-devices
```
If not found: `sudo apt-get install v4l-utils`

**Check Camera:**
```bash
ls /dev/video*
```
Should show at least one video device.

**Check Permissions:**
```bash
groups
```
Should include "video". If not:
```bash
sudo usermod -a -G video $USER
# Log out and back in
```

## Usage Modes

### Standalone Mode (Recommended for Testing)

Run from the v4l2-ui directory:
```bash
cd v4l2-ui
./v4l2-ui
```

### Installed Mode (Optional)

For system-wide access, run the installer:
```bash
cd v4l2-ui
./install.sh
```

Then run from anywhere:
```bash
v4l2-ui
```

## Quick Navigation

Once running:
- `↑↓` - Navigate between controls
- `←→` - Adjust values (applies immediately)
  - **Hold for speed boost:** x1 → x10 → x100
- `Enter` - Type exact value
- `Space` - Toggle ON/OFF
- `0` - Reset to default
- `s` - Save preset
- `l` - Load preset
- `q` - Quit

## Common Issues

**"Permission denied: ./v4l2-ui"**
```bash
chmod +x v4l2-ui v4l2_control.py
```

**"No V4L2 devices found"**
```bash
# Check camera is connected
ls /dev/video*
v4l2-ctl --list-devices
```

**"v4l2-ctl: command not found"**
```bash
sudo apt-get install v4l-utils
```

**"Permission denied" accessing camera**
```bash
sudo usermod -a -G video $USER
# Log out and log back in
```

## Sharing with Friends

Just send them the entire v4l2-ui folder (or the .tar.gz file).

They can:
1. Extract it
2. Run `./v4l2-ui`
3. Done!

No installation required unless they want system-wide access.

## Files Included

- `v4l2-ui` - Launcher script (run this)
- `v4l2_control.py` - Main application
- `install.sh` - Optional installer for system-wide access
- `README.md` - Full user guide
- `INSTALL.md` - Installation guide
- `SHARING-CHECKLIST.md` - Distribution guide
- `QUICKSTART.md` - This file

## Next Steps

1. **Test it:** Run `./v4l2-ui` and select your camera
2. **Adjust settings:** Use arrow keys to change values
3. **Save a preset:** Press `s` and name it
4. **Copy crowsnest config:** Bottom line shows the v4l2ctl config

For detailed documentation, see README.md
