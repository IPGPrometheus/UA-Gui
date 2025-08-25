#!/bin/bash
set -e

# Docker entrypoint script for Upload Assistant GUI Manager

echo "Starting Upload Assistant GUI Manager..."

# Check if X11 is available
if [ -z "$DISPLAY" ]; then
    echo "Warning: DISPLAY environment variable not set. GUI may not work."
    echo "Make sure to run with: docker run -e DISPLAY=\$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix ..."
fi

# Check X11 connection
if ! xauth list >/dev/null 2>&1; then
    echo "Warning: X11 authentication may not be properly configured."
fi

# Create necessary directories if they don't exist
mkdir -p /config
mkdir -p /logs
mkdir -p /mnt/user/appdata/cross-pollinator/logs
mkdir -p /mnt/user/data/torrents

# Set up configuration directory permissions
if [ -d "/config" ] && [ "$(stat -c '%U' /config)" != "appuser" ]; then
    echo "Setting up configuration directory permissions..."
    sudo chown -R appuser:appuser /config 2>/dev/null || true
fi

# Set up logs directory permissions  
if [ -d "/logs" ] && [ "$(stat -c '%U' /logs)" != "appuser" ]; then
    echo "Setting up logs directory permissions..."
    sudo chown -R appuser:appuser /logs 2>/dev/null || true
fi

# Check if upload-assistant is available
if command -v upload-assistant >/dev/null 2>&1; then
    echo "Upload Assistant found: $(which upload-assistant)"
else
    echo "Warning: upload-assistant not found in PATH. You may need to install it or mount it as a volume."
    echo "Expected location: /usr/local/bin/upload-assistant"
fi

# Check if required directories are mounted
if [ ! -d "/mnt/user/appdata/cross-pollinator/logs" ]; then
    echo "Warning: Cross-pollinator logs directory not found. Creating placeholder..."
    mkdir -p /mnt/user/appdata/cross-pollinator/logs
fi

if [ ! -d "/mnt/user/data/torrents" ]; then
    echo "Warning: Torrents directory not found. Creating placeholder..."
    mkdir -p /mnt/user/data/torrents
fi

# Set up default configuration if it doesn't exist
CONFIG_FILE="/config/ua_gui_config.ini"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating default configuration file..."
    cat > "$CONFIG_FILE" << 'EOF'
[PATHS]
logs_dir = /mnt/user/appdata/cross-pollinator/logs
torrents_dir = /mnt/user/data/torrents
upload_assistant_path = upload-assistant

[UA_ARGS]
tmdb = 
imdb = 
mal = 
category = 
type = 
source = 
edition = 
resolution = 
freeleech = false
tag = 
region = 
season = 
episode = 
daily = false
no_dupe = false
skip_imghost = false
personalrelease = false
EOF
    echo "Default configuration created at $CONFIG_FILE"
fi

# Link config file to expected location
if [ -f "$CONFIG_FILE" ]; then
    ln -sf "$CONFIG_FILE" "/home/appuser/.ua_gui_config.ini" 2>/dev/null || true
fi

# Test GUI availability
echo "Testing GUI availability..."
if python3 -c "import tkinter; root = tkinter.Tk(); root.withdraw(); print('GUI test passed')" 2>/dev/null; then
    echo "GUI environment is ready"
else
    echo "Warning: GUI test failed. The application may not display properly."
    echo "Common solutions:"
    echo "1. Run: xhost +local:docker  # on host system"
    echo "2. Ensure DISPLAY is set: export DISPLAY=:0"
    echo "3. Mount X11 socket: -v /tmp/.X11-unix:/tmp/.X11-unix"
fi

# Function to handle shutdown gracefully
cleanup() {
    echo "Shutting down Upload Assistant GUI Manager..."
    # Kill any background processes
    jobs -p | xargs -r kill
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Log startup information
echo "=== Upload Assistant GUI Manager Startup ==="
echo "User: $(whoami)"
echo "Home: $HOME"
echo "Working Directory: $(pwd)"
echo "Display: $DISPLAY"
echo "Python Version: $(python3 --version)"
echo "Available Terminals: $(which gnome-terminal xterm konsole 2>/dev/null | tr '\n' ' ')"
echo "Upload Assistant: $(which upload-assistant 2>/dev/null || echo 'Not found')"
echo "Configuration: $CONFIG_FILE"
echo "============================================="

# Execute the main command
exec "$@"