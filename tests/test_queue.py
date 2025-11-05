import unittest
import os
from queuectl.storage import Storage, get_db_connection, _connections
from queuectl.queue_manager import QueueManager
from queuectl.config import Config

class TestQueue(unittest.TestCase):

    def setUp(self):
        self.db_file = "test_queue.db"
        # Ensure the test database file does not exist from a previous failed run
        if os.path.exists(self.db_file):
            # If a connection to it is still open, close it.
            if self.db_file in _connections:
                _connections[self.db_file].close()
                del _connections[self.db_file]
            os.remove(self.db_file)

        self.storage = Storage(db_file=self.db_file)
        self.config = Config(db_file=self.db_file)
        self.qm = QueueManager(db_file=self.db_file)

    def tearDown(self):
        # Close the connection and remove it from the pool
        conn = get_db_connection(self.db_file)
        conn.close()
        del _connections[self.db_file]
        
        # Now it's safe to remove the file
        if os.path.exists(self.db_file):
            os.remove(self.db_file)

    def test_enqueue_job(self):
        job_data = {"id": "test1", "command": "echo 'test'"}
        self.qm.enqueue(job_data)
        job = self.storage.get_job("test1")
        self.assertIsNotNone(job)
        self.assertEqual(job['id'], "test1")
        self.assertEqual(job['state'], "pending")

    def test_job_lifecycle(self):
        job_data = {"id": "test2", "command": "echo 'test'"}
        self.qm.enqueue(job_data)

        # Pick up for processing
        job = self.qm.get_job_to_process()
        self.assertEqual(job['id'], "test2")
        self.assertEqual(self.storage.get_job("test2")['state'], "processing")

        # Mark as completed
        self.qm.mark_completed("test2")
        self.assertEqual(self.storage.get_job("test2")['state'], "completed")

    def test_failed_job_and_retry(self):
        self.config.set('max_retries', 3)
        job_data = {"id": "test3", "command": "exit 1"}
        self.qm.enqueue(job_data)

        job = self.qm.get_job_to_process()
        
        # First failure
        self.qm.mark_failed("test3")
        job = self.storage.get_job("test3")
        self.assertEqual(job['state'], "failed")
        self.assertEqual(job['attempts'], 1)

        # Second failure
        self.qm.mark_failed("test3")
        job = self.storage.get_job("test3")
        self.assertEqual(job['state'], "failed")
        self.assertEqual(job['attempts'], 2)

        # Third failure -> moves to DLQ
        self.qm.mark_failed("test3")
        job = self.storage.get_job("test3")
        self.assertEqual(job['state'], "dead")
        self.assertEqual(job['attempts'], 3)

    def test_dlq_retry(self):
        job_data = {"id": "test4", "command": "exit 1"}
        self.qm.enqueue(job_data)
        self.storage.update_job_state("test4", "dead")

        self.assertTrue(self.qm.retry_dlq_job("test4"))
        job = self.storage.get_job("test4")
        self.assertEqual(job['state'], "pending")
        self.assertEqual(job['attempts'], 0)

if __name__ == '__main__':
    unittest.main()
