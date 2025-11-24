#!/usr/bin/env python3
"""
Database migration script for schedule chains feature
Adds parent-child relationship support to existing databases
"""

import sqlite3
import os
import sys

# Get database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'scheduler.db')

def migrate_database():
    """Apply migration to add schedule chain support"""
    
    if not os.path.exists(DATABASE_PATH):
        print(f"Error: Database not found at {DATABASE_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(DATABASE_PATH)
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    print("Starting database migration for schedule chains...")
    
    try:
        # Check if migration is needed
        cursor.execute("PRAGMA table_info(schedules)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'parent_schedule_id' in columns:
            print("Migration already applied. Skipping.")
            return
        
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Add new columns to schedules table
        print("Adding columns to schedules table...")
        cursor.execute("ALTER TABLE schedules ADD COLUMN parent_schedule_id INTEGER DEFAULT NULL")
        cursor.execute("ALTER TABLE schedules ADD COLUMN execution_order INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE schedules ADD COLUMN continue_on_parent_failure BOOLEAN DEFAULT 0")
        
        # Add new columns to execution_logs table
        print("Adding columns to execution_logs table...")
        cursor.execute("ALTER TABLE execution_logs ADD COLUMN parent_execution_id INTEGER DEFAULT NULL")
        cursor.execute("ALTER TABLE execution_logs ADD COLUMN execution_order INTEGER DEFAULT 0")
        
        # Create new indexes
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedules_parent ON schedules(parent_schedule_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_logs_parent ON execution_logs(parent_execution_id)")
        
        # Commit transaction
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {str(e)}")
        sys.exit(1)
        
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()
