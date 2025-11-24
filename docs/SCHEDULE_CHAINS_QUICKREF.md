# Schedule Chains - Quick Reference

## Creating a Chain

### Step 1: Create Parent Schedule
```
Schedule Form:
├── Name: "Morning Setup"
├── Time: 06:00
├── Command: Register 1044 = 0
└── Parent Schedule: None (Root Schedule)  ← Leave as "None"
```

### Step 2: Create Child Schedule(s)
```
Schedule Form:
├── Name: "Morning SOC"
├── Time: 06:00
├── Command: Register 608 = 100
└── Schedule Chain Section:
    ├── Parent Schedule: "Morning Setup"  ← Select parent
    ├── Execution Order: 0                ← Lower = first
    └── Continue on Failure: ☐            ← Check if should run even when parent fails
```

## Execution Order Examples

### Simple Chain (2 steps)
```
Parent (06:00)
  └─ Child Order 0
```

### Complex Chain (4 steps)
```
Parent (06:00)
  ├─ Child Order 0  (executes first)
  ├─ Child Order 1  (executes second)
  └─ Child Order 2  (executes third)
```

## Visual Indicators

### In Schedule List
- **Root with children:** `Schedule Name 🔀 2` (badge shows child count)
- **Child schedule:** `↪ Schedule Name (child of: Parent Name)` (indented with arrow)

### Color Coding
- Green background = Enabled
- Red background = Disabled
- Left gray border = Child schedule

## API Quick Reference

### Get all schedules (with hierarchy)
```bash
curl http://localhost:5783/api/schedules
```

### Get children of a schedule
```bash
curl http://localhost:5783/api/schedules/1/children
```

### Create schedule with parent
```bash
curl -X POST http://localhost:5783/api/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Child Schedule",
    "schedule_type": "daily",
    "time": "06:00",
    "command_type": "register",
    "register_number": 608,
    "register_value": "100",
    "parent_schedule_id": 1,
    "execution_order": 0,
    "continue_on_parent_failure": false
  }'
```

## Common Patterns

### Pattern 1: Mode Switch + Configuration
```
Parent: Set Priority Mode
  └─ Child: Configure mode-specific settings
```

### Pattern 2: Sequential Time Slots
```
Parent: Enable Schedule Slot 1
  ├─ Child 0: Set Start Time
  ├─ Child 1: Set Stop Time
  └─ Child 2: Enable the slot
```

### Pattern 3: Multi-Register Time Schedule
```
Parent: Set Grid First Time 1 Start (hex)
  ├─ Child 0: Set Grid First Time 1 Stop (hex)
  └─ Child 1: Enable Grid First Time 1
```

## Failure Handling

### Default Behavior (continue_on_failure = false)
```
Parent ✓ → Child executes
Parent ✗ → Child SKIPPED (logged as "parent failed")
```

### With Continue on Failure (continue_on_failure = true)
```
Parent ✓ → Child executes
Parent ✗ → Child executes anyway
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Child not executing | Check parent succeeded, or enable "Continue on Failure" |
| Wrong execution order | Verify execution_order values (0, 1, 2...) |
| Can't select parent | Only root schedules can be parents |
| Schedule not in dropdown | Refresh page to reload schedule list |

## Testing Commands

### Test execution (won't send to inverter if Grott server is down)
```bash
# Create test chain
python3 /opt/grott-scheduler/test_schedule_chains.py

# Check logs
tail -f /opt/grott-scheduler/logs/scheduler.log

# View recent executions
curl http://localhost:5783/api/logs?limit=10 | python3 -m json.tool
```

## Best Practices

✅ **DO:**
- Use descriptive names indicating parent-child relationship
- Test chains manually before scheduling
- Keep chains short (2-4 steps ideal)
- Monitor execution logs after deployment

❌ **DON'T:**
- Create circular dependencies (A→B→A)
- Make chains too long (>5 steps)
- Forget to set execution order
- Rely on timing between steps (they execute immediately)

## Migration Status

✅ Database migrated: `/opt/grott-scheduler/database/migrate.py`
✅ Service restarted: `systemctl status grott-scheduler.service`
✅ Web UI updated: New "Schedule Chain" section in form
✅ Backward compatible: Existing schedules work as before

## Support Files

- Documentation: `/opt/grott-scheduler/docs/SCHEDULE_CHAINS.md`
- Test Script: `/opt/grott-scheduler/test_schedule_chains.py`
- Migration: `/opt/grott-scheduler/database/migrate.py`
- Summary: `/opt/grott-scheduler/SCHEDULE_CHAINS_SUMMARY.md`
