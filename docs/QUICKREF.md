# Grott Scheduler - Quick Reference

## 📋 Installation

```bash
cd /opt/grott-scheduler
sudo bash install.sh
```

## 🌐 Access

- **Web UI**: `http://<serverip>:5783/frontend/index.html`
- **API**: `http://<serverip>:5783/api`

## 🎛️ Service Commands

```bash
# Status
systemctl status grott-scheduler

# Logs (live)
journalctl -u grott-scheduler -f

# Restart
systemctl restart grott-scheduler

# Stop/Start
systemctl stop grott-scheduler
systemctl start grott-scheduler
```

## 📝 Common Schedules

### 1. Battery First Mode (Daily 6 AM)
- **Schedule Type**: Daily
- **Time**: 06:00
- **Command**: Template → "Battery First Mode"

### 2. Load First Mode (Daily 9 AM)
- **Schedule Type**: Daily
- **Time**: 09:00
- **Command**: Register
  - Register: 1044 (Work Mode)
  - Value: 0

### 3. Grid First Schedule (9 AM - 5 PM)
- **Schedule Type**: Daily
- **Time**: 00:01 (early morning)
- **Command**: Multi-register
  - Start: 1080
  - End: 1082
  - Value: `900-1700-1`

### 4. Set Discharge SOC to 50%
- **Schedule Type**: Daily
- **Time**: Any
- **Command**: Register
  - Register: 608 (Load First Discharge Stop SOC)
  - Value: 50

### 5. Conditional SOC Charge
- **Schedule Type**: Daily
- **Time**: 08:00
- **Command**: Template → "Battery First Mode"
- **Condition**: 
  - Register: 1109 (SOC Read)
  - Operator: <
  - Value: 20

## 🔢 Important Registers

| Register | Name | Read/Write | Values |
|----------|------|------------|--------|
| 608 | Load First Discharge SOC | Write | 0-100 |
| 1044 | Work Mode | Read/Write | 0=Load, 1=Battery, 2=Grid |
| 1080-1082 | Grid First Schedule 1 | Read/Write | Time format |
| 1083-1085 | Grid First Schedule 2 | Read/Write | Time format |
| 1086-1088 | Grid First Schedule 3 | Read/Write | Time format |
| 1109 | Load First Discharge SOC | Read | 0-100 |

## 🕒 Multi-Register Time Format

For Grid First schedules (registers 1080-1082, etc.):

**Format**: `StartTime-EndTime-Enable`

**Examples**:
- `900-1700-1` = 9:00 AM to 5:00 PM, Enabled
- `600-1200-1` = 6:00 AM to 12:00 PM, Enabled
- `1300-2100-0` = 1:00 PM to 9:00 PM, Disabled

**Time Format**: HHMM (24-hour)
- `600` = 6:00 AM
- `900` = 9:00 AM
- `1200` = 12:00 PM
- `1700` = 5:00 PM
- `2100` = 9:00 PM

## 🔔 Pushover Setup

1. Get User Key from https://pushover.net/
2. Create app, get API Token
3. In web interface → Configuration:
   - `pushover_user_key`: Your user key
   - `pushover_api_token`: Your API token
4. Toggle "Pushover Notifications" when creating schedules

## 🧪 Testing

### Test Schedule Immediately
Click the **Play** button (▶) next to any schedule

### Test Grott Connection
```bash
curl "http://<grottserver>:5782/inverter?command=register&inverter=NTCRBLR00Y&register=1044"
```

### Test API
```bash
# Get schedules
curl http://<serverip>:5783/api/schedules

# Get stats
curl http://<serverip>:5783/api/stats

# Get logs
curl http://<serverip>:5783/api/logs?limit=10
```

## 🚨 Troubleshooting

### Service Not Starting
```bash
journalctl -u grott-scheduler -n 100
systemctl status grott-scheduler
```

### Schedules Not Executing
1. Check service: `systemctl status grott-scheduler`
2. Check logs: `journalctl -u grott-scheduler -f`
3. Verify schedule is enabled in web UI
4. Test Grott connection (see above)

### Commands Failing
1. Check execution logs in web UI
2. Verify inverter serial in Configuration
3. Test Grott manually
4. Increase retry attempts in Configuration

## 📁 File Locations

- **Database**: `/opt/grott-scheduler/database/scheduler.db`
- **Logs**: `/opt/grott-scheduler/logs/scheduler.log`
- **Config**: Database (Configuration tab in web UI)
- **Service**: `/etc/systemd/system/grott-scheduler.service`

## 🔄 Backup Database

```bash
# Create backup
cp /opt/grott-scheduler/database/scheduler.db \
   /opt/grott-scheduler/database/scheduler.db.backup.$(date +%Y%m%d)

# Restore
cp /opt/grott-scheduler/database/scheduler.db.backup.20241120 \
   /opt/grott-scheduler/database/scheduler.db
systemctl restart grott-scheduler
```

## 🔌 Node-RED Integration

### Serve Web UI
1. Create HTTP In node: `/scheduler`
2. Add File In node: `/opt/grott-scheduler/frontend/index.html`
3. Add HTTP Response node
4. Access: `http://your-nodered:1880/scheduler`

### API Calls from Node-RED
```javascript
// Get all schedules
msg.url = "http://<serverip>:5783/api/schedules";
msg.method = "GET";
return msg;
```

## 📚 Full Documentation

See `/opt/grott-scheduler/docs/INSTALL.md` for complete guide.

## ⚡ Quick Configuration

Default settings (change in Configuration tab):
- **grott_host**: <grottserver>
- **grott_port**: 5782
- **inverter_serial**: NTCRBLR00Y
- **max_retries**: 5
- **retry_delay**: 10 (seconds)

## 🎯 Best Practices

1. **Test First**: Use "Execute Now" button before enabling schedules
2. **Enable Pushover**: Get notified of failures
3. **Check Logs**: Review execution logs regularly
4. **Backup Database**: Before making major changes
5. **Use Templates**: For common operations
6. **Conditional Execution**: For SOC-dependent actions
7. **Monitor Success Rate**: On schedules dashboard

## 📞 Support

- **Full Docs**: `/opt/grott-scheduler/docs/INSTALL.md`
- **Grott Docs**: https://github.com/johanmeijer/grott
- **Registers**: `/opt/grott/documentatie/registers.md`
