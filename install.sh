#!/bin/bash
# V4L2 Control UI - Installation Script
# This script installs the V4L2 Control UI to your system

set -e

INSTALL_DIR="$HOME/v4l2-ui"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/v4l2-ui"

echo "========================================="
echo "V4L2 Control UI - Installation Script"
echo "========================================="
echo ""

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3 first:"
    echo "  sudo apt-get update && sudo apt-get install python3"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Check for v4l2-ctl
if ! command -v v4l2-ctl &> /dev/null; then
    echo "WARNING: v4l2-ctl is not installed!"
    echo "Installing v4l-utils..."
    sudo apt-get update
    sudo apt-get install -y v4l-utils
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install v4l-utils"
        echo "Please install manually: sudo apt-get install v4l-utils"
        exit 1
    fi
fi

echo "✓ v4l2-ctl found"

# Check for video devices
if ! ls /dev/video* &> /dev/null; then
    echo "WARNING: No video devices found at /dev/video*"
    echo "Make sure your camera is connected."
    echo "Installation will continue, but the tool won't work until a camera is connected."
fi

# Create directories
echo ""
echo "Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$CONFIG_DIR/presets"

echo "✓ Directories created"

# Copy files
echo ""
echo "Installing files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if we're already in the install directory
if [ "$SCRIPT_DIR" = "$INSTALL_DIR" ]; then
    echo "✓ Already running from install directory ($INSTALL_DIR)"
    if [ -f "$INSTALL_DIR/v4l2_control.py" ]; then
        chmod +x "$INSTALL_DIR/v4l2_control.py"
        echo "✓ Set executable permissions on v4l2_control.py"
    else
        echo "ERROR: v4l2_control.py not found in $INSTALL_DIR"
        exit 1
    fi
else
    # Copy files from source to install directory
    if [ -f "$SCRIPT_DIR/v4l2_control.py" ]; then
        cp "$SCRIPT_DIR/v4l2_control.py" "$INSTALL_DIR/"
        chmod +x "$INSTALL_DIR/v4l2_control.py"
        echo "✓ Copied v4l2_control.py"
    else
        echo "ERROR: v4l2_control.py not found in $SCRIPT_DIR"
        exit 1
    fi

    if [ -f "$SCRIPT_DIR/README.md" ]; then
        cp "$SCRIPT_DIR/README.md" "$INSTALL_DIR/"
        echo "✓ Copied README.md"
    fi
fi

# Create launcher script in .local/bin
cat > "$BIN_DIR/v4l2-ui" << 'EOF'
#!/bin/bash
python3 "$HOME/v4l2-ui/v4l2_control.py" "$@"
EOF

chmod +x "$BIN_DIR/v4l2-ui"
echo "✓ Created launcher script"

# Check if .local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "WARNING: $HOME/.local/bin is not in your PATH"
    echo "Add this line to your ~/.bashrc or ~/.profile:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then run: source ~/.bashrc"
    echo ""
    echo "For now, you can run the tool with: $BIN_DIR/v4l2-ui"
else
    echo "✓ $HOME/.local/bin is in PATH"
fi

# Check video group membership
if ! groups | grep -q video; then
    echo ""
    echo "WARNING: Your user is not in the 'video' group"
    echo "This may cause permission issues with camera access."
    echo "To fix this, run:"
    echo "  sudo usermod -a -G video $USER"
    echo "Then log out and log back in for changes to take effect."
fi

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "To run the V4L2 Control UI:"
if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
    echo "  v4l2-ui"
else
    echo "  $BIN_DIR/v4l2-ui"
    echo "  (or add ~/.local/bin to PATH and run: v4l2-ui)"
fi
echo ""
echo "For help and documentation, see:"
echo "  $INSTALL_DIR/README.md"
echo ""
