import sqlite3
import json
from datetime import datetime, timezone

DB_FILE = 'queue.db'

# This dictionary will act as a connection pool, ensuring one connection per DB file.
_connections = {}

def get_db_connection(db_file=None):
    """Gets a single connection for a given database file."""
    global DB_FILE
    db_path = db_file or DB_FILE
    if db_path not in _connections:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _connections[db_path] = conn
    return _connections[db_path]

class Storage:
    def __init__(self, db_file=None):
        self.conn = get_db_connection(db_file)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    command TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_retries INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    run_at TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

    def add_job(self, job):
        with self.conn:
            self.conn.execute("""
                INSERT INTO jobs (id, command, state, attempts, max_retries, created_at, updated_at)
                VALUES (:id, :command, :state, :attempts, :max_retries, :created_at, :updated_at)
            """, job)

    def get_job(self, job_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_pending_job(self):
        with self.conn:
            cursor = self.conn.cursor()
            # Find a job that is pending or failed and ready to be run
            cursor.execute("""
                SELECT * FROM jobs 
                WHERE (state = 'pending' OR (state = 'failed' AND run_at <= ?))
                ORDER BY created_at ASC 
                LIMIT 1
            """, (datetime.now(timezone.utc).isoformat(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_job_state(self, job_id, state, attempts=None):
        with self.conn:
            data = {
                "id": job_id,
                "state": state,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            query = "UPDATE jobs SET state = :state, updated_at = :updated_at"
            if attempts is not None:
                query += ", attempts = :attempts"
                data["attempts"] = attempts
            
            query += " WHERE id = :id"
            self.conn.execute(query, data)

    def update_job(self, job_id, updates):
        with self.conn:
            updates['id'] = job_id
            updates['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            set_clauses = ", ".join([f"{key} = :{key}" for key in updates if key != 'id'])
            query = f"UPDATE jobs SET {set_clauses} WHERE id = :id"
            self.conn.execute(query, updates)

    def get_jobs_by_state(self, state):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE state = ?", (state,))
        return [dict(row) for row in cursor.fetchall()]

    def get_job_summary(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT state, COUNT(*) as count FROM jobs GROUP BY state")
        return {row['state']: row['count'] for row in cursor.fetchall()}

    def get_config(self, key, default=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        return json.loads(row['value']) if row else default

    def set_config(self, key, value):
        with self.conn:
            self.conn.execute("REPLACE INTO config (key, value) VALUES (?, ?)", (key, json.dumps(value)))
