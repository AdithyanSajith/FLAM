# QueueCTL - Architecture and Design

This document outlines the architecture and design decisions for `queuectl`, a CLI-based background job queue system.

## 1. Core Components

The system is designed with a clear separation of concerns, broken down into the following components:

- **CLI (`cli.py`)**: The user-facing interface built with **Typer**. It's responsible for parsing commands and orchestrating the other components. It remains lightweight and delegates all business logic.

- **Queue Manager (`queue_manager.py`)**: The brain of the system. It handles the core logic of the job lifecycle:

  - Enqueuing new jobs.
  - Transitioning jobs between states (`pending`, `processing`, `completed`, `failed`, `dead`).
  - Managing the Dead Letter Queue (DLQ).
  - Coordinating with the storage layer.

- **Worker (`worker.py`)**: Responsible for executing jobs.

  - Each worker runs in a separate thread, allowing for parallel processing.
  - It fetches a job from the queue, executes its command using `subprocess`, and reports the outcome (success or failure) back to the Queue Manager.
  - It includes a graceful shutdown mechanism to finish its current job before exiting.

- **Storage (`storage.py`)**: The persistence layer.

  - **SQLite** was chosen as the database. It's a serverless, file-based database, which fits the requirement for an embedded, persistent storage solution without requiring a separate database server.
  - It abstracts all SQL queries, providing simple methods for the Queue Manager to interact with the data (e.g., `add_job`, `get_pending_job`).
  - A single `jobs` table stores all job information, and a `config` table stores system settings.

- **Configuration (`config.py`)**: Manages system-wide settings.
  - It provides a simple key-value interface for getting and setting configuration parameters like `max_retries` and `backoff_base`.
  - Configuration is persisted in the same SQLite database.

## 2. Job Lifecycle and State Management

A job progresses through a well-defined lifecycle, managed by its `state` field:

1.  **`pending`**: A job is created in this state. Workers poll for `pending` jobs.
2.  **`processing`**: When a worker picks up a job, it immediately sets its state to `processing`. This acts as a **locking mechanism** to prevent other workers from picking up the same job.
3.  **`completed`**: If the job's command returns an exit code of `0`, the worker marks it as `completed`.
4.  **`failed`**: If the command returns a non-zero exit code, the worker marks it as `failed`. The Queue Manager increments the `attempts` counter and calculates the next `run_at` time for the exponential backoff.
5.  **`dead`**: If a job fails and its `attempts` have reached `max_retries`, it is moved to the `dead` state, effectively placing it in the Dead Letter Queue.

## 3. Concurrency and Locking

To support multiple workers safely, a locking mechanism is essential to prevent two workers from executing the same job.

- **Strategy**: The current implementation uses **optimistic locking at the application level**.

  1.  A worker queries for a `pending` job.
  2.  As soon as it fetches a job, it immediately updates its state to `processing`.
  3.  This state change is an atomic operation in the database.
  4.  Other workers querying for `pending` jobs will no longer see the job that was just picked up.

- **Trade-offs**: This is a simple and effective strategy for moderate load. In a highly concurrent, distributed environment, this could be improved with database-level locking (e.g., `SELECT ... FOR UPDATE`) to ensure atomicity between selecting and updating the job row.

## 4. Persistence

- **Choice of Database**: **SQLite** was chosen because it's lightweight, serverless, and stores the entire database in a single file (`queue.db`). This makes the application self-contained and easy to set up, fulfilling the "embedded DB" requirement perfectly.
- **Schema**:
  - `jobs` table: Contains all job fields, including state, attempts, and timestamps. An index on the `state` and `created_at` columns would improve query performance for fetching pending jobs.
  - `config` table: A simple key-value store for system settings.

## 5. Retry Mechanism and Exponential Backoff

- When a job fails, it doesn't immediately return to the `pending` state. Instead, it's marked as `failed`, and its `run_at` field is updated.
- The delay is calculated using the formula: `delay = base ^ attempts`.
  - `base` is a configurable value (`backoff_base`).
  - `attempts` is the number of times the job has failed.
- Workers are programmed to pick up jobs that are either `pending` OR (`failed` AND `run_at` is in the past). This ensures that failed jobs are only retried after their backoff delay has passed.

## 6. Configuration Management

- The `config` module provides a centralized way to manage settings.
- Storing configuration in the database allows it to be changed dynamically via the CLI (`queuectl config set`) without requiring a restart of the application.
- Default values are hardcoded in the `Config` class to ensure the system can run out-of-the-box.

## 7. Modularity and Extensibility

The code is structured into modules with distinct responsibilities. This makes it:

- **Easier to maintain**: Changes to the storage layer won't affect the CLI logic.
- **Easier to test**: Each component can be unit-tested in isolation.
- **Extensible**: New features, like a web dashboard or different storage backends, can be added by creating new modules that conform to the existing interfaces.
