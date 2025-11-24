# Parent-Child Schedule Chains

## Overview

The Grott Scheduler now supports **parent-child schedule chains**, allowing multiple register changes to execute sequentially at a single scheduled time. This feature enables complex, multi-step operations where child schedules execute one after another, with built-in failure handling.

## Key Features

### 1. Sequential Execution
- **Parent schedule** executes first at the scheduled time
- **Child schedules** execute automatically after their parent completes
- Children are executed in order based on their `execution_order` value (0, 1, 2, etc.)

### 2. Failure Handling
- By default, if a parent fails, its children **will not execute**
- You can override this with the **"Continue on Parent Failure"** checkbox
- Each child schedule has its own failure handling setting

### 3. Hierarchical Organization
- Only root (parent) schedules appear in the APScheduler
- Child schedules are automatically triggered by their parents
- The UI clearly shows parent-child relationships

### 4. Automatic Cascade Delete
- **Deleting a parent schedule automatically deletes all its children**
- The UI warns you before deletion showing the number of children that will be deleted
- Deleting a child schedule does NOT affect the parent
- This prevents orphaned child schedules

## Database Changes

### New Columns in `schedules` table:
- `parent_schedule_id` - References the parent schedule (NULL for root schedules)
- `execution_order` - Determines the order of execution among siblings (0, 1, 2...)
- `continue_on_parent_failure` - Boolean flag to execute even if parent fails

### New Columns in `execution_logs` table:
- `parent_execution_id` - Links to the parent execution log entry
- `execution_order` - Records the execution order for tracking

## How to Use

### Creating a Schedule Chain

1. **Create the Parent Schedule** (Root)
   - Set up your first register change as normal
   - Leave "Parent Schedule" set to "None (Root Schedule)"
   - This schedule will trigger at the configured time

2. **Create Child Schedules**
   - Create a new schedule
   - In the "Schedule Chain" section, select the parent schedule
   - Set the execution order (0 executes first, then 1, 2, etc.)
   - Optionally check "Continue on Parent Failure" if this should run even when parent fails
   - **Important:** The time settings are inherited from the parent, but you still need to provide them

3. **Add Multiple Children**
   - Create as many child schedules as needed
   - Each can have different execution orders
   - Different failure handling per child

### Example Use Case

**Scenario:** Switch to Load First mode and set SOC to 100% at 6:00 AM

**Parent Schedule:**
- Name: "Morning - Switch to Load First"
- Time: 06:00
- Command: Single Register Write
- Register: 1044 (Priority Mode)
- Value: 0 (Load First)
- Parent: None (Root Schedule)

**Child Schedule 1:**
- Name: "Morning - Set SOC to 100%"
- Time: 06:00 (inherited but required)
- Command: Single Register Write  
- Register: 608 (Load First Discharge Stop SOC)
- Value: 100
- Parent: "Morning - Switch to Load First"
- Execution Order: 0
- Continue on Failure: Unchecked (only runs if parent succeeds)

### Execution Flow

```
06:00:00 - Parent executes (Register 1044 = 0)
   ↓ (success)
06:00:XX - Child Order 0 executes (Register 608 = 100)
   ↓ (success)
06:00:YY - Child Order 1 executes (if exists)
   ↓
...and so on
```

If the parent fails and "Continue on Parent Failure" is unchecked, the child will be logged as skipped.

## API Changes

### New Endpoint
- `GET /api/schedules/<id>/children` - Returns all child schedules for a given parent

### Updated Endpoints
- `POST /api/schedules` - Now accepts `parent_schedule_id`, `execution_order`, `continue_on_parent_failure`
- `PUT /api/schedules/<id>` - Same as above
- `GET /api/schedules` - Now includes `child_count` and orders by parent relationship

### Manual Execution
When you manually execute a schedule using "Execute Now", it will:
1. Execute the selected schedule
2. Automatically execute all its children in order
3. Respect the failure handling rules

## UI Indicators

### Schedules Table
- **Root schedules with children:** Show a badge with child count (e.g., `🔀 2`)
- **Child schedules:** Indented with an arrow (↪) and show their parent's name
- Visual styling: Child schedules have a left border for easy identification

### Schedule Form
- New "Schedule Chain" section with:
  - Parent Schedule dropdown (shows only root schedules)
  - Execution Order field (numeric, 0-999)
  - Continue on Parent Failure checkbox

## Migration

For existing installations, run the migration:

```bash
cd /opt/grott-scheduler/database
python3 migrate.py
```

Then restart the service:

```bash
systemctl restart grott-scheduler.service
```

## Best Practices

1. **Keep chains reasonably short** - Too many steps increase complexity
2. **Use descriptive names** - Clearly indicate parent-child relationships
3. **Test with manual execution** - Use "Execute Now" to test chains before scheduling
4. **Monitor logs** - Check execution logs to verify chain behavior
5. **Consider failure scenarios** - Think about whether children should run if parent fails

## Execution Logs

The execution logs now show:
- Parent-child relationships via `parent_execution_id`
- Execution order for each step
- Whether a schedule was skipped due to parent failure
- Full chain execution history

## Limitations

1. **Single level hierarchy** - Currently supports parent→child, not grandchildren
2. **Time inheritance** - Children must specify time settings even though they inherit from parent
3. **Same inverter** - All schedules in a chain should target the same inverter

## Troubleshooting

### Child schedule not executing
- Check that parent schedule succeeded
- Verify "Continue on Parent Failure" setting if parent failed
- Ensure child schedule is enabled
- Check execution logs for skip reasons

### Execution order wrong
- Verify execution_order values (0, 1, 2...)
- Remember: Lower numbers execute first
- Check for duplicate order values (both will execute, but order is unpredictable)

### Can't select a schedule as parent
- Only root schedules (no parent) can be parents
- You can't make a child schedule a parent of another
- The schedule being edited cannot be its own parent

## Future Enhancements

Potential future improvements:
- Multi-level hierarchy (grandchildren)
- Conditional chains based on parent results
- Parallel execution of children
- Time delays between chain steps
- Visual chain designer
