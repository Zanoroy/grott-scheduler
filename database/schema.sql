-- Grott Scheduler Database Schema
-- SQLite3 Database

-- Configuration table
CREATE TABLE IF NOT EXISTS config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default configuration
INSERT OR IGNORE INTO config (key, value, description) VALUES
    ('grott_host', '<grottserver>', 'Grott server IP address'),
    ('grott_port', '5782', 'Grott server port'),
    ('inverter_serial', 'NTCRBLR00Y', 'Default inverter serial number'),
    ('pushover_user_key', '', 'Pushover user key for notifications'),
    ('pushover_api_token', '', 'Pushover API token'),
    ('max_retries', '5', 'Maximum retry attempts for failed commands'),
    ('retry_delay', '10', 'Delay in seconds between retries');

-- Schedules table
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    schedule_type TEXT NOT NULL, -- 'daily', 'weekly', 'once', 'conditional'
    time TEXT NOT NULL, -- HH:MM format
    days_of_week TEXT, -- JSON array for weekly: [0,1,2,3,4,5,6] (0=Monday)
    specific_date TEXT, -- YYYY-MM-DD for one-time schedules
    command_type TEXT NOT NULL, -- 'register', 'multiregister', 'template', 'custom'
    register_number INTEGER,
    register_name TEXT,
    register_value TEXT,
    multiregister_start INTEGER,
    multiregister_end INTEGER,
    multiregister_value TEXT,
    template_name TEXT,
    custom_command TEXT,
    condition_type TEXT, -- 'none', 'soc', 'register_value'
    condition_register INTEGER,
    condition_operator TEXT, -- '<', '>', '=', '<=', '>='
    condition_value TEXT,
    enabled BOOLEAN DEFAULT 1,
    pushover_enabled BOOLEAN DEFAULT 1,
    inverter_serial TEXT,
    parent_schedule_id INTEGER DEFAULT NULL,
    execution_order INTEGER DEFAULT 0,
    continue_on_parent_failure BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_executed_at TIMESTAMP,
    next_execution_at TIMESTAMP,
    FOREIGN KEY (parent_schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
);

-- Execution logs table
CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER,
    schedule_name TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    command TEXT,
    success BOOLEAN,
    attempts INTEGER DEFAULT 1,
    response TEXT,
    error_message TEXT,
    condition_met BOOLEAN,
    condition_details TEXT,
    parent_execution_id INTEGER DEFAULT NULL,
    execution_order INTEGER DEFAULT 0,
    FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE SET NULL,
    FOREIGN KEY (parent_execution_id) REFERENCES execution_logs(id) ON DELETE SET NULL
);

-- Templates table  
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    command_type TEXT NOT NULL,
    command_data TEXT NOT NULL, -- JSON containing command details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default templates
INSERT OR IGNORE INTO templates (name, description, command_type, command_data) VALUES
    ('Set Load First + SOC 100%', 'Set priority to Load First and discharge stop SOC to 100%', 'multi_command', 
     '[{"type":"register","register":1044,"value":0},{"type":"register","register":608,"value":100}]'),
    ('Set Battery First', 'Set priority mode to Battery First', 'register',
     '{"register":1044,"value":1}'),
    ('Set Grid First', 'Set priority mode to Grid First', 'register',
     '{"register":1044,"value":2}'),
    ('Disable All Battery Schedules', 'Disable battery schedule slots 1-3', 'multi_command',
     '[{"type":"register","register":1102,"value":0},{"type":"register","register":1105,"value":0},{"type":"register","register":1108,"value":0}]');

-- Register groups table
CREATE TABLE IF NOT EXISTS register_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- Insert register groups
INSERT OR IGNORE INTO register_groups (name) VALUES
    ('Ungrouped'),
    ('Grid First'),
    ('Grid First 1'),
    ('Battery First'),
    ('Battery First 1'),
    ('Load First'),
    ('Time'),
    ('Export Limit');

