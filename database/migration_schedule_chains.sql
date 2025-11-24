-- Migration: Add parent-child schedule chain support
-- Date: 2025-11-24

-- Add columns to schedules table for chain support
ALTER TABLE schedules ADD COLUMN parent_schedule_id INTEGER DEFAULT NULL;
ALTER TABLE schedules ADD COLUMN execution_order INTEGER DEFAULT 0;
ALTER TABLE schedules ADD COLUMN continue_on_parent_failure BOOLEAN DEFAULT 0;

-- Create schedule_chains table to manage chain metadata
CREATE TABLE IF NOT EXISTS schedule_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    root_schedule_id INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (root_schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
);

-- Create schedule_chain_members table for better chain management
CREATE TABLE IF NOT EXISTS schedule_chain_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chain_id INTEGER NOT NULL,
    schedule_id INTEGER NOT NULL,
    parent_schedule_id INTEGER,
    execution_order INTEGER NOT NULL DEFAULT 0,
    continue_on_parent_failure BOOLEAN DEFAULT 0,
    FOREIGN KEY (chain_id) REFERENCES schedule_chains(id) ON DELETE CASCADE,
    FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
);

-- Add chain execution tracking to execution_logs
ALTER TABLE execution_logs ADD COLUMN chain_id INTEGER DEFAULT NULL;
ALTER TABLE execution_logs ADD COLUMN parent_execution_id INTEGER DEFAULT NULL;
ALTER TABLE execution_logs ADD COLUMN execution_order INTEGER DEFAULT 0;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_schedules_parent ON schedules(parent_schedule_id);
CREATE INDEX IF NOT EXISTS idx_chain_members_chain ON schedule_chain_members(chain_id);
CREATE INDEX IF NOT EXISTS idx_chain_members_schedule ON schedule_chain_members(schedule_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_chain ON execution_logs(chain_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_parent ON execution_logs(parent_execution_id);
