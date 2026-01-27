import unittest
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch, MagicMock
import importlib.util

# Path to the of-dag script
OF_DAG_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'scripts', 'of-dag'))

# Load the script as a module for unit testing
spec = importlib.util.spec_from_loader("of_dag", loader=None, origin=OF_DAG_SCRIPT)
of_dag = importlib.util.module_from_spec(spec)
with open(OF_DAG_SCRIPT) as f:
    exec(f.read(), of_dag.__dict__)


class TestUrlExtraction(unittest.TestCase):
    """Unit tests for URL extraction logic."""

    def test_extract_url_simple(self):
        """Test extracting URL from a simple log line."""
        log_line = "View the DAG at https://airflow.example.com/dag?id=test"
        url = of_dag.extract_url(log_line)
        self.assertEqual(url, "https://airflow.example.com/dag?id=test")

    def test_extract_url_full_log_format(self):
        """Test extracting URL from actual oneflow log format."""
        log_line = "[2026-01-27 00:17:42,401] {logging_mixin.py:113} INFO - [2026-01-27 00:17:42,401] {workflow.py:39} INFO - View the DAG at https://airflow-stone.d.musta.ch/tree?base_date=&num_runs=1&dag_id=oneflow__1720553__airseal_s3_sampler&arrange=UD&root="
        url = of_dag.extract_url(log_line)
        self.assertEqual(
            url,
            "https://airflow-stone.d.musta.ch/tree?base_date=&num_runs=1&dag_id=oneflow__1720553__airseal_s3_sampler&arrange=UD&root="
        )

    def test_extract_url_no_match(self):
        """Test that None is returned when no URL is found."""
        log_line = "[2026-01-27 00:17:42,401] {workflow.py:39} INFO - Starting task..."
        url = of_dag.extract_url(log_line)
        self.assertIsNone(url)

    def test_extract_url_http(self):
        """Test extracting HTTP URL (not HTTPS)."""
        log_line = "View the DAG at http://localhost:8080/dag?id=test"
        url = of_dag.extract_url(log_line)
        self.assertEqual(url, "http://localhost:8080/dag?id=test")

    def test_extract_url_multiline(self):
        """Test extracting URL from multiline log output."""
        logs = """
[2026-01-27 00:17:40,000] {workflow.py:10} INFO - Initializing workflow...
[2026-01-27 00:17:41,000] {workflow.py:20} INFO - Processing data...
[2026-01-27 00:17:42,401] {workflow.py:39} INFO - View the DAG at https://airflow.example.com/tree?dag_id=test
[2026-01-27 00:17:43,000] {workflow.py:50} INFO - Done.
"""
        url = of_dag.extract_url(logs)
        self.assertEqual(url, "https://airflow.example.com/tree?dag_id=test")


class TestOfDagIntegration(unittest.TestCase):
    """Integration tests using mocked 'of' command."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.fake_of_dir = os.path.join(self.test_dir, 'bin')
        os.makedirs(self.fake_of_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)

    def create_fake_of(self, logs_output, exit_code=0):
        """Create a fake 'of' script that returns specified output."""
        fake_of = os.path.join(self.fake_of_dir, 'of')
        with open(fake_of, 'w') as f:
            f.write('#!/bin/sh\n')
            f.write(f'echo "{logs_output}"\n')
            f.write(f'exit {exit_code}\n')
        os.chmod(fake_of, 0o755)
        return fake_of

    def test_finds_url_in_logs(self):
        """Test that script finds and prints URL from logs."""
        log_output = "[2026-01-27 00:17:42,401] {workflow.py:39} INFO - View the DAG at https://airflow.example.com/dag?id=test123"
        self.create_fake_of(log_output)

        env = os.environ.copy()
        env['PATH'] = self.fake_of_dir + os.pathsep + env['PATH']
        env['DATA_DIR'] = self.test_dir

        result = subprocess.run(
            [sys.executable, OF_DAG_SCRIPT, '--print', 'job123'],
            env=env,
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("https://airflow.example.com/dag?id=test123", result.stdout)

    def test_no_url_found_exits_nonzero(self):
        """Test that script exits with error when no URL found."""
        log_output = "[2026-01-27 00:17:42,401] {workflow.py:39} INFO - Task completed"
        self.create_fake_of(log_output)

        env = os.environ.copy()
        env['PATH'] = self.fake_of_dir + os.pathsep + env['PATH']
        env['DATA_DIR'] = self.test_dir

        result = subprocess.run(
            [sys.executable, OF_DAG_SCRIPT, 'job123'],
            env=env,
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("No DAG URL found", result.stderr)

    def test_warns_without_data_dir(self):
        """Test that script warns when DATA_DIR is not set."""
        log_output = "View the DAG at https://airflow.example.com/dag"
        self.create_fake_of(log_output)

        env = os.environ.copy()
        env['PATH'] = self.fake_of_dir + os.pathsep + env['PATH']
        env.pop('DATA_DIR', None)

        result = subprocess.run(
            [sys.executable, OF_DAG_SCRIPT, '--print', 'job123'],
            env=env,
            capture_output=True,
            text=True
        )

        self.assertIn("DATA_DIR not set", result.stderr)

    def test_help_output(self):
        """Test that --help works."""
        result = subprocess.run(
            [sys.executable, OF_DAG_SCRIPT, '--help'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("job_id", result.stdout)
        self.assertIn("--tail", result.stdout)
        self.assertIn("--print", result.stdout)


if __name__ == '__main__':
    unittest.main()
