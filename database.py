import sqlite3
from datetime import datetime
import os

class Database:
    def __init__(self, db_name="jobs.db"):
        self.db_name = db_name
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Table for jobs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_url TEXT UNIQUE,
                    job_id TEXT UNIQUE,
                    job_title TEXT,
                    location TEXT,
                    description TEXT,
                    status TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            """)
            # Table for logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    message TEXT,
                    level TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_job(self, job_url,job_id, status, details=None, job_title=None, location=None, description=None):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO jobs (job_url,job_id, status, details, job_title, location, description, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?,?)
                """, (job_url,job_id, status, details, job_title, location, description, datetime.now().isoformat()))
                conn.commit()
                self.log(f"Job added: {job_title} at {location}", "INFO")
        except sqlite3.Error as e:
            self.log(f"Error adding job: {e}", "ERROR")

    def update_job_status(self, job_id, status):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET status = ? WHERE job_id = ?", (status, job_id))
            conn.commit()

    def log(self, message, level="INFO"):
        print(f"[{level}] {message}")
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO logs (message, level, timestamp) VALUES (?, ?, ?)",
                (message, level, datetime.now().isoformat()))
                conn.commit()
        except sqlite3.Error as e:
            print(f"Failed to log to database: {e}")

    def get_all_jobs(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_logs(self, limit=50):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]