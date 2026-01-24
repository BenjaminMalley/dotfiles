import unittest
import os
import shutil
import subprocess
import time
import sys
import tempfile
from unittest.mock import patch
from pathlib import Path
import importlib.util

# Path to the wts script
WTS_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'scripts', 'wts'))

class TestWtsIntegration(unittest.TestCase):
    def run_tmux(self, *args, **kwargs):
        """Helper to run tmux commands with a custom socket."""
        # Use a custom socket to isolate from user's running tmux
        base_cmd = ['tmux', '-L', 'wts_test_socket']
        # If we are starting the server (new-session), we might want -f /dev/null
        # But we can pass it in args if needed.
        # However, for consistency, let's just prepend the socket.
        full_cmd = base_cmd + list(args)
        return subprocess.run(full_cmd, **kwargs)

    def setUp(self):
        # Create a temp directory
        self.test_dir = os.path.join(os.path.dirname(__file__), 'temp_wts_test')
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

        # Setup Git Repo
        subprocess.run(['git', 'init'], cwd=self.test_dir, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.test_dir, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.test_dir, check=True)
        subprocess.run(['git', 'commit', '--allow-empty', '-m', 'Initial commit'], cwd=self.test_dir, check=True, stdout=subprocess.DEVNULL)

        # Create worktree for the cleanup test
        # We need to simulate the folder structure that wts expects: ~/worktrees/<repo>/<branch>
        repo_name = os.path.basename(self.test_dir)
        self.worktree_path = os.path.join(self.test_dir, 'worktrees', repo_name, 'feature-branch')
        # Parent dir must exist
        os.makedirs(os.path.dirname(self.worktree_path), exist_ok=True)
        subprocess.run(['git', 'worktree', 'add', self.worktree_path, '-b', 'feature-branch'], cwd=self.test_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        self.session_name = "test-wts-session"
        
        # Ensure clean state for tmux server on this socket
        self.run_tmux('kill-server', stderr=subprocess.DEVNULL)
        
        # Start a dummy session to keep the server alive when the test session is killed
        # This mimics real usage where other sessions usually exist.
        # If the server dies (last session killed), the run-shell background job might be terminated.
        self.run_tmux('new-session', '-d', '-s', 'keepalive', '/bin/sh', check=True)

    def tearDown(self):
        # Clean up tmux server
        self.run_tmux('kill-server', stderr=subprocess.DEVNULL)
        
        # Clean up temp dir
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_wts_create(self):
        """Tests the creation of a worktree and tmux session."""
        branch_name = "new-feature"
        # Create the branch first
        subprocess.run(['git', 'branch', branch_name], cwd=self.test_dir, check=True)
        
        # Create a fake tmux script to intercept calls
        fake_tmux_dir = os.path.join(self.test_dir, 'bin')
        os.makedirs(fake_tmux_dir)
        fake_tmux = os.path.join(fake_tmux_dir, 'tmux')
        tmux_log = os.path.join(self.test_dir, 'tmux.log')
        with open(fake_tmux, 'w') as f:
            f.write(f'#!/bin/sh\necho "fake tmux called with: $@" >> {tmux_log}\n')
            f.write('if echo "$@" | grep -q "has-session"; then\n')
            f.write('  exit 1\n')
            f.write('fi\n')
            f.write('exit 0\n')
        os.chmod(fake_tmux, 0o755)
        
        # Setup environment to use fake home and fake tmux
        env = os.environ.copy()
        env['HOME'] = self.test_dir
        env['PATH'] = fake_tmux_dir + os.pathsep + env['PATH']
        
        # Run wts script
        subprocess.run([sys.executable, WTS_SCRIPT, branch_name], cwd=self.test_dir, env=env, check=True)

        # Verify worktree was created
        repo_name = os.path.basename(self.test_dir)
        # wts creates worktrees in ~/worktrees/<repo>/<branch>
        expected_path = os.path.join(self.test_dir, 'worktrees', repo_name, branch_name)
        self.assertTrue(os.path.exists(expected_path), f"Worktree should be created at {expected_path}")
        
        # Verify tmux execution was attempted
        self.assertTrue(os.path.exists(tmux_log), "tmux should have been called")
        with open(tmux_log, 'r') as f:
            content = f.read()
            self.assertIn("new-session", content)
            self.assertIn(branch_name, content)

    def test_wts_done(self):
        # Start tmux session running the wts command directly
        # This avoids shell startup scripts (like airchat) interfering
        # We must set HOME so wts knows where ~/worktrees is (checking against our temp dir)
        cmd_str = f"export HOME='{self.test_dir}'; '{sys.executable}' '{WTS_SCRIPT}' --done"
        
        # Start the session. It runs the command and stays open until command finishes (or is killed)
        self.run_tmux('new-session', '-d', '-s', self.session_name, '-c', self.worktree_path, cmd_str, check=True)

        # Wait for cleanup
        max_retries = 20
        for _ in range(max_retries):
            # Check if session is gone
            ret = self.run_tmux('has-session', '-t', self.session_name, stderr=subprocess.DEVNULL)
            if ret.returncode != 0:
                break
            time.sleep(0.5)
        
        self.assertNotEqual(ret.returncode, 0, "Tmux session should have been killed")

        # Check if worktree is gone
        self.assertFalse(os.path.exists(self.worktree_path), "Worktree directory should have been removed")

    def test_wts_done_alias(self):
        """Tests the -d alias for cleanup."""
        # Start tmux session running the wts command with -d
        cmd_str = f"export HOME='{self.test_dir}'; '{sys.executable}' '{WTS_SCRIPT}' -d"
        
        # Start the session
        self.run_tmux('new-session', '-d', '-s', self.session_name, '-c', self.worktree_path, cmd_str, check=True)

        # Wait for cleanup
        max_retries = 20
        for _ in range(max_retries):
            ret = self.run_tmux('has-session', '-t', self.session_name, stderr=subprocess.DEVNULL)
            if ret.returncode != 0:
                break
            time.sleep(0.5)
        
        self.assertNotEqual(ret.returncode, 0, "Tmux session should have been killed with -d")
        self.assertFalse(os.path.exists(self.worktree_path), "Worktree directory should have been removed with -d")

    def test_wts_create_no_worktree(self):
        """Tests creation of session without worktree (inside repo)."""
        branch_name = "fix-bug"
        
        # Create a fake tmux script
        fake_tmux_dir = os.path.join(self.test_dir, 'bin')
        os.makedirs(fake_tmux_dir, exist_ok=True)
        fake_tmux = os.path.join(fake_tmux_dir, 'tmux')
        tmux_log = os.path.join(self.test_dir, 'tmux_nw.log')
        with open(fake_tmux, 'w') as f:
            f.write(f'#!/bin/sh\necho "fake tmux called with: $@" >> {tmux_log}\n')
            f.write('if echo "$@" | grep -q "has-session"; then\n')
            f.write('  exit 1\n')
            f.write('fi\n')
            f.write('exit 0\n')
        os.chmod(fake_tmux, 0o755)
        
        env = os.environ.copy()
        env['HOME'] = self.test_dir
        env['PATH'] = fake_tmux_dir + os.pathsep + env['PATH']
        
        # Run wts with --no-worktree
        # Note: Depending on implementation, flag might need to be before or after name
        # We will assume argparse handles both, but let's put it after for now or check usage
        subprocess.run([sys.executable, WTS_SCRIPT, branch_name, '--no-worktree'], cwd=self.test_dir, env=env, check=True)
        
        # Verify NO worktree was created
        repo_name = os.path.basename(self.test_dir)
        unexpected_path = os.path.join(self.test_dir, 'worktrees', repo_name, branch_name)
        self.assertFalse(os.path.exists(unexpected_path), "Worktree should NOT be created")
        
        # Verify tmux called with correct session name and CWD (should be repo root)
        with open(tmux_log, 'r') as f:
            content = f.read()
            self.assertIn(f"new-session -d -s {repo_name}-{branch_name}", content)
            # It should set CWD to self.test_dir
            self.assertIn(f"-c {self.test_dir}", content)

    def test_wts_outside_repo(self):
        """Tests creation of session outside of a git repo."""
        # Create a temp dir outside of the current git repo
        with tempfile.TemporaryDirectory() as temp_dir:
            session_name = "random-session"
            
            # Fake tmux setup
            fake_tmux_dir = os.path.join(temp_dir, 'bin')
            os.makedirs(fake_tmux_dir, exist_ok=True)
            fake_tmux = os.path.join(fake_tmux_dir, 'tmux')
            tmux_log = os.path.join(temp_dir, 'tmux_og.log')
            with open(fake_tmux, 'w') as f:
                f.write(f'#!/bin/sh\necho "fake tmux called with: $@" >> {tmux_log}\n')
                f.write('if echo "$@" | grep -q "has-session"; then\n')
                f.write('  exit 1\n')
                f.write('fi\n')
                f.write('exit 0\n')
            os.chmod(fake_tmux, 0o755)
            
            env = os.environ.copy()
            env['HOME'] = temp_dir
            env['PATH'] = fake_tmux_dir + os.pathsep + env['PATH']
            
            # Run wts outside repo
            subprocess.run([sys.executable, WTS_SCRIPT, session_name], cwd=temp_dir, env=env, check=True)
            
            # Verify tmux called with simple session name
            with open(tmux_log, 'r') as f:
                content = f.read()
                self.assertIn(f"new-session -d -s {session_name}", content)
                self.assertIn(f"-c {os.path.realpath(temp_dir)}", content)

if __name__ == '__main__':
    # Verify dependencies
    if shutil.which('tmux') is None:
        print("Skipping wts tests: tmux not found")
        sys.exit(0)
    if shutil.which('git') is None:
        print("Skipping wts tests: git not found")
        sys.exit(0)
        
    unittest.main()
