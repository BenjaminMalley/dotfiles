import unittest
import os
import shutil
import subprocess
import time
import sys

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

        # Create worktree
        self.worktree_path = os.path.join(self.test_dir, 'feature-branch')
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

    def test_wts_done(self):
        # Start tmux session running the wts command directly
        # This avoids shell startup scripts (like airchat) interfering
        cmd_str = f"'{sys.executable}' '{WTS_SCRIPT}' --done"
        
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

if __name__ == '__main__':
    # Verify dependencies
    if shutil.which('tmux') is None:
        print("Skipping wts tests: tmux not found")
        sys.exit(0)
    if shutil.which('git') is None:
        print("Skipping wts tests: git not found")
        sys.exit(0)
        
    unittest.main()
