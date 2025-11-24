# Schedule Chains Feature - Implementation Summary

## What Was Implemented

The Grott Scheduler now supports **parent-child schedule chains**, allowing you to create complex, multi-step schedules where multiple register changes execute sequentially at a single scheduled time.

## Key Changes

### 1. Database Schema Updates
- Added `parent_schedule_id`, `execution_order`, and `continue_on_parent_failure` columns to `schedules` table
- Added `parent_execution_id` and `execution_order` columns to `execution_logs` table
- Created indexes for performance
- Migration script available at `/opt/grott-scheduler/database/migrate.py`

### 2. Backend Changes (`backend/app.py`)
- Enhanced `execute_schedule()` to recursively execute child schedules
- Modified scheduler initialization to only load root schedules (children are triggered by parents)
- Updated API endpoints to support parent-child fields:
  - `POST /api/schedules` - accepts parent_schedule_id, execution_order, continue_on_parent_failure
  - `PUT /api/schedules/<id>` - same as above
  - `GET /api/schedules` - returns child_count and orders by hierarchy
  - New: `GET /api/schedules/<id>/children` - returns all children of a schedule

### 3. Frontend Changes (`frontend/index.html`)
- Added "Schedule Chain" section to the schedule form with:
  - Parent Schedule dropdown (populated with root schedules only)
  - Execution Order input field
  - Continue on Parent Failure checkbox
- Visual indicators in schedule list:
  - Root schedules with children show badge with count
  - Child schedules are indented with arrow indicator
  - Color-coded border for child schedules
- Updated JavaScript to handle parent-child relationships

### 4. Documentation
- Comprehensive guide: `/opt/grott-scheduler/docs/SCHEDULE_CHAINS.md`
- Test script: `/opt/grott-scheduler/test_schedule_chains.py`

## How It Works

1. **Create a root schedule** - This is your parent that will trigger at the scheduled time
2. **Create child schedules** - These execute after the parent completes
3. **Set execution order** - Children execute in order (0, 1, 2, etc.)
4. **Configure failure handling** - Choose whether children run if parent fails

### Execution Flow

```
[Scheduled Time] → Parent Executes
                   ↓ (if successful, or if continue_on_failure=true)
                   Child Order 0 Executes
                   ↓ (if successful, or if continue_on_failure=true)
                   Child Order 1 Executes
                   ↓
                   ... and so on
```

## Example Use Case

**Scenario:** Every morning at 6 AM, switch to Load First mode AND set SOC to 100%

1. Create parent schedule:
   - Name: "Morning - Switch to Load First"
   - Register 1044 = 0 (Load First mode)
   - Time: 06:00

2. Create child schedule:
   - Name: "Morning - Set SOC 100%"
   - Register 608 = 100 (SOC)
   - Parent: "Morning - Switch to Load First"
   - Order: 0

Now both register changes happen sequentially at 6 AM!

## Files Modified

- `/opt/grott-scheduler/database/schema.sql` - Updated schema
- `/opt/grott-scheduler/database/migrate.py` - NEW migration script
- `/opt/grott-scheduler/database/migration_schedule_chains.sql` - NEW migration SQL
- `/opt/grott-scheduler/backend/app.py` - Enhanced execution logic
- `/opt/grott-scheduler/frontend/index.html` - Updated UI
- `/opt/grott-scheduler/docs/SCHEDULE_CHAINS.md` - NEW documentation
- `/opt/grott-scheduler/test_schedule_chains.py` - NEW test script

## Migration Applied

✅ Database migration has been successfully applied to your existing database
✅ Service has been restarted and is running properly

## Testing

To test the new feature:

1. **Using the Web UI:**
   - Open http://172.17.254.10:5783/frontend/index.html
   - Create a schedule (this will be the parent)
   - Create another schedule and select the first one as "Parent Schedule"
   - Click "Execute Now" on the parent to test the chain

2. **Using the Test Script:**
   ```bash
   cd /opt/grott-scheduler
   python3 test_schedule_chains.py
   ```
   This will create a sample chain, optionally execute it, and clean up.

## Backward Compatibility

✅ **Fully backward compatible** - existing schedules continue to work exactly as before
- All existing schedules are treated as root schedules (parent_schedule_id = NULL)
- No changes required to existing schedules
- New fields default to appropriate values

## Next Steps

1. **Test with your schedules** - Try creating a simple chain
2. **Monitor execution logs** - Verify chains execute in correct order
3. **Check failure handling** - Test what happens when parent fails
4. **Review documentation** - See `/opt/grott-scheduler/docs/SCHEDULE_CHAINS.md` for full details

## Support

If you encounter any issues:
1. Check `/opt/grott-scheduler/logs/scheduler.log` for errors
2. Verify database migration completed: `ls -la /opt/grott-scheduler/database/scheduler.db`
3. Check service status: `systemctl status grott-scheduler.service`
4. Review the documentation for troubleshooting tips
