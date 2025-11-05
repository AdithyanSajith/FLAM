# QueueCTL - A CLI-based background job queue system

This project is a minimal, production-grade job queue system called `queuectl`. It manages background jobs with worker processes, handles retries using exponential backoff, and maintains a Dead Letter Queue (DLQ) for permanently failed jobs.

## Features

- **Enqueue and manage background jobs**: Add jobs to a persistent queue.
- **Multiple worker processes**: Process jobs in parallel.
- **Automatic retries with exponential backoff**: Failed jobs are retried automatically.
- **Dead Letter Queue (DLQ)**: Jobs that fail permanently are moved to a DLQ for manual inspection.
- **Persistent job storage**: Job data survives restarts using SQLite.
- **CLI interface**: All operations are accessible through a command-line interface.

## Tech Stack

- **Python**: The core language for the application.
- **Typer**: For creating the CLI interface.
- **SQLite**: For persistent job storage.

## Architecture Overview

### Job Lifecycle

1.  **`pending`**: A new job is enqueued and waits to be picked up.
2.  **`processing`**: A worker picks up the job and starts executing the command.
3.  **`completed`**: The job's command executes successfully (exit code 0).
4.  **`failed`**: The command fails. The job is scheduled for a retry with an exponential backoff delay.
5.  **`dead`**: The job reaches its maximum number of retries and is moved to the Dead Letter Queue.

### Components

- **`main.py`**: The entry point for the `queuectl` CLI application.
- **`cli.py`**: Defines all the CLI commands using Typer.
- **`queue_manager.py`**: Contains the business logic for managing jobs (enqueue, state changes, DLQ).
- **`worker.py`**: Implements the worker logic for processing jobs. It runs jobs in separate threads.
- **`storage.py`**: Handles all database interactions with SQLite, providing a persistence layer.
- **`config.py`**: Manages system configuration, such as retry counts and backoff rates.

## Setup Instructions

1.  **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd queuectl
    ```

2.  **Create a virtual environment and install dependencies:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    The application is now ready to be used via the `queuectl` command.
    ```bash
    python -m queuectl.main --help
    ```

## Usage Examples

### Enqueue a Job

```bash
python -m queuectl.main enqueue '{"id":"job1", "command":"echo Hello from Job 1"}'
# Output: Job enqueued with ID: job1
```

### Start Workers

```bash
python -m queuectl.main worker start --count 2
# Output: Started 2 workers.
```

_(Workers will start processing jobs in the background)_

### Check Status

```bash
python -m queuectl.main status
# --- Job Status ---
# Completed: 1
#
# --- Worker Status ---
# Active Workers: 2
```

### List Jobs by State

```bash
python -m queuectl.main list --state completed
# {
#   "id": "job1",
#   "command": "echo Hello from Job 1",
#   ...
# }
```

### Manage the DLQ

To simulate a job failing and moving to the DLQ:

```bash
# Enqueue a failing command
python -m queuectl.main enqueue '{"id":"job-fail", "command":"exit 1"}'

# After workers run, it will move to DLQ
python -m queuectl.main dlq list

# Retry a job from the DLQ
python -m queuectl.main dlq retry job-fail
```

### Configure Settings

```bash
# Set max retries to 5
python -m queuectl.main config set max-retries 5

# Show current config
python -m queuectl.main config show
```

## Testing Instructions

A simple test script can be used to validate the core flows.

1.  **Run the test script:**
    _(A test script will be provided to simulate various scenarios)_

    You can manually test the expected scenarios:

    - **Basic success**: `queuectl enqueue '{"id":"j1","command":"echo success"}'`
    - **Failure and retry**: `queuectl enqueue '{"id":"j2","command":"nonexistent-command"}'`
    - **Persistence**: Enqueue jobs, stop workers, restart the app, and see that jobs are still there.

## Assumptions & Trade-offs

- **Concurrency**: The current implementation uses a simple `LIMIT 1` query to fetch pending jobs, which is a basic form of locking. For a high-concurrency production system, a more robust row-level locking mechanism (like `SELECT FOR UPDATE`) would be necessary.
- **Worker Management**: Worker processes are managed in-memory within the main CLI process. For a distributed or more robust system, a dedicated worker manager or a process supervisor (like `systemd` or `supervisor`) would be better.
- **Storage**: SQLite is used for simplicity and to meet the "embedded DB" requirement. For a larger-scale application, a dedicated database server like PostgreSQL would be more appropriate.

## Repository

The source code is available at: [Your GitHub Repository Link Here]

## Demo

A live demo of the CLI in action can be found here: [https://drive.google.com/file/d/1Wcm127__rkNPK-FB54mnEHE-Vosy6hEw/view?usp=sharing](https://drive.google.com/file/d/1Wcm127__rkNPK-FB54mnEHE-Vosy6hEw/view?usp=sharing)
