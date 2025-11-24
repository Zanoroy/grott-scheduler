#!/usr/bin/env python3
"""
Test script for parent-child schedule chains
Creates a sample chain and tests execution
"""

import requests
import json
import time

API_BASE = "http://localhost:5783/api"

def create_test_schedules():
    """Create a test parent-child schedule chain"""
    
    print("Creating test schedule chain...")
    
    # Create parent schedule
    parent = {
        "name": "Test Parent - Set Load First",
        "description": "Parent schedule to switch to Load First mode",
        "schedule_type": "daily",
        "time": "06:00",
        "command_type": "register",
        "register_number": 1044,
        "register_name": "Priority Mode",
        "register_value": "0",
        "enabled": True,
        "pushover_enabled": False
    }
    
    response = requests.post(f"{API_BASE}/schedules", json=parent)
    if response.status_code == 201:
        parent_id = response.json()['id']
        print(f"✓ Created parent schedule (ID: {parent_id})")
    else:
        print(f"✗ Failed to create parent: {response.text}")
        return
    
    # Create child schedule 1
    child1 = {
        "name": "Test Child 1 - Set SOC to 100%",
        "description": "First child - sets discharge stop SOC",
        "schedule_type": "daily",
        "time": "06:00",
        "command_type": "register",
        "register_number": 608,
        "register_name": "Load First Discharge Stop SOC",
        "register_value": "100",
        "enabled": True,
        "pushover_enabled": False,
        "parent_schedule_id": parent_id,
        "execution_order": 0,
        "continue_on_parent_failure": False
    }
    
    response = requests.post(f"{API_BASE}/schedules", json=child1)
    if response.status_code == 201:
        child1_id = response.json()['id']
        print(f"✓ Created child schedule 1 (ID: {child1_id})")
    else:
        print(f"✗ Failed to create child 1: {response.text}")
        return
    
    # Create child schedule 2
    child2 = {
        "name": "Test Child 2 - Enable Grid First Schedule 1",
        "description": "Second child - enables a schedule slot",
        "schedule_type": "daily",
        "time": "06:00",
        "command_type": "register",
        "register_number": 1082,
        "register_name": "Grid First Enable 1",
        "register_value": "1",
        "enabled": True,
        "pushover_enabled": False,
        "parent_schedule_id": parent_id,
        "execution_order": 1,
        "continue_on_parent_failure": False
    }
    
    response = requests.post(f"{API_BASE}/schedules", json=child2)
    if response.status_code == 201:
        child2_id = response.json()['id']
        print(f"✓ Created child schedule 2 (ID: {child2_id})")
    else:
        print(f"✗ Failed to create child 2: {response.text}")
        return
    
    print(f"\n✓ Successfully created schedule chain!")
    print(f"  Parent ID: {parent_id}")
    print(f"  Child 1 ID: {child1_id} (order: 0)")
    print(f"  Child 2 ID: {child2_id} (order: 1)")
    
    return parent_id, child1_id, child2_id


def test_execution(parent_id):
    """Test executing the parent schedule"""
    
    print(f"\nTesting execution of parent schedule (ID: {parent_id})...")
    print("This will execute the parent and all children in sequence.")
    print("(Note: This will send commands to your Grott server!)")
    
    input("Press Enter to execute the schedule chain, or Ctrl+C to cancel...")
    
    response = requests.post(f"{API_BASE}/schedules/{parent_id}/execute")
    if response.ok:
        result = response.json()
        print(f"✓ Execution completed")
        print(f"  Success: {result.get('execution_success')}")
        print(f"  Log ID: {result.get('execution_log_id')}")
    else:
        print(f"✗ Execution failed: {response.text}")


def show_schedules():
    """Display all schedules"""
    
    print("\nCurrent schedules:")
    response = requests.get(f"{API_BASE}/schedules")
    if response.ok:
        schedules = response.json()
        for s in schedules:
            indent = "  ↪ " if s.get('parent_schedule_id') else ""
            parent_info = f" (child of {s['parent_schedule_id']})" if s.get('parent_schedule_id') else ""
            child_info = f" [{s.get('child_count', 0)} children]" if s.get('child_count', 0) > 0 else ""
            print(f"{indent}{s['id']}: {s['name']}{parent_info}{child_info}")
    else:
        print(f"✗ Failed to get schedules: {response.text}")


def show_logs():
    """Display recent execution logs"""
    
    print("\nRecent execution logs:")
    response = requests.get(f"{API_BASE}/logs?limit=10")
    if response.ok:
        logs = response.json()
        for log in logs:
            parent_info = f" (child of log {log['parent_execution_id']})" if log.get('parent_execution_id') else ""
            status = "✓" if log['success'] else "✗"
            print(f"{status} {log['schedule_name']} - {log['executed_at']}{parent_info}")
            if log.get('error_message'):
                print(f"    Error: {log['error_message']}")
    else:
        print(f"✗ Failed to get logs: {response.text}")


def cleanup(parent_id):
    """Clean up test schedules"""
    
    print(f"\nCleaning up test schedules...")
    
    # Deleting parent will cascade to children
    response = requests.delete(f"{API_BASE}/schedules/{parent_id}")
    if response.ok:
        print("✓ Deleted parent and child schedules")
    else:
        print(f"✗ Failed to delete: {response.text}")


if __name__ == "__main__":
    print("=== Grott Scheduler - Parent-Child Chain Test ===\n")
    
    try:
        # Show current state
        show_schedules()
        
        # Create test chain
        ids = create_test_schedules()
        if not ids:
            print("\nFailed to create schedules. Exiting.")
            exit(1)
        
        parent_id, child1_id, child2_id = ids
        
        # Show schedules
        show_schedules()
        
        # Test execution (optional)
        choice = input("\nDo you want to test execution? (y/n): ")
        if choice.lower() == 'y':
            test_execution(parent_id)
            time.sleep(1)
            show_logs()
        
        # Cleanup
        choice = input("\nDo you want to delete the test schedules? (y/n): ")
        if choice.lower() == 'y':
            cleanup(parent_id)
            show_schedules()
        else:
            print(f"\nTest schedules kept. Parent ID: {parent_id}")
        
        print("\n✓ Test complete!")
        
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
