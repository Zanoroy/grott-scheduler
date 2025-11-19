#!/bin/bash
#
# Grott Scheduler Installation Script
# For Oracle Linux 2 / RHEL-based systems
#

set -e

echo "=========================================="
echo "Grott Scheduler Installation"
echo "=========================================="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    echo "Please run: sudo bash install.sh"
    exit 1
fi

# Define paths
INSTALL_DIR="/opt/grott-scheduler"
SERVICE_FILE="/etc/systemd/system/grott-scheduler.service"
VENV_DIR="$INSTALL_DIR/venv"

# Check if already installed
if systemctl is-active --quiet grott-scheduler; then
    echo "Grott Scheduler is currently running. Stopping service..."
    systemctl stop grott-scheduler
fi

# Install Python 3 and pip if not present
echo "Step 1: Installing system dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "Installing Python 3..."
    yum install -y python3 python3-pip
else
    echo "Python 3 is already installed: $(python3 --version)"
fi

# Install virtualenv
echo "Installing virtualenv..."
pip3 install --upgrade pip virtualenv

# Create virtual environment
echo
echo "Step 2: Creating Python virtual environment..."
if [ -d "$VENV_DIR" ]; then
    echo "Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

cd "$INSTALL_DIR"
python3 -m venv "$VENV_DIR"

# Activate virtual environment and install dependencies
echo
echo "Step 3: Installing Python dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# Initialize database
echo
echo "Step 4: Initializing database..."
cd "$INSTALL_DIR/database"

if [ -f "scheduler.db" ]; then
    echo "Database already exists. Creating backup..."
    cp scheduler.db "scheduler.db.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Initialize database with schema
source "$VENV_DIR/bin/activate"
python3 << EOF
import sqlite3
import os

db_path = 'scheduler.db'
schema_path = 'schema.sql'

# Create database
conn = sqlite3.connect(db_path)

# Load and execute schema
with open(schema_path, 'r') as f:
    schema = f.read()
    conn.executescript(schema)

conn.commit()
conn.close()

print("Database initialized successfully")
EOF
deactivate

# Create logs directory
echo
echo "Step 5: Creating logs directory..."
mkdir -p "$INSTALL_DIR/logs"
chmod 755 "$INSTALL_DIR/logs"

# Install systemd service
echo
echo "Step 6: Installing systemd service..."
# Update service file to use virtual environment
cat > "$SERVICE_FILE" << 'SERVICEEOF'
[Unit]
Description=Grott Scheduler Service
Documentation=https://github.com/johanmeijer/grott
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/grott-scheduler/backend
ExecStart=/opt/grott-scheduler/venv/bin/python3 /opt/grott-scheduler/backend/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=grott-scheduler

# Environment
Environment="PYTHONUNBUFFERED=1"
Environment="PATH=/opt/grott-scheduler/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Reload systemd
systemctl daemon-reload

# Enable service
echo
echo "Step 7: Enabling and starting service..."
systemctl enable grott-scheduler
systemctl start grott-scheduler

# Wait a moment for service to start
sleep 3

# Check service status
echo
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo
echo "Service Status:"
systemctl status grott-scheduler --no-pager -l

echo
echo "Installation Details:"
echo "  - Install Directory: $INSTALL_DIR"
echo "  - Database: $INSTALL_DIR/database/scheduler.db"
echo "  - Logs: $INSTALL_DIR/logs/scheduler.log"
echo "  - API Endpoint: http://localhost:5783/api"
echo "  - Web Interface: http://<serverip>:5783 (serve via Node-RED)"
echo
echo "Useful Commands:"
echo "  - View logs: journalctl -u grott-scheduler -f"
echo "  - Restart service: systemctl restart grott-scheduler"
echo "  - Stop service: systemctl stop grott-scheduler"
echo "  - Check status: systemctl status grott-scheduler"
echo
echo "Next Steps:"
echo "  1. Configure Grott connection in the web interface (Configuration tab)"
echo "  2. Set up Pushover API keys if desired"
echo "  3. Create your first schedule!"
echo
echo "To serve the web interface via Node-RED:"
echo "  1. Copy $INSTALL_DIR/frontend/index.html to your Node-RED static files"
echo "  2. Or use an HTTP In node to serve the file"
echo "  3. Access via Node-RED URL"
echo

# Check if service is running
if systemctl is-active --quiet grott-scheduler; then
    echo "✓ Grott Scheduler is running successfully!"
else
    echo "✗ WARNING: Service failed to start. Check logs:"
    echo "  journalctl -u grott-scheduler -n 50"
fi

echo
