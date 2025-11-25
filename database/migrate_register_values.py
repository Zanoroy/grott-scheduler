#!/usr/bin/env python3
"""
Migration script to add register_values table
This table stores the current values of registers as the source of truth
"""

import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'scheduler.db')

def migrate():
    """Add register_values table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Create register_values table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS register_values (
                register_number INTEGER PRIMARY KEY,
                current_value INTEGER NOT NULL DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_read_from_inverter TIMESTAMP,
                FOREIGN KEY (register_number) REFERENCES registers(register_number)
            )
        """)
        
        # Initialize register values for registers 1070-1088 (Grid First settings)
        # Values are stored as decimals in the database, converted to hex for transmission
        register_defaults = {
            1070: 100,  # Grid First Discharge Power Rate
            1071: 10,   # Grid First Stop SOC
        }
        
        for reg in range(1070, 1089):
            default_value = register_defaults.get(reg, 0)
            cursor.execute("""
                INSERT OR IGNORE INTO register_values (register_number, current_value) 
                VALUES (?, ?)
            """, (reg, default_value))
        
        # Create index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_register_values_updated 
            ON register_values(last_updated DESC)
        """)
        
        conn.commit()
        print("✓ Migration completed successfully")
        print("✓ Added register_values table")
        print("✓ Initialized 19 registers (1070-1088) with default value 0")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
