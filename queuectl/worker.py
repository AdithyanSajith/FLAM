import subprocess
import time
import threading
from .queue_manager import QueueManager

class Worker:
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.queue_manager = QueueManager()
        self.stop_event = threading.Event()

    def run(self):
        print(f"Worker {self.worker_id} started")
        while not self.stop_event.is_set():
            job = self.queue_manager.get_job_to_process()
            if job:
                print(f"Worker {self.worker_id} picked up job {job['id']}")
                self.execute_job(job)
            else:
                time.sleep(1) # Wait for new jobs

    def execute_job(self, job):
        try:
            result = subprocess.run(job['command'], shell=True, check=True, capture_output=True, text=True)
            print(f"Job {job['id']} completed successfully. Output:\n{result.stdout}")
            self.queue_manager.mark_completed(job['id'])
        except subprocess.CalledProcessError as e:
            print(f"Job {job['id']} failed. Error:\n{e.stderr}")
            self.queue_manager.mark_failed(job['id'])

    def stop(self):
        print(f"Worker {self.worker_id} stopping gracefully...")
        self.stop_event.set()

# In-memory store for worker processes for simplicity
# In a real system, this would be managed more robustly (e.g., PID files, a manager process)
WORKERS = []
WORKER_THREADS = []

def start_workers(count):
    for i in range(count):
        worker = Worker(i + 1)
        WORKERS.append(worker)
        thread = threading.Thread(target=worker.run)
        thread.start()
        WORKER_THREADS.append(thread)
    print(f"Started {count} workers.")

def stop_workers():
    for worker in WORKERS:
        worker.stop()
    for thread in WORKER_THREADS:
        thread.join()
    WORKERS.clear()
    WORKER_THREADS.clear()
    print("All workers stopped.")
