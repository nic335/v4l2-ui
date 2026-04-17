# V4L2 Control UI - Sharing Checklist

## For You (The Distributor)

### Before Sharing

- [ ] Test the tool on your system one more time
- [ ] Create a clean copy of the v4l2-ui folder
- [ ] Verify all files are present:
  - [ ] `v4l2_control.py` (main application)
  - [ ] `install.sh` (installation script)
  - [ ] `README.md` (user guide)
  - [ ] `INSTALL.md` (installation guide)
  - [ ] `SHARING-CHECKLIST.md` (this file)

### Package the Tool

Choose one method:

**Method A: Create Archive**
```bash
cd ~
tar -czf v4l2-ui.tar.gz v4l2-ui/
```
Share `v4l2-ui.tar.gz` via USB, email, or file transfer.

**Method B: Git Repository**
```bash
cd ~/v4l2-ui
git init
git add v4l2_control.py install.sh README.md INSTALL.md SHARING-CHECKLIST.md
git commit -m "V4L2 Control UI - Camera control tool for SSH/PuTTY"
# Push to GitHub/GitLab if desired
```

**Method C: Direct File Copy**
Copy these files to USB or shared folder:
- `v4l2_control.py`
- `install.sh`
- `README.md`
- `INSTALL.md`

---

## For Your Friends (The Users)

### Pre-Installation Checklist

Before installing, verify:

- [ ] **Linux system** (Raspberry Pi, Ubuntu, Debian, or similar)
- [ ] **Camera connected** (USB webcam or built-in camera)
- [ ] **Terminal access** (direct or via SSH/PuTTY)
- [ ] **Internet connection** (for installing dependencies)

### Installation Steps

#### Standalone Mode (Easiest - No Installation!)

1. **Get the files:**
   - Extract archive: `tar -xzf v4l2-ui.tar.gz`
   - Or clone repo: `git clone <repo-url>`
   - Or copy files to a folder named `v4l2-ui`

2. **Run it:**
   ```bash
   cd v4l2-ui
   chmod +x v4l2-ui v4l2_control.py  # First time only
   ./v4l2-ui
   ```

#### System-Wide Install (Optional)

If you want to run from anywhere:
```bash
cd v4l2-ui
chmod +x install.sh
./install.sh
```

3. **Follow any warnings** displayed by the installer

4. **If PATH warning appears:**
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

5. **If video group warning appears:**
   ```bash
   sudo usermod -a -G video $USER
   # Then log out and log back in
   ```

6. **Test it:**
   ```bash
   v4l2-ui
   ```

### First-Time Setup

- [ ] Run `v4l2-ui` and select your camera
- [ ] Familiarize yourself with the controls
- [ ] Press `0` on a control to see default reset
- [ ] Create a preset: adjust settings, press `s`, name it
- [ ] Try loading the preset: press `l`, select it

### Verification Checklist

After installation, verify:

- [ ] Tool launches without errors
- [ ] Camera device is detected and listed
- [ ] Controls are displayed correctly
- [ ] Can adjust integer controls with ←→
- [ ] Can toggle boolean controls with Space
- [ ] Can save a preset with `s`
- [ ] Can load a preset with `l`
- [ ] Crowsnest config line appears at bottom

---

## Common Issues & Quick Fixes

### Issue: "No V4L2 devices found"
**Fix:** 
```bash
# Check if camera is detected
ls /dev/video*
v4l2-ctl --list-devices

# If nothing shows, reconnect camera or reboot
```

### Issue: "v4l2-ctl: command not found"
**Fix:**
```bash
sudo apt-get update
sudo apt-get install v4l-utils
```

### Issue: "Permission denied" when accessing camera
**Fix:**
```bash
# Add user to video group
sudo usermod -a -G video $USER
# Log out and log back in
```

