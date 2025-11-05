import typer
import json
from .queue_manager import QueueManager
from .worker import start_workers, stop_workers, WORKERS
from .config import Config

app = typer.Typer(help="A CLI-based background job queue system.")
queue_manager = QueueManager()
config_manager = Config()

@app.command("enqueue")
def enqueue(job_data: str = typer.Argument(..., help='Job data in JSON format. e.g., \'{"id":"job1","command":"sleep 2"}\'')):
    """
    Add a new job to the queue.
    """
    try:
        data = json.loads(job_data)
        job = queue_manager.enqueue(data)
        print(f"Job enqueued with ID: {job['id']}")
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error: {e}")

@app.command("status")
def status():
    """
    Show a summary of all job states & active workers.
    """
    summary = queue_manager.get_status()
    print("--- Job Status ---")
    for state, count in summary.items():
        print(f"{state.capitalize()}: {count}")
    print("\n--- Worker Status ---")
    print(f"Active Workers: {len(WORKERS)}")


@app.command("list")
def list_jobs(state: str = typer.Option("pending", help="List jobs by state (pending, processing, completed, failed, dead)")):
    """
    List jobs by state.
    """
    jobs = queue_manager.list_jobs(state)
    if not jobs:
        print(f"No jobs found in '{state}' state.")
        return
    
    for job in jobs:
        print(json.dumps(job, indent=2))

# Worker commands
worker_app = typer.Typer(help="Manage worker processes.")
app.add_typer(worker_app, name="worker")

@worker_app.command("start")
def worker_start(count: int = typer.Option(1, "--count", "-c", help="Number of workers to start.")):
    """
    Start one or more worker processes.
    """
    start_workers(count)

@worker_app.command("stop")
def worker_stop():
    """
    Stop all running workers gracefully.
    """
    stop_workers()

# DLQ commands
dlq_app = typer.Typer(help="Manage the Dead Letter Queue (DLQ).")
app.add_typer(dlq_app, name="dlq")

@dlq_app.command("list")
def dlq_list():
    """
    View all jobs in the DLQ.
    """
    jobs = queue_manager.get_dlq()
    if not jobs:
        print("DLQ is empty.")
        return
    for job in jobs:
        print(json.dumps(job, indent=2))

@dlq_app.command("retry")
def dlq_retry(job_id: str = typer.Argument(..., help="The ID of the job to retry.")):
    """
    Retry a job from the DLQ.
    """
    if queue_manager.retry_dlq_job(job_id):
        print(f"Job {job_id} has been moved back to the queue.")
    else:
        print(f"Error: Job {job_id} not found in DLQ or could not be retried.")

# Config commands
config_app = typer.Typer(help="Manage configuration.")
app.add_typer(config_app, name="config")

@config_app.command("set")
def config_set(key: str, value: str):
    """
    Set a configuration value (e.g., max-retries, backoff-base).
    """
    try:
        # map cli-friendly name to internal name
        key_map = {"max-retries": "max_retries", "backoff-base": "backoff_base"}
        internal_key = key_map.get(key, key)
        
        updated_config = config_manager.set(internal_key, value)
        print(f"Configuration updated: {updated_config}")
    except KeyError as e:
        print(f"Error: {e}")

@config_app.command("show")
def config_show():
    """
    Show the current configuration.
    """
    print(json.dumps(config_manager.get_all(), indent=2))
