# Grott Scheduler - Installation & Configuration Guide

## Overview

Grott Scheduler is a professional-grade automation system for scheduling commands to Growatt inverters via the Grott proxy. It provides a web-based interface for creating, managing, and monitoring scheduled tasks with retry logic, conditional execution, and failure notifications.

## Features

- **Web Interface**: Bootstrap 5 responsive UI for easy management
- **Multiple Schedule Types**: Daily, weekly, and one-time schedules
- **Command Types**:
  - Single register writes
  - Multi-register writes (for time schedules)
  - Pre-defined templates
  - Custom commands
- **Conditional Execution**: Execute based on register values (e.g., SOC level)
- **Retry Logic**: Automatic retries with configurable attempts and delays
- **Pushover Notifications**: Alert on failures (configurable per-schedule)
- **Execution History**: Comprehensive logging with success/failure tracking
- **RESTful API**: Full API for integration with other systems

## System Requirements

- Oracle Linux 2 / RHEL 7+ / CentOS 7+ (or compatible)
- Python 3.6 or higher
- Internet connection for package installation
- Running Grott proxy instance
- (Optional) Node-RED for serving web interface
- (Optional) Pushover account for notifications

## Installation

### Quick Install

```bash
cd /opt/grott-scheduler
sudo bash install.sh
```

The installation script will:
1. Install Python 3 and dependencies
2. Create Python virtual environment
3. Install required Python packages
4. Initialize SQLite database
5. Create systemd service
6. Start the scheduler service

### Manual Installation

If you prefer to install manually:

```bash
# Install Python 3
sudo yum install -y python3 python3-pip

# Create virtual environment
cd /opt/grott-scheduler
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
cd database
python3 << EOF
import sqlite3
conn = sqlite3.connect('scheduler.db')
with open('schema.sql', 'r') as f:
    conn.executescript(f.read())
conn.commit()
conn.close()
EOF

# Create logs directory
mkdir -p ../logs

# Install systemd service
sudo cp systemd/grott-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable grott-scheduler
sudo systemctl start grott-scheduler
```

## Configuration

### Initial Setup

1. **Access the Web Interface**:
   - Direct: `http://<serverip>:5783/frontend/index.html`
   - Via Node-RED: Configure Node-RED to serve the `frontend/index.html` file