-- Registers reference table
CREATE TABLE IF NOT EXISTS registers (
    register_number INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    write_only BOOLEAN DEFAULT 0,
    read_register INTEGER, -- For write-only registers, which register to read
    value_type TEXT, -- 'decimal', 'hex', 'time', 'boolean'
    type INTEGER DEFAULT 0, -- 0=hex, 1=dec - tells writer if value should be converted to hex before writing
    min_value INTEGER,
    max_value INTEGER,
    category TEXT, -- 'priority', 'schedule', 'battery', 'grid', 'other'
    group_id INTEGER,
    FOREIGN KEY (group_id) REFERENCES register_groups(id)
);

-- Insert known registers from grott with group assignments
INSERT OR IGNORE INTO registers (register_number, name, description, write_only, read_register, value_type, type, min_value, max_value, category, group_id) VALUES
    (608, 'Load First Discharge Stop SOC', 'Load First mode discharge stop SOC (write-only)', 1, 1109, 'decimal', 1, 0, 100, 'battery', 6),
    (1044, 'Priority Mode', '0=Load First, 1=Battery First, 2=Grid First', 0, NULL, 'decimal', 1, 0, 2, 'priority', 1),
    -- Grid First group (1070-1088)
    (1070, 'Grid First Discharge Power Rate', 'Discharge power rate when Grid First', 0, NULL, 'decimal', 1, 0, 100, 'grid', 2),
    (1071, 'Grid First Stop SOC', 'Stop discharge SOC when Grid First', 0, NULL, 'decimal', 1, 0, 100, 'grid', 2),
    (1080, 'Grid First Start Time 1', 'Grid First schedule 1 start time (HH:MM in hex)', 0, NULL, 'time', 0, 0, 2359, 'schedule', 2),
    (1081, 'Grid First Stop Time 1', 'Grid First schedule 1 stop time (HH:MM in hex)', 0, NULL, 'time', 0, 0, 2359, 'schedule', 2),
    (1082, 'Grid First Enable 1', 'Grid First schedule 1 enable (0=off, 1=on)', 0, NULL, 'boolean', 1, 0, 1, 'schedule', 2),
    (1083, 'Grid First Start Time 2', 'Grid First schedule 2 start time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 2),
    (1084, 'Grid First Stop Time 2', 'Grid First schedule 2 stop time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 2),
    (1085, 'Grid First Enable 2', 'Grid First schedule 2 enable', 0, NULL, 'boolean', 1, 0, 1, 'schedule', 2),
    (1086, 'Grid First Start Time 3', 'Grid First schedule 3 start time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 2),
    (1087, 'Grid First Stop Time 3', 'Grid First schedule 3 stop time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 2),
    (1088, 'Grid First Enable 3', 'Grid First schedule 3 enable', 0, NULL, 'boolean', 1, 0, 1, 'schedule', 2),
    -- Battery First group (1090-1108)
    (1090, 'Battery First Power Rate', 'Charge power rate when Battery First', 0, NULL, 'decimal', 1, 0, 100, 'battery', 4),
    (1091, 'Battery First Stop SOC', 'Stop charge SOC when Battery First (only active in Battery First mode)', 0, NULL, 'decimal', 1, 0, 100, 'battery', 4),
    (1092, 'AC Charge Switch', 'AC charge enable when Battery First', 0, NULL, 'boolean', 1, 0, 1, 'battery', 4),
    (1100, 'Battery First Start Time 1', 'Battery First schedule 1 start time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 4),
    (1101, 'Battery First Stop Time 1', 'Battery First schedule 1 stop time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 4),
    (1102, 'Battery First Enable 1', 'Battery First schedule 1 enable', 0, NULL, 'boolean', 1, 0, 1, 'schedule', 4),
    (1103, 'Battery First Start Time 2', 'Battery First schedule 2 start time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 4),
    (1104, 'Battery First Stop Time 2', 'Battery First schedule 2 stop time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 4),
    (1105, 'Battery First Enable 2', 'Battery First schedule 2 enable', 0, NULL, 'boolean', 1, 0, 1, 'schedule', 4),
    (1106, 'Battery First Start Time 3', 'Battery First schedule 3 start time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 4),
    (1107, 'Battery First Stop Time 3', 'Battery First schedule 3 stop time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 4),
    (1108, 'Battery First Enable 3', 'Battery First schedule 3 enable', 0, NULL, 'boolean', 1, 0, 1, 'schedule', 4),
    -- Load First group (1109-1118)
    (1109, 'Load First Discharge Stop SOC (Read)', 'Read-only register for Load First discharge stop SOC', 0, NULL, 'decimal', 1, 0, 100, 'battery', 6),
    (1110, 'Load First Start Time 1', 'Load First schedule 1 start time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 6),
    (1111, 'Load First Stop Time 1', 'Load First schedule 1 stop time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 6),
    (1112, 'Load First Enable 1', 'Load First schedule 1 enable', 0, NULL, 'boolean', 1, 0, 1, 'schedule', 6),
    (1113, 'Load First Start Time 2', 'Load First schedule 2 start time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 6),
    (1114, 'Load First Stop Time 2', 'Load First schedule 2 stop time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 6),
    (1115, 'Load First Enable 2', 'Load First schedule 2 enable', 0, NULL, 'boolean', 1, 0, 1, 'schedule', 6),
    (1116, 'Load First Start Time 3', 'Load First schedule 3 start time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 6),
    (1117, 'Load First Stop Time 3', 'Load First schedule 3 stop time', 0, NULL, 'time', 0, 0, 2359, 'schedule', 6),
    (1118, 'Load First Enable 3', 'Load First schedule 3 enable', 0, NULL, 'boolean', 1, 0, 1, 'schedule', 6),
    -- Export Limit group (122-123)
    (122, 'Export Limit Enable', 'Export limit enable/disable', 0, NULL, 'boolean', 1, 0, 1, 'grid', 8),
    (123, 'Export Limit Power', 'Export limit power percentage', 0, NULL, 'decimal', 1, 0, 100, 'grid', 8);

-- Register values cache table (source of truth for register values)
CREATE TABLE IF NOT EXISTS register_values (
    register_number INTEGER PRIMARY KEY,
    current_value INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_read_from_inverter TIMESTAMP,
    FOREIGN KEY (register_number) REFERENCES registers(register_number)
);

-- Initialize register values for all known registers
-- Values are stored as decimals, converted to hex for transmission when type=0
INSERT OR IGNORE INTO register_values (register_number, current_value) VALUES
    -- Grid First (1070-1088)
    (1070, 100), (1071, 10), (1072, 0), (1073, 0), (1074, 0), (1075, 0), (1076, 0), (1077, 0), (1078, 0), (1079, 0),
    (1080, 0), (1081, 0), (1082, 0), (1083, 0), (1084, 0), (1085, 0), (1086, 0), (1087, 0), (1088, 0),
    -- Battery First (1090-1108)
    (1090, 0), (1091, 0), (1092, 0), (1100, 0), (1101, 0), (1102, 0), (1103, 0), (1104, 0), (1105, 0),
    (1106, 0), (1107, 0), (1108, 0),
    -- Load First (1109-1118)
    (1109, 0), (1110, 0), (1111, 0), (1112, 0), (1113, 0), (1114, 0), (1115, 0), (1116, 0), (1117, 0), (1118, 0),
    -- Export Limit (122-123)
    (122, 0), (123, 0),
    -- Other
    (608, 0), (1044, 0);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON schedules(enabled);
CREATE INDEX IF NOT EXISTS idx_schedules_next_execution ON schedules(next_execution_at);
CREATE INDEX IF NOT EXISTS idx_schedules_parent ON schedules(parent_schedule_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_schedule_id ON execution_logs(schedule_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_executed_at ON execution_logs(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_execution_logs_parent ON execution_logs(parent_execution_id);
CREATE INDEX IF NOT EXISTS idx_register_values_updated ON register_values(last_updated DESC);