### Issue: "v4l2-ui: command not found"
**Fix:**
```bash
# Use full path
~/.local/bin/v4l2-ui

# Or add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Issue: Controls show as "(inactive)"
**Fix:** This is normal! Some controls depend on others:
- `white_balance_temperature` → needs `white_balance_automatic` OFF
- `exposure_time_absolute` → needs `auto_exposure` set to Manual Mode

Toggle the parent control to activate dependent controls.

---

## What to Tell Your Friends

### Quick Pitch

"This is a terminal UI for controlling camera settings over SSH. You can adjust brightness, contrast, exposure, white balance, and more - all from the command line. Perfect for headless Raspberry Pi setups with cameras!"

### Key Features to Highlight

1. **Works over SSH/PuTTY** - No GUI needed
2. **Live adjustment** - Changes apply immediately
3. **Presets** - Save and load your favorite settings
4. **Crowsnest integration** - Copy config line for crowsnest
5. **Reset to defaults** - Press `0` on any control
6. **No dependencies** - Just Python 3 and v4l-utils

### Tips for Friends

1. **Start with defaults:** Press `0` on each control to reset to camera defaults
2. **Save often:** Create presets for different scenarios (daylight, lowlight, etc.)
3. **Use crowsnest line:** Copy the bottom line for your crowsnest config
4. **Experiment safely:** All changes are live but can be reset with `0`
5. **Check inactive controls:** Some controls only work when others are set correctly
6. **Large values:** Hold arrow keys for progressive speed (x1 → x10 → x100) - great for white_balance_temperature!

### Use Cases

- **3D printer cameras** - Adjust camera for better print monitoring
- **Raspberry Pi projects** - Control camera without desktop
- **Remote systems** - Configure camera over SSH
- **Crowsnest users** - Easy way to find optimal settings
- **Multiple cameras** - Switch between devices easily

---

## Support Information

### Where to Get Help

1. **Read the README.md** - Comprehensive user guide
2. **Check INSTALL.md** - Detailed installation and troubleshooting
3. **Test with defaults** - Press `0` to reset controls
4. **Verify camera works** - Test with `v4l2-ctl -d /dev/video0 --list-ctrls`

### What to Include When Asking for Help

If someone has issues, ask them to provide:
- Operating system and version: `uname -a`
- Python version: `python3 --version`
- Camera devices: `v4l2-ctl --list-devices`
- Error message (exact text)
- What they were trying to do

---

## Distribution Methods Comparison

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **Archive (.tar.gz)** | Simple, single file | Manual updates | One-time sharing |
| **Git Repository** | Easy updates, version control | Requires Git knowledge | Ongoing development |
| **Direct Files** | No compression needed | Multiple files to track | Local network sharing |
| **USB Drive** | Works offline | Physical transfer needed | In-person sharing |

---

## Quick Reference Card (Print/Share This)

```
V4L2 CONTROL UI - QUICK REFERENCE
==================================

INSTALLATION:
  cd v4l2-ui && ./install.sh

LAUNCH:
  v4l2-ui

NAVIGATION:
  ↑↓        Navigate controls
  ←→        Adjust values
            Hold ←→ for speed: x1→x10→x100
  Enter     Type exact value
  Space     Toggle ON/OFF
  0         Reset to default
  s         Save preset
  l         Load preset
  d         Change device
  r         Refresh
  q         Quit

REQUIREMENTS:
  - Linux system
  - Python 3
  - v4l-utils package
  - Camera connected
  - User in video group

TROUBLESHOOTING:
  No devices?     ls /dev/video*
  Permission?     sudo usermod -a -G video $USER
  Not found?      export PATH="$HOME/.local/bin:$PATH"

PRESETS LOCATION:
  ~/.config/v4l2-ui/presets/

CROWSNEST CONFIG:
  Bottom line shows v4l2ctl config
  Copy and paste into crowsnest.conf
```

---

## Success Criteria

Your friend has successfully installed when they can:

✅ Launch `v4l2-ui` from terminal
✅ See their camera in the device list
✅ Navigate and adjust controls
✅ Save and load a preset
✅ See the crowsnest config line at bottom
✅ Use it over SSH/PuTTY without issues

---

## Final Notes

- **No internet required** after installation
- **All changes are reversible** - press `0` to reset
- **Safe to experiment** - won't damage camera
- **Works with any V4L2 camera** - USB webcams, Pi cameras, etc.
- **Lightweight** - minimal system resources
- **Fast** - changes apply immediately

Good luck sharing! 🎥
