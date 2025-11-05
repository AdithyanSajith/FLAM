import json
import time
from datetime import datetime, timedelta, timezone
from .storage import Storage
from .config import Config

class QueueManager:
    def __init__(self, db_file=None):
        self.storage = Storage(db_file=db_file)
        self.config = Config(db_file=db_file)

    def enqueue(self, job_data):
        job_id = job_data.get("id")
        command = job_data.get("command")
        if not job_id or not command:
            raise ValueError("Job must have an id and command")

        job = {
            "id": job_id,
            "command": command,
            "state": "pending",
            "attempts": 0,
            "max_retries": self.config.get('max_retries'),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.storage.add_job(job)
        return job

    def get_job_to_process(self):
        # This is a simplified locking mechanism.
        # In a real-world scenario, you'd use a more robust locking mechanism.
        job = self.storage.get_pending_job()
        if job:
            self.storage.update_job_state(job['id'], 'processing')
        return job

    def mark_completed(self, job_id):
        self.storage.update_job_state(job_id, 'completed')

    def mark_failed(self, job_id):
        job = self.storage.get_job(job_id)
        if not job:
            return

        attempts = job['attempts'] + 1
        if attempts >= job['max_retries']:
            self.storage.update_job_state(job_id, 'dead', attempts=attempts)
        else:
            self.storage.update_job_state(job_id, 'failed', attempts=attempts)
            # Exponential backoff
            delay = self.config.get('backoff_base') ** attempts
            run_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            self.storage.update_job(job_id, {"run_at": run_at.isoformat()})


    def list_jobs(self, state):
        return self.storage.get_jobs_by_state(state)

    def get_dlq(self):
        return self.storage.get_jobs_by_state('dead')

    def retry_dlq_job(self, job_id):
        job = self.storage.get_job(job_id)
        if job and job['state'] == 'dead':
            self.storage.update_job_state(job_id, 'pending', attempts=0)
            return True
        return False

    def get_status(self):
        return self.storage.get_job_summary()
