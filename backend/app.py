#!/usr/bin/env python3
"""
Grott Scheduler - Backend API and Scheduler Service
Manages scheduled commands for Growatt inverters via Grott
"""

import os
import sys
import sqlite3
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
import time

from flask import Flask, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, '..', 'database', 'scheduler.db')
LOG_FILE = os.path.join(BASE_DIR, '..', 'logs', 'scheduler.log')

# Ensure logs directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('grott-scheduler')

# Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for Node-RED integration

# Scheduler
scheduler = BackgroundScheduler(timezone=pytz.timezone('UTC'))
scheduler.start()


class Database:
    """Database helper class"""
    
    @staticmethod
    def get_connection():
        """Get database connection"""
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def init_database():
        """Initialize database with schema"""
        schema_file = os.path.join(BASE_DIR, '..', 'database', 'schema.sql')
        if os.path.exists(schema_file):
            conn = Database.get_connection()
            with open(schema_file, 'r') as f:
                conn.executescript(f.read())
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        else:
            logger.error(f"Schema file not found: {schema_file}")
    
    @staticmethod
    def execute(query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor
    
    @staticmethod
    def fetch_all(query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Fetch all results"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results
    
    @staticmethod
    def fetch_one(query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Fetch one result"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        return result


class InverterCommand:
    """Handle inverter commands via Grott"""
    
    @staticmethod
    def get_config() -> Dict[str, str]:
        """Get configuration from database"""
        rows = Database.fetch_all("SELECT key, value FROM config")
        return {row['key']: row['value'] for row in rows}
    
    @staticmethod
    def execute_command(command_data: Dict, inverter_serial: str = None, max_retries: int = 5) -> Tuple[bool, str, int]:
        """
        Execute inverter command with retry logic
        Returns: (success, response/error, attempts)
        """
        config = InverterCommand.get_config()
        host = config.get('grott_host', '<grottserver>')
        port = config.get('grott_port', '5782')
        serial = inverter_serial or config.get('inverter_serial', 'NTCRBLR00Y')
        max_retries = int(config.get('max_retries', max_retries))
        retry_delay = int(config.get('retry_delay', 10))
        
        base_url = f"http://{host}:{port}/inverter"
        
        for attempt in range(1, max_retries + 1):
            try:
                if command_data['type'] == 'read':
                    # Read register value
                    url = f"{base_url}?command=register&inverter={serial}&register={command_data['register']}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            value = data.get('value', 'N/A')
                            logger.info(f"Read register {command_data['register']}: {value}")
                            return True, f"Register {command_data['register']} = {value}", attempt
                        except:
                            return True, response.text, attempt
                    else:
                        logger.warning(f"Attempt {attempt}/{max_retries} failed: {response.status_code} - {response.text}")
                        if attempt < max_retries:
                            time.sleep(retry_delay)
                    
                elif command_data['type'] == 'register':
                    # Single register write
                    url = f"{base_url}?command=register&inverter={serial}&register={command_data['register']}&value={command_data['value']}"
                    response = requests.put(url, timeout=10)
                    
                elif command_data['type'] == 'multiregister':
                    # Multi-register write
                    url = f"{base_url}?command=multiregister&inverter={serial}&startregister={command_data['start_register']}&endregister={command_data['end_register']}&value={command_data['value']}"
                    response = requests.put(url, timeout=10)
                    
                elif command_data['type'] == 'custom':
                    # Custom curl command - parse and execute
                    # This is a simplified version, you might need more robust parsing
                    response = requests.request(
                        method=command_data.get('method', 'GET'),
                        url=command_data['url'],
                        timeout=10
                    )
                else:
                    return False, f"Unknown command type: {command_data['type']}", attempt
                
                # Check response
                if response.status_code == 200 and response.text.strip() == 'OK':
                    logger.info(f"Command executed successfully on attempt {attempt}")
                    return True, response.text, attempt
                else:
                    logger.warning(f"Attempt {attempt}/{max_retries} failed: {response.status_code} - {response.text}")
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                    
            except Exception as e:
                logger.error(f"Attempt {attempt}/{max_retries} error: {str(e)}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
        
        return False, f"Failed after {max_retries} attempts", max_retries
    
    @staticmethod
    def check_condition(condition_type: str, condition_register: int, condition_operator: str, condition_value: str) -> Tuple[bool, str]:
        """
        Check if condition is met
        Returns: (condition_met, details)
        """
        if condition_type == 'none' or not condition_type:
            return True, "No condition"
        
        try:
            # Read current register value
            config = InverterCommand.get_config()
            host = config.get('grott_host', '<grottserver>')
            port = config.get('grott_port', '5782')
            serial = config.get('inverter_serial', 'NTCRBLR00Y')
            
            url = f"http://{host}:{port}/inverter?command=register&inverter={serial}&register={condition_register}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return False, f"Failed to read register {condition_register}"
            
            data = response.json()
            current_value = int(data.get('value', 0))
            target_value = int(condition_value)
            
            # Evaluate condition
            if condition_operator == '<':
                met = current_value < target_value
            elif condition_operator == '>':
                met = current_value > target_value
            elif condition_operator == '=':
                met = current_value == target_value
            elif condition_operator == '<=':
                met = current_value <= target_value
            elif condition_operator == '>=':
                met = current_value >= target_value
            else:
                return False, f"Unknown operator: {condition_operator}"
            
            details = f"Register {condition_register}: {current_value} {condition_operator} {target_value} = {met}"
            return met, details
            
        except Exception as e:
            return False, f"Condition check error: {str(e)}"


class ScheduleExecutor:
    """Execute scheduled tasks"""
    
    @staticmethod
    def execute_schedule(schedule_id: int):
        """Execute a schedule"""
        logger.info(f"Executing schedule ID: {schedule_id}")
        
        # Get schedule details
        schedule = Database.fetch_one(
            "SELECT * FROM schedules WHERE id = ? AND enabled = 1",
            (schedule_id,)
        )
        
        if not schedule:
            logger.warning(f"Schedule {schedule_id} not found or disabled")
            return
        
        # Check condition if applicable
        condition_met = True
        condition_details = "No condition"
        
        if schedule['condition_type'] and schedule['condition_type'] != 'none':
            condition_met, condition_details = InverterCommand.check_condition(
                schedule['condition_type'],
                schedule['condition_register'],
                schedule['condition_operator'],
                schedule['condition_value']
            )
            
            if not condition_met:
                logger.info(f"Condition not met for schedule {schedule_id}: {condition_details}")
                # Log skipped execution
                Database.execute(
                    """INSERT INTO execution_logs 
                       (schedule_id, schedule_name, command, success, attempts, condition_met, condition_details)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (schedule_id, schedule['name'], "Skipped - condition not met", True, 0, False, condition_details)
                )
                return
        
        # Build command
        command_data = ScheduleExecutor.build_command(schedule)
        if not command_data:
            logger.error(f"Failed to build command for schedule {schedule_id}")
            return
        
        # Execute command
        success, response, attempts = InverterCommand.execute_command(
            command_data,
            schedule['inverter_serial']
        )
        
        # Log execution
        Database.execute(
            """INSERT INTO execution_logs 
               (schedule_id, schedule_name, command, success, attempts, response, error_message, condition_met, condition_details)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (schedule_id, schedule['name'], json.dumps(command_data), success, attempts,
             response if success else None, response if not success else None,
             condition_met, condition_details)
        )
        
        # Update last executed
        Database.execute(
            "UPDATE schedules SET last_executed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (schedule_id,)
        )
        
        # Send notification if enabled and failed
        if not success and schedule['pushover_enabled']:
            ScheduleExecutor.send_pushover_notification(schedule, response, attempts)
        
        logger.info(f"Schedule {schedule_id} execution completed: {'SUCCESS' if success else 'FAILED'}")
    
    @staticmethod
    def build_command(schedule: sqlite3.Row) -> Optional[Dict]:
        """Build command data from schedule"""
        try:
            if schedule['command_type'] == 'read':
                return {
                    'type': 'read',
                    'register': schedule['register_number']
                }
            
            elif schedule['command_type'] == 'register':
                return {
                    'type': 'register',
                    'register': schedule['register_number'],
                    'value': schedule['register_value']
                }
            
            elif schedule['command_type'] == 'multiregister':
                return {
                    'type': 'multiregister',
                    'start_register': schedule['multiregister_start'],
                    'end_register': schedule['multiregister_end'],
                    'value': schedule['multiregister_value']
                }
            
            elif schedule['command_type'] == 'template':
                # Load template and execute
                template = Database.fetch_one(
                    "SELECT * FROM templates WHERE name = ?",
                    (schedule['template_name'],)
                )
                if template:
                    return json.loads(template['command_data'])
            
            elif schedule['command_type'] == 'custom':
                return json.loads(schedule['custom_command'])
            
            return None
            
        except Exception as e:
            logger.error(f"Error building command: {str(e)}")
            return None
    
    @staticmethod
    def send_pushover_notification(schedule: sqlite3.Row, error_message: str, attempts: int):
        """Send Pushover notification on failure"""
        try:
            config = InverterCommand.get_config()
            user_key = config.get('pushover_user_key', '')
            api_token = config.get('pushover_api_token', '')
            
            if not user_key or not api_token:
                logger.warning("Pushover credentials not configured")
                return
            
            message = f"Schedule '{schedule['name']}' failed after {attempts} attempts.\nError: {error_message}"
            
            requests.post('https://api.pushover.net/1/messages.json', data={
                'token': api_token,
                'user': user_key,
                'title': 'Grott Scheduler Alert',
                'message': message,
                'priority': 0
            }, timeout=10)
            
            logger.info(f"Pushover notification sent for schedule {schedule['id']}")
            
        except Exception as e:
            logger.error(f"Failed to send Pushover notification: {str(e)}")


# REST API Endpoints

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


@app.route('/api/config', methods=['GET', 'PUT'])
def manage_config():
    """Get or update configuration"""
    if request.method == 'GET':
        rows = Database.fetch_all("SELECT * FROM config")
        config = [dict(row) for row in rows]
        return jsonify(config)
    
    elif request.method == 'PUT':
        data = request.json
        for item in data:
            Database.execute(
                "UPDATE config SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?",
                (item['value'], item['key'])
            )
        return jsonify({'success': True, 'message': 'Configuration updated'})


@app.route('/api/registers', methods=['GET'])
def get_registers():
    """Get all known registers"""
    rows = Database.fetch_all("SELECT * FROM registers ORDER BY category, register_number")
    registers = [dict(row) for row in rows]
    return jsonify(registers)


@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get all templates"""
    rows = Database.fetch_all("SELECT * FROM templates ORDER BY name")
    templates = [dict(row) for row in rows]
    return jsonify(templates)


@app.route('/api/schedules', methods=['GET', 'POST'])
def manage_schedules():
    """Get all schedules or create new schedule"""
    if request.method == 'GET':
        rows = Database.fetch_all("""
            SELECT s.*, 
                   (SELECT COUNT(*) FROM execution_logs WHERE schedule_id = s.id) as execution_count,
                   (SELECT COUNT(*) FROM execution_logs WHERE schedule_id = s.id AND success = 1) as success_count
            FROM schedules s
            ORDER BY s.created_at DESC
        """)
        schedules = [dict(row) for row in rows]
        
        # Parse JSON fields
        for schedule in schedules:
            if schedule.get('days_of_week'):
                schedule['days_of_week'] = json.loads(schedule['days_of_week'])
        
        return jsonify(schedules)
    
    elif request.method == 'POST':
        data = request.json
        
        # Convert days_of_week to JSON if present
        days_of_week = json.dumps(data.get('days_of_week')) if data.get('days_of_week') else None
        
        cursor = Database.execute("""
            INSERT INTO schedules (
                name, description, schedule_type, time, days_of_week, specific_date,
                command_type, register_number, register_name, register_value,
                multiregister_start, multiregister_end, multiregister_value,
                template_name, custom_command,
                condition_type, condition_register, condition_operator, condition_value,
                enabled, pushover_enabled, inverter_serial
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['name'], data.get('description'), data['schedule_type'], data['time'],
            days_of_week, data.get('specific_date'),
            data['command_type'], data.get('register_number'), data.get('register_name'), data.get('register_value'),
            data.get('multiregister_start'), data.get('multiregister_end'), data.get('multiregister_value'),
            data.get('template_name'), data.get('custom_command'),
            data.get('condition_type', 'none'), data.get('condition_register'), data.get('condition_operator'), data.get('condition_value'),
            data.get('enabled', True), data.get('pushover_enabled', True), data.get('inverter_serial')
        ))
        
        schedule_id = cursor.lastrowid
        
        # Add to scheduler
        add_schedule_to_apscheduler(schedule_id)
        
        return jsonify({'success': True, 'id': schedule_id, 'message': 'Schedule created'}), 201


@app.route('/api/schedules/<int:schedule_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_schedule(schedule_id):
    """Get, update, or delete a specific schedule"""
    if request.method == 'GET':
        row = Database.fetch_one("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
        if not row:
            return jsonify({'error': 'Schedule not found'}), 404
        
        schedule = dict(row)
        if schedule.get('days_of_week'):
            schedule['days_of_week'] = json.loads(schedule['days_of_week'])
        
        return jsonify(schedule)
    
    elif request.method == 'PUT':
        data = request.json
        days_of_week = json.dumps(data.get('days_of_week')) if data.get('days_of_week') else None
        
        Database.execute("""
            UPDATE schedules SET
                name = ?, description = ?, schedule_type = ?, time = ?, days_of_week = ?, specific_date = ?,
                command_type = ?, register_number = ?, register_name = ?, register_value = ?,
                multiregister_start = ?, multiregister_end = ?, multiregister_value = ?,
                template_name = ?, custom_command = ?,
                condition_type = ?, condition_register = ?, condition_operator = ?, condition_value = ?,
                enabled = ?, pushover_enabled = ?, inverter_serial = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            data['name'], data.get('description'), data['schedule_type'], data['time'],
            days_of_week, data.get('specific_date'),
            data['command_type'], data.get('register_number'), data.get('register_name'), data.get('register_value'),
            data.get('multiregister_start'), data.get('multiregister_end'), data.get('multiregister_value'),
            data.get('template_name'), data.get('custom_command'),
            data.get('condition_type', 'none'), data.get('condition_register'), data.get('condition_operator'), data.get('condition_value'),
            data.get('enabled', True), data.get('pushover_enabled', True), data.get('inverter_serial'),
            schedule_id
        ))
        
        # Remove and re-add to scheduler
        scheduler.remove_job(f"schedule_{schedule_id}", jobstore='default')
        add_schedule_to_apscheduler(schedule_id)
        
        return jsonify({'success': True, 'message': 'Schedule updated'})
    
    elif request.method == 'DELETE':
        # Remove from scheduler
        try:
            scheduler.remove_job(f"schedule_{schedule_id}", jobstore='default')
        except:
            pass
        
        # Delete from database
        Database.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        
        return jsonify({'success': True, 'message': 'Schedule deleted'})


@app.route('/api/schedules/<int:schedule_id>/execute', methods=['POST'])
def execute_schedule_now(schedule_id):
    """Manually execute a schedule immediately"""
    try:
        ScheduleExecutor.execute_schedule(schedule_id)
        return jsonify({'success': True, 'message': 'Schedule executed'})
    except Exception as e:
        logger.error(f"Error executing schedule {schedule_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/logs', methods=['GET'])
def get_execution_logs():
    """Get execution logs"""
    limit = request.args.get('limit', 100, type=int)
    schedule_id = request.args.get('schedule_id', type=int)
    
    query = "SELECT * FROM execution_logs"
    params = ()
    
    if schedule_id:
        query += " WHERE schedule_id = ?"
        params = (schedule_id,)
    
    query += " ORDER BY executed_at DESC LIMIT ?"
    params = params + (limit,)
    
    rows = Database.fetch_all(query, params)
    logs = [dict(row) for row in rows]
    
    return jsonify(logs)


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics"""
    stats = {}
    
    # Total schedules
    row = Database.fetch_one("SELECT COUNT(*) as count FROM schedules")
    stats['total_schedules'] = row['count']
    
    # Active schedules
    row = Database.fetch_one("SELECT COUNT(*) as count FROM schedules WHERE enabled = 1")
    stats['active_schedules'] = row['count']
    
    # Total executions
    row = Database.fetch_one("SELECT COUNT(*) as count FROM execution_logs")
    stats['total_executions'] = row['count']
    
    # Success rate
    row = Database.fetch_one("SELECT COUNT(*) as count FROM execution_logs WHERE success = 1")
    stats['successful_executions'] = row['count']
    
    # Recent failures
    rows = Database.fetch_all("""
        SELECT schedule_name, executed_at, error_message 
        FROM execution_logs 
        WHERE success = 0 
        ORDER BY executed_at DESC 
        LIMIT 10
    """)
    stats['recent_failures'] = [dict(row) for row in rows]
    
    # Next executions
    rows = Database.fetch_all("""
        SELECT id, name, schedule_type, time, next_execution_at
        FROM schedules 
        WHERE enabled = 1 AND next_execution_at IS NOT NULL
        ORDER BY next_execution_at ASC 
        LIMIT 10
    """)
    stats['upcoming_schedules'] = [dict(row) for row in rows]
    
    return jsonify(stats)


def add_schedule_to_apscheduler(schedule_id: int):
    """Add schedule to APScheduler"""
    schedule = Database.fetch_one("SELECT * FROM schedules WHERE id = ? AND enabled = 1", (schedule_id,))
    
    if not schedule:
        return
    
    job_id = f"schedule_{schedule_id}"
    
    try:
        # Remove existing job if present
        try:
            scheduler.remove_job(job_id)
        except:
            pass
        
        # Parse time
        hour, minute = map(int, schedule['time'].split(':'))
        
        if schedule['schedule_type'] == 'daily':
            # Daily schedule
            trigger = CronTrigger(hour=hour, minute=minute)
            scheduler.add_job(
                func=ScheduleExecutor.execute_schedule,
                trigger=trigger,
                args=[schedule_id],
                id=job_id,
                replace_existing=True
            )
            logger.info(f"Added daily schedule {schedule_id} at {schedule['time']}")
        
        elif schedule['schedule_type'] == 'weekly':
            # Weekly schedule
            days_of_week = json.loads(schedule['days_of_week']) if schedule['days_of_week'] else []
            if days_of_week:
                # APScheduler uses 0=Monday, 6=Sunday (same as Python)
                trigger = CronTrigger(day_of_week=','.join(map(str, days_of_week)), hour=hour, minute=minute)
                scheduler.add_job(
                    func=ScheduleExecutor.execute_schedule,
                    trigger=trigger,
                    args=[schedule_id],
                    id=job_id,
                    replace_existing=True
                )
                logger.info(f"Added weekly schedule {schedule_id} for days {days_of_week} at {schedule['time']}")
        
        elif schedule['schedule_type'] == 'once':
            # One-time schedule
            if schedule['specific_date']:
                run_date = datetime.strptime(f"{schedule['specific_date']} {schedule['time']}", "%Y-%m-%d %H:%M")
                if run_date > datetime.now():
                    trigger = DateTrigger(run_date=run_date)
                    scheduler.add_job(
                        func=ScheduleExecutor.execute_schedule,
                        trigger=trigger,
                        args=[schedule_id],
                        id=job_id,
                        replace_existing=True
                    )
                    logger.info(f"Added one-time schedule {schedule_id} for {run_date}")
                else:
                    logger.warning(f"One-time schedule {schedule_id} date is in the past")
        
        # Update next execution time
        next_run = scheduler.get_job(job_id).next_run_time if scheduler.get_job(job_id) else None
        if next_run:
            Database.execute(
                "UPDATE schedules SET next_execution_at = ? WHERE id = ?",
                (next_run.isoformat(), schedule_id)
            )
        
    except Exception as e:
        logger.error(f"Error adding schedule {schedule_id} to APScheduler: {str(e)}")


def initialize_scheduler():
    """Load all active schedules into APScheduler"""
    logger.info("Initializing scheduler...")
    
    schedules = Database.fetch_all("SELECT id FROM schedules WHERE enabled = 1")
    for schedule in schedules:
        add_schedule_to_apscheduler(schedule['id'])
    
    logger.info(f"Loaded {len(schedules)} active schedules")


if __name__ == '__main__':
    # Initialize database
    Database.init_database()
    
    # Initialize scheduler
    initialize_scheduler()
    
    # Start Flask app
    logger.info("Starting Grott Scheduler API on port 5783...")
    app.run(host='0.0.0.0', port=5783, debug=False)