2. **Configure Grott Connection**:
   - Go to **Configuration** tab
   - Set `grott_host` (default: <grottserver>)
   - Set `grott_port` (default: 5782)
   - Set `inverter_serial` (your inverter's serial number, e.g., NTCRBLR00Y)

3. **Configure Pushover (Optional)**:
   - Get your User Key from https://pushover.net/
   - Create an application and get API Token
   - Set `pushover_user_key` and `pushover_api_token` in Configuration
   - Set `max_retries` (default: 5) and `retry_delay` (default: 10 seconds)

### Database Configuration

The database is automatically initialized with default settings:

| Key | Default Value | Description |
|-----|---------------|-------------|
| grott_host | <grottserver> | Grott proxy IP address |
| grott_port | 5782 | Grott proxy HTTP port |
| inverter_serial | NTCRBLR00Y | Default inverter serial number |
| pushover_user_key | (empty) | Pushover user key for notifications |
| pushover_api_token | (empty) | Pushover API token |
| max_retries | 5 | Maximum retry attempts on failure |
| retry_delay | 10 | Delay between retries (seconds) |

## Creating Schedules

### Schedule Types

1. **Daily**: Executes every day at specified time
2. **Weekly**: Executes on selected days of the week
3. **Once**: Executes once on a specific date/time

### Command Types

#### 1. Single Register Write

Write a value to a single register.

**Example**: Set Load First Discharge Stop SOC to 50%
- Command Type: `register`
- Register: `608 - Load First Discharge Stop SOC`
- Value: `50`

#### 2. Multi-Register Write

Write to multiple consecutive registers (commonly used for time schedules).

**Example**: Set Grid First Time Schedule 1 (9:00 AM - 5:00 PM, Enabled)
- Command Type: `multiregister`
- Start Register: `1080`
- End Register: `1082`
- Value: `900-1700-1`

**Value Format**: `StartTime-EndTime-Enable`
- StartTime: HHMM format (e.g., 900 for 9:00 AM)
- EndTime: HHMM format (e.g., 1700 for 5:00 PM)
- Enable: 1 (enabled) or 0 (disabled)

#### 3. Template

Use pre-defined templates for common operations.

**Available Templates**:
- **Load First + SOC 100%**: Switch to Load First mode with full discharge
- **Battery First Mode**: Switch to Battery First mode
- **Grid First Mode**: Switch to Grid First mode
- **Disable All Battery Schedules**: Disable all Grid First time schedules

#### 4. Custom Command

Execute custom commands via JSON.

**Example**:
```json
{
  "type": "register",
  "register": 1044,
  "value": 0
}
```

### Conditional Execution

Execute schedules only when certain conditions are met.

**Example**: Only charge battery if SOC < 30%
- Condition Type: `register`
- Register: `1109 - Load First Discharge Stop SOC (Read)`
- Operator: `<`
- Value: `30`

**Available Operators**: `<`, `>`, `=`, `<=`, `>=`

### Schedule Options

- **Enabled**: Whether schedule is active
- **Pushover Notifications on Failure**: Send alert when schedule fails
- **Inverter Serial**: Override default serial number (optional)

## Usage Examples

### Example 1: Daily Battery Charge Schedule

**Goal**: Switch to Battery First mode every day at 6:00 AM

1. Click **New Schedule**
2. Name: "Morning Battery Charge"
3. Schedule Type: `Daily`
4. Time: `06:00`
5. Command Type: `template`
6. Template: `Battery First Mode`
7. Enable: ✓
8. Click **Save Schedule**

### Example 2: Weekly Load First Schedule

**Goal**: Enable Load First mode Monday-Friday at 9:00 AM

1. Click **New Schedule**
2. Name: "Weekday Load First"
3. Schedule Type: `Weekly`
4. Days: Mon, Tue, Wed, Thu, Fri
5. Time: `09:00`
6. Command Type: `register`
7. Register: `1044 - Work Mode`
8. Value: `0` (Load First)
9. Click **Save Schedule**

### Example 3: Grid First Time Schedule with Multi-Register

**Goal**: Set Grid First Schedule 1 to 9:00-17:00 daily

1. Click **New Schedule**
2. Name: "Grid First Schedule 1 (9-5)"
3. Schedule Type: `Daily`
4. Time: `00:01` (run early morning to set for the day)
5. Command Type: `multiregister`
6. Start Register: `1080`
7. End Register: `1082`
8. Value: `900-1700-1`
9. Click **Save Schedule**

### Example 4: Conditional SOC-Based Charging

**Goal**: Switch to Battery First only if SOC < 20%

1. Click **New Schedule**
2. Name: "Low SOC Emergency Charge"
3. Schedule Type: `Daily`
4. Time: `08:00`
5. Command Type: `template`
6. Template: `Battery First Mode`
7. Condition Type: `register`
8. Condition Register: `1109 - Load First Discharge Stop SOC (Read)`
9. Operator: `<`
10. Value: `20`
11. Click **Save Schedule**

## Managing Schedules

### Viewing Schedules

The **Schedules** tab shows all configured schedules with:
- Name and description
- Schedule type (daily/weekly/once)
- Execution time
- Command type
- Status (enabled/disabled)
- Last execution time
- Success rate

### Executing Schedules Manually

Click the **Play** button (▶) next to any schedule to execute it immediately for testing.

### Editing Schedules

Click the **Edit** button (✎) to modify an existing schedule. Changes take effect immediately.

### Deleting Schedules

Click the **Delete** button (🗑) to remove a schedule. This action cannot be undone.

## Monitoring

### Dashboard

The **Dashboard** tab provides:
- **Statistics**: Total schedules, active schedules, total executions, success rate
- **Upcoming Executions**: Next scheduled tasks
- **Recent Failures**: Last failed executions with error details

### Execution Logs

The **Execution Logs** tab shows detailed history:
- Schedule name
- Execution timestamp
- Success/failure status
- Retry attempts
- Condition evaluation
- Error messages (if failed)
- Response from inverter (if successful)

### System Logs

View real-time service logs:

```bash
# Follow logs in real-time
journalctl -u grott-scheduler -f

# View last 100 lines
journalctl -u grott-scheduler -n 100

# View logs for specific date
journalctl -u grott-scheduler --since "2024-11-20 00:00:00"
```

## Service Management

### Check Service Status

```bash
systemctl status grott-scheduler
```

### Start/Stop Service

```bash
# Start
systemctl start grott-scheduler

# Stop
systemctl stop grott-scheduler

# Restart
systemctl restart grott-scheduler
```

### Enable/Disable Auto-Start

```bash
# Enable (start on boot)
systemctl enable grott-scheduler

# Disable
systemctl disable grott-scheduler
```

### View Logs

```bash
# Real-time logs
journalctl -u grott-scheduler -f

# Last 50 entries
journalctl -u grott-scheduler -n 50

# Logs since boot
journalctl -u grott-scheduler -b
```

## API Reference

The scheduler provides a RESTful API on port 5783.

### Endpoints

#### Health Check
```
GET /api/health
```

#### Configuration
```
GET /api/config
PUT /api/config
```

#### Registers
```
GET /api/registers
```

#### Templates
```
GET /api/templates
```

#### Schedules
```
GET /api/schedules
POST /api/schedules
GET /api/schedules/{id}
PUT /api/schedules/{id}
DELETE /api/schedules/{id}
POST /api/schedules/{id}/execute
```

#### Execution Logs
```
GET /api/logs?limit=100&schedule_id={id}
```

#### Statistics
```
GET /api/stats
```

### Example API Calls

```bash
# Get all schedules
curl http://<serverip>:5783/api/schedules

# Create new schedule
curl -X POST http://<serverip>:5783/api/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Schedule",
    "schedule_type": "daily",
    "time": "10:00",
    "command_type": "register",
    "register_number": 1044,
    "register_value": 0,
    "enabled": true
  }'

# Execute schedule immediately
curl -X POST http://<serverip>:5783/api/schedules/1/execute

# Get execution logs
curl http://<serverip>:5783/api/logs?limit=50
```

## Integration with Node-RED

### Serving the Web Interface

**Method 1: Static File Serving**

1. Copy `frontend/index.html` to Node-RED static files directory
2. Access via `http://your-nodered:1880/index.html`

**Method 2: HTTP In Node**

1. Create HTTP In node with `/scheduler` path
2. Add Template node with file contents
3. Add HTTP Response node
4. Access via `http://your-nodered:1880/scheduler`

**Method 3: Dashboard Template**

1. Add UI Template node to Node-RED dashboard
2. Paste HTML content
3. Access via Node-RED dashboard

### API Integration

Use HTTP Request nodes to interact with the API:

```javascript
// Example: Get all schedules
msg.url = "http://<serverip>:5783/api/schedules";
return msg;
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
systemctl status grott-scheduler

# View detailed logs
journalctl -u grott-scheduler -n 100

# Check if port 5783 is available
netstat -tuln | grep 5783
```

### Database Errors

```bash
# Check database exists
ls -lh /opt/grott-scheduler/database/scheduler.db

# Reinitialize database (WARNING: loses data)
cd /opt/grott-scheduler/database
rm scheduler.db
sqlite3 scheduler.db < schema.sql
```

### Schedules Not Executing

1. Check if service is running: `systemctl status grott-scheduler`
2. Verify schedule is enabled in web interface
3. Check execution logs for errors
4. Verify time/date settings on server
5. Check Grott proxy is accessible at <grottserver>:5782

### Commands Failing

1. Verify Grott proxy is running: `curl http://<grottserver>:5782/inverter?command=register&inverter=NTCRBLR00Y&register=1044`
2. Check inverter serial number in configuration
3. Review execution logs for specific error messages
4. Test command manually via curl
5. Increase retry attempts and delay

### Pushover Notifications Not Working

1. Verify User Key and API Token in configuration
2. Test credentials at pushover.net
3. Check execution logs for notification errors
4. Ensure server has internet access

## Database Backup

### Manual Backup

```bash
# Create backup
cp /opt/grott-scheduler/database/scheduler.db \
   /opt/grott-scheduler/database/scheduler.db.backup.$(date +%Y%m%d)

# Restore from backup
cp /opt/grott-scheduler/database/scheduler.db.backup.20241120 \
   /opt/grott-scheduler/database/scheduler.db
systemctl restart grott-scheduler
```

### Automated Backup (Cron)

Add to crontab:

```bash
# Backup database daily at 2 AM
0 2 * * * cp /opt/grott-scheduler/database/scheduler.db /opt/grott-scheduler/database/scheduler.db.backup.$(date +\%Y\%m\%d)

# Delete backups older than 30 days
0 3 * * * find /opt/grott-scheduler/database -name "scheduler.db.backup.*" -mtime +30 -delete
```

## Updating

```bash
# Stop service
systemctl stop grott-scheduler

# Pull latest code or make changes
cd /opt/grott-scheduler
# ... make your updates ...

# Reinstall dependencies if needed
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Restart service
systemctl start grott-scheduler
```

## Uninstallation

```bash
# Stop and disable service
systemctl stop grott-scheduler
systemctl disable grott-scheduler

# Remove service file
rm /etc/systemd/system/grott-scheduler.service
systemctl daemon-reload

# Remove installation (optional)
rm -rf /opt/grott-scheduler
```

## Support & Documentation

- **Grott Documentation**: https://github.com/johanmeijer/grott
- **Register Reference**: `/opt/grott/documentatie/registers.md`
- **Example Layouts**: `/opt/grott/examples/Record Layout/`

## Known Register Values

### Work Mode (Register 1044)
- `0` = Load First
- `1` = Battery First
- `2` = Grid First

### Grid First Schedules
- Registers 1080-1082: Schedule 1
- Registers 1083-1085: Schedule 2
- Registers 1086-1088: Schedule 3
- Registers 1089-1091: Schedule 4 (Battery First only)

Format: StartTime (HHMM), EndTime (HHMM), Enable (0/1)

### Load First Discharge SOC
- Register 608: Write-only
- Register 1109: Read-only
- Value: 0-100 (percentage)

## License

This project is part of the Grott ecosystem. See Grott license for details.

## Version

Grott Scheduler v1.0.0 (November 2024)
