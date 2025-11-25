#!/usr/bin/env python3
"""
Migration script to add register_groups table and update registers table
Adds group_id and type columns to registers table
"""

import sqlite3
import sys
import os

def migrate():
    db_path = '/opt/grott-scheduler/database/scheduler.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Starting migration...")
        
        # Create register_groups table
        print("Creating register_groups table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS register_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        
        # Insert register groups
        print("Inserting register groups...")
        groups = [
            'Ungrouped',
            'Grid First',
            'Grid First 1',
            'Battery First',
            'Battery First 1',
            'Load First',
            'Time',
            'Export Limit'
        ]
        for group in groups:
            cursor.execute("INSERT OR IGNORE INTO register_groups (name) VALUES (?)", (group,))
        
        # Check if columns exist in registers table
        cursor.execute("PRAGMA table_info(registers)")
        columns = [col[1] for col in cursor.fetchall()]
        
        needs_type = 'type' not in columns
        needs_group_id = 'group_id' not in columns
        
        if needs_type or needs_group_id:
            print("Adding new columns to registers table...")
            
            # Create new table with additional columns
            cursor.execute("""
                CREATE TABLE registers_new (
                    register_number INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    write_only BOOLEAN DEFAULT 0,
                    read_register INTEGER,
                    value_type TEXT,
                    type INTEGER DEFAULT 0,
                    min_value INTEGER,
                    max_value INTEGER,
                    category TEXT,
                    group_id INTEGER,
                    FOREIGN KEY (group_id) REFERENCES register_groups(id)
                )
            """)
            
            # Copy data from old table, setting default values
            cursor.execute("""
                INSERT INTO registers_new 
                (register_number, name, description, write_only, read_register, 
                 value_type, type, min_value, max_value, category, group_id)
                SELECT register_number, name, description, write_only, read_register,
                       value_type, 0, min_value, max_value, category, 1
                FROM registers
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE registers")
            cursor.execute("ALTER TABLE registers_new RENAME TO registers")
            print("Registers table updated")
        
        # Update register groups and types
        print("Updating register group assignments and types...")
        
        # Grid First group (id=2)
        grid_first_regs = list(range(1070, 1089))  # 1070-1088
        for reg in grid_first_regs:
            # Time registers use hex (type=0), others use decimal (type=1)
            reg_type = 0 if reg in [1080, 1081, 1083, 1084, 1086, 1087] else 1
            cursor.execute("UPDATE registers SET group_id = 2, type = ? WHERE register_number = ?", (reg_type, reg))
        
        # Battery First group (id=4)
        battery_first_regs = list(range(1090, 1109))  # 1090-1108
        for reg in battery_first_regs:
            # Time registers use hex (type=0), others use decimal (type=1)
            reg_type = 0 if reg in [1100, 1101, 1103, 1104, 1106, 1107] else 1
            cursor.execute("UPDATE registers SET group_id = 4, type = ? WHERE register_number = ?", (reg_type, reg))
        
        # Load First group (id=6)
        load_first_regs = list(range(1109, 1119))  # 1109-1118
        for reg in load_first_regs:
            # Time registers use hex (type=0), others use decimal (type=1)
            reg_type = 0 if reg in [1110, 1111, 1113, 1114, 1116, 1117] else 1
            cursor.execute("UPDATE registers SET group_id = 6, type = ? WHERE register_number = ?", (reg_type, reg))
        
        # Export Limit group (id=8)
        cursor.execute("UPDATE registers SET group_id = 8, type = 1 WHERE register_number IN (122, 123)")
        
        # Other registers (Ungrouped, id=1)
        cursor.execute("UPDATE registers SET group_id = 1, type = 1 WHERE register_number IN (608, 1044)")
        
        # Add missing register_values entries
        print("Adding missing register_values entries...")
        new_registers = (
            # Battery First (1090-1108)
            list(range(1090, 1109)) +
            # Load First (1109-1118)
            list(range(1109, 1119)) +
            # Export Limit
            [122, 123] +
            # Other
            [608, 1044]
        )
        
        for reg_num in new_registers:
            cursor.execute("""
                INSERT OR IGNORE INTO register_values (register_number, current_value)
                VALUES (?, 0)
            """, (reg_num,))
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM register_groups")
        group_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM registers")
        register_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM register_values")
        value_count = cursor.fetchone()[0]
        
        print(f"\nSummary:")
        print(f"  Register groups: {group_count}")
        print(f"  Registers: {register_count}")
        print(f"  Register values: {value_count}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
