# Upload Assistant GUI Manager - Docker Setup

This Docker setup provides a containerized environment for running the Upload Assistant GUI Manager with proper X11 forwarding for GUI display.

## Quick Start

### 1. Prerequisites

**On Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose x11-xserver-utils xauth
```

**On CentOS/RHEL:**
```bash
sudo yum install -y docker docker-compose xorg-x11-server-utils xorg-x11-xauth
```

**Or use the Makefile:**
```bash
make install-deps
```

### 2. Setup and Run

```bash
# Clone/download the files to a directory
cd upload-assistant-gui

# One-time setup (installs dependencies, creates directories, builds image)
make setup

# Run the application
make run
```

## File Structure

```
upload-assistant-gui/
├── Dockerfile              # Main container definition
├── docker-compose.yml      # Docker Compose configuration
├── requirements.txt        # Python dependencies
├── entrypoint.sh           # Container startup script
├── supervisor.conf         # Process management
├── Makefile               # Easy command shortcuts
├── ua_gui_manager.py      # Main application (from previous artifact)
├── config/                # Configuration files (mounted)
├── logs/                  # Application logs (mounted)
└── README.md             # This file
```

## Available Commands

### Using Makefile (Recommended)

| Command | Description |
|---------|-------------|
| `make setup` | Complete initial setup |
| `make build` | Build Docker image |
| `make run` | Run GUI application |
| `make run-bg` | Run in background |
| `make stop` | Stop container |
| `make logs` | View logs |
| `make shell` | Open shell in container |
| `make clean` | Remove container and image |

### Using Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild
docker-compose build
```

### Manual Docker Commands

```bash
# Build image
docker build -t ua-gui-manager .

# Run with GUI support
docker run -it --rm \
    --name ua-gui-manager \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v $HOME/.Xauthority:/home/appuser/.Xauthority:ro \
    -v $(pwd)/config:/config \
    -v $(pwd)/logs:/logs \
    -v /mnt/user/appdata/cross-pollinator/logs:/mnt/user/appdata/cross-pollinator/logs:ro \
    -v /mnt/user/data/torrents:/mnt/user/data/torrents:rw \
    --network host \
    --security-opt seccomp:unconfined \
    ua-gui-manager
```

## Volume Mounts

The container uses several volume mounts for data persistence and integration:

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./config` | `/config` | Application configuration |
| `./logs` | `/logs` | Application logs |
| `/mnt/user/appdata/cross-pollinator/logs` | `/mnt/user/appdata/cross-pollinator/logs` | Cross-pollinator logs (read-only) |
| `/mnt/user/data/torrents` | `/mnt/user/data/torrents` | Torrents directory (read-write) |
| `/tmp/.X11-unix` | `/tmp/.X11-unix` | X11 socket for GUI |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISPLAY` | `:0` | X11 display for GUI |
| `PYTHONUNBUFFERED` | `1` | Python output buffering |

### Configuration File

The application configuration is stored in `./config/ua_gui_config.ini`:

```ini
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
# ... other Upload Assistant arguments
```

## Troubleshooting

### GUI Not Displaying

1. **Enable X11 forwarding:**
   ```bash
   xhost +local:docker
   export DISPLAY=:0
   ```

2. **Check X11 socket permissions:**
   ```bash
   ls -la /tmp/.X11-unix/
   ```

3. **Test GUI availability:**
   ```bash
   make test-gui
   ```

### Permission Issues

1. **Fix directory permissions:**
   ```bash
   sudo chown -R $USER:$USER ./config ./logs
   ```

2. **Check mount point permissions:**
   ```bash
   ls -la /mnt/user/data/torrents
   ls -la /mnt/user/appdata/cross-pollinator/logs
   ```

### Container Won't Start

1. **Check Docker daemon:**
   ```bash
   sudo systemctl status docker
   sudo systemctl start docker
   ```

2. **View container logs:**
   ```bash
   make logs
   # or
   docker logs ua-gui-manager
   ```

3. **Check for port conflicts:**
   ```bash
   docker ps -a
   ```

### Upload Assistant Not Found

1. **Mount upload-assistant binary:**
   ```bash
   # Add to docker run command:
   -v /path/to/upload-assistant:/usr/local/bin/upload-assistant:ro
   ```

2. **Or install in container:**
   ```bash
   make shell
   # Inside container:
   pip install upload-assistant
   ```

## Advanced Usage

### Development Mode

Mount your source code for live editing:

```bash
make dev
```

This mounts `ua_gui_manager.py` as read-only so you can edit it on the host and restart the container to see changes.

### Custom Paths

Edit `docker-compose.yml` to adjust mount paths:

```yaml
volumes:
  - /your/custom/torrents/path:/mnt/user/data/torrents:rw
  - /your/custom/logs/path:/mnt/user/appdata/cross-pollinator/logs:ro
```

### Running Without GUI (Headless)

For testing or automation, you can run without X11:

```bash
docker run -it --rm \
    --name ua-gui-manager-headless \
    -v $(pwd)/config:/config \
    -v $(pwd)/logs:/logs \
    ua-gui-manager bash
```

### Using with VNC

For remote GUI access, you can set up VNC:

1. **Install VNC server in container:**
   ```dockerfile
   RUN apt-get install -y tightvncserver
   ```

2. **Start VNC server:**
   ```bash
   vncserver :1 -geometry 1024x768 -depth 24
   ```

3. **Connect with VNC client to localhost:5901**

## Security Considerations

- The container runs with user privileges (UID 1000)
- X11 forwarding is enabled only for local connections
- File system access is limited to mounted volumes
- Network access is restricted to host network for X11

## Performance Tips

1. **Use Docker volumes for better performance:**
   ```bash
   docker volume create ua-gui-config
   docker volume create ua-gui-logs
   ```

2. **Limit container resources:**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 512M
         cpus: '1.0'
   ```

3. **Use multi-stage builds for smaller images:**
   See Dockerfile for optimization opportunities.

## Backup and Restore

### Backup Configuration
```bash
make backup-config
# Creates: config-backup-YYYYMMDD-HHMMSS.tar.gz
```

### Restore Configuration
```bash
tar -xzf config-backup-YYYYMMDD-HHMMSS.tar.gz
```

## Support

For issues with the Docker setup:

1. Check the troubleshooting section above
2. Verify your system meets the prerequisites
3. Test GUI availability: `make test-gui`
4. Check container logs: `make logs`

For application-specific issues, refer to the main application documentation.