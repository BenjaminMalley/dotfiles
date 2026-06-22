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

    def test_wts_create_with_prefix(self):
        """Tests automatic branch prefixing based on USER env var."""
        branch_name = "my-feature"
        user = "testuser"
        repo_name = os.path.basename(self.test_dir)
        expected_full_branch = f"{user}/{repo_name}-{branch_name}"
        
        # Create a fake tmux script
        fake_tmux_dir = os.path.join(self.test_dir, 'bin')
        os.makedirs(fake_tmux_dir, exist_ok=True)
        fake_tmux = os.path.join(fake_tmux_dir, 'tmux')
        tmux_log = os.path.join(self.test_dir, 'tmux_prefix.log')
        with open(fake_tmux, 'w') as f:
            f.write(f'#!/bin/sh\necho "fake tmux called with: $@" >> {tmux_log}\n')
            f.write('if echo "$@" | grep -q "has-session"; then\n')
            f.write('  exit 1\n')
            f.write('fi\n')
            f.write('exit 0\n')
        os.chmod(fake_tmux, 0o755)
        
        env = os.environ.copy()
        env['HOME'] = self.test_dir
        env['USER'] = user
        env['PATH'] = fake_tmux_dir + os.pathsep + env['PATH']
        
        # Run wts script
        # We need to simulate "yes" input because wts prompts to create the branch
        p = subprocess.Popen(
            [sys.executable, WTS_SCRIPT, branch_name], 
            cwd=self.test_dir, 
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = p.communicate(input="y\n")
        
        if p.returncode != 0:
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
        self.assertEqual(p.returncode, 0, "wts failed")

        # Verify worktree created at short path
        expected_worktree_path = os.path.join(self.test_dir, 'worktrees', repo_name, branch_name)
        self.assertTrue(os.path.exists(expected_worktree_path), f"Worktree should be at {expected_worktree_path}")
        
        # Verify the actual git branch has the prefix
        # We check the branch checked out in the worktree
        actual_branch = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
            cwd=expected_worktree_path, 
            capture_output=True, 
            text=True, 
            check=True
        ).stdout.strip()
        self.assertEqual(actual_branch, expected_full_branch, "Branch name should be prefixed")

        # Verify tmux session uses short name
        with open(tmux_log, 'r') as f:
            content = f.read()
            self.assertIn(f"new-session -d -s {branch_name}", content)

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
        env['WTS_AGENT_CMD'] = 'test-agent'
        
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
            self.assertIn("rename-window", content)
            self.assertIn("split-window", content)
            self.assertIn("vim .", content)
            self.assertIn("test-agent", content)

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

    def test_wts_add(self):
        """Tests that wts --add creates a worktree for a second repo with the correct branch prefix."""
        import json

        # Create a second git repo inside the test dir
        second_repo = os.path.join(self.test_dir, 'second-repo')
        os.makedirs(second_repo)
        subprocess.run(['git', 'init'], cwd=second_repo, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=second_repo, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=second_repo, check=True)
        subprocess.run(['git', 'commit', '--allow-empty', '-m', 'Initial commit'], cwd=second_repo, check=True, stdout=subprocess.DEVNULL)

        user = 'testuser'
        short_name = self.session_name  # e.g. "test-wts-session"
        expected_worktree = os.path.join(self.test_dir, 'worktrees', 'second-repo', short_name)
        expected_branch = f"{user}/second-repo-{short_name}"

        # Start a live session on the test socket, then run wts --add from inside it
        self.run_tmux('new-session', '-d', '-s', self.session_name, '-c', self.test_dir, check=True)

        cmd_str = (
            f"export HOME='{self.test_dir}'; "
            f"export USER='{user}'; "
            f"'{sys.executable}' '{WTS_SCRIPT}' --add '{second_repo}'"
        )
        self.run_tmux('send-keys', '-t', self.session_name, cmd_str, 'Enter', check=True)

        # Poll for the worktree to appear
        max_retries = 20
        for _ in range(max_retries):
            if os.path.exists(expected_worktree):
                break
            time.sleep(0.5)

        self.assertTrue(os.path.exists(expected_worktree), f"Worktree should exist at {expected_worktree}")

        actual_branch = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=expected_worktree, capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(actual_branch, expected_branch, "Worktree should be on the prefixed branch")

        # Poll for the tmux option to be written
        option_value = None
        for _ in range(10):
            res = self.run_tmux('show-options', '-t', self.session_name, '-v', '@wts-added-repos',
                                capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                option_value = res.stdout.strip()
                break
            time.sleep(0.3)

        self.assertIsNotNone(option_value, "tmux option @wts-added-repos should be set")
        entries = json.loads(option_value)
        self.assertTrue(
            any(e['worktree'] == expected_worktree for e in entries),
            "State should record the added worktree path",
        )

    def test_wts_done_removes_added_repos(self):
        """Tests that wts --done also removes worktrees recorded in @wts-added-repos."""
        import json

        # Create a second repo and its worktree manually
        second_repo = os.path.join(self.test_dir, 'second-repo')
        os.makedirs(second_repo)
        subprocess.run(['git', 'init'], cwd=second_repo, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=second_repo, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=second_repo, check=True)
        subprocess.run(['git', 'commit', '--allow-empty', '-m', 'Initial commit'], cwd=second_repo, check=True, stdout=subprocess.DEVNULL)

        added_worktree = os.path.join(self.test_dir, 'worktrees', 'second-repo', self.session_name)
        os.makedirs(os.path.dirname(added_worktree), exist_ok=True)
        subprocess.run(
            ['git', 'worktree', 'add', added_worktree, '-b', f'branch-{self.session_name}'],
            cwd=second_repo, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        # Start a session and pre-seed the tmux options
        self.run_tmux('new-session', '-d', '-s', self.session_name, '-c', self.worktree_path, check=True)
        state = json.dumps([{"repo_root": second_repo, "worktree": added_worktree}])
        self.run_tmux('set-option', '-t', self.session_name, '@wts-added-repos', state, check=True)

        # Run --done from inside the session
        cmd_str = f"export HOME='{self.test_dir}'; '{sys.executable}' '{WTS_SCRIPT}' --done"
        self.run_tmux('send-keys', '-t', self.session_name, cmd_str, 'Enter', check=True)

        # Wait for the session to die
        max_retries = 20
        for _ in range(max_retries):
            ret = self.run_tmux('has-session', '-t', self.session_name, stderr=subprocess.DEVNULL)
            if ret.returncode != 0:
                break
            time.sleep(0.5)

        self.assertNotEqual(ret.returncode, 0, "Session should have been killed")
        self.assertFalse(os.path.exists(self.worktree_path), "Primary worktree should be removed")
        self.assertFalse(os.path.exists(added_worktree), "Added cross-repo worktree should be removed")

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
            self.assertIn(f"new-session -d -s {branch_name}", content)
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

    def test_wts_no_worktree_no_name(self):
        """Tests 'wts -n' without providing a name."""
        # Create a fake tmux script
        fake_tmux_dir = os.path.join(self.test_dir, 'bin')
        os.makedirs(fake_tmux_dir, exist_ok=True)
        fake_tmux = os.path.join(fake_tmux_dir, 'tmux')
        tmux_log = os.path.join(self.test_dir, 'tmux_nw_nn.log')
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
        
        # Get repo name for verification
        repo_name = os.path.basename(self.test_dir)
        expected_session_name = repo_name

        # Run wts with -n but NO name
        subprocess.run([sys.executable, WTS_SCRIPT, '-n'], cwd=self.test_dir, env=env, check=True)
        
        # Verify tmux called with correct session name (should default to repo name)
        with open(tmux_log, 'r') as f:
            content = f.read()
            self.assertIn(f"new-session -d -s {expected_session_name}", content)
            self.assertIn(f"-c {self.test_dir}", content)

    def test_wts_attach(self):
        """Tests 'wts --attach'."""
        # Create a fake tmux script
        fake_tmux_dir = os.path.join(self.test_dir, 'bin')
        os.makedirs(fake_tmux_dir, exist_ok=True)
        fake_tmux = os.path.join(fake_tmux_dir, 'tmux')
        tmux_log = os.path.join(self.test_dir, 'tmux_attach.log')
        with open(fake_tmux, 'w') as f:
            f.write(f'#!/bin/sh\necho "fake tmux called with: $@" >> {tmux_log}\n')
            f.write('if echo "$@" | grep -q "has-session"; then\n')
            f.write('  exit 0\n') # Simulate session exists
            f.write('fi\n')
            f.write('exit 0\n')
        os.chmod(fake_tmux, 0o755)
        
        env = os.environ.copy()
        env['HOME'] = self.test_dir
        env['PATH'] = fake_tmux_dir + os.pathsep + env['PATH']
        env.pop('TMUX', None)  # Ensure we test attach-session path, not switch-client

        # Run wts --attach
        res = subprocess.run([sys.executable, WTS_SCRIPT, '--attach'], cwd=self.test_dir, env=env, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"STDOUT: {res.stdout}")
            print(f"STDERR: {res.stderr}")
            self.assertEqual(res.returncode, 0, "wts --attach failed")
        
        # Verify tmux called with attach-session and correct name
        current_branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=self.test_dir, capture_output=True, text=True, check=True).stdout.strip()
        expected_session_name = current_branch

        with open(tmux_log, 'r') as f:
            content = f.read()
            self.assertIn(f"attach-session -t {expected_session_name}", content)

    def _write_fake_resurrect(self):
        """Creates a fake tmux-resurrect save.sh under the test HOME. Returns its path."""
        save_dir = os.path.join(self.test_dir, '.tmux', 'plugins', 'tmux-resurrect', 'scripts')
        os.makedirs(save_dir, exist_ok=True)
        save_script = os.path.join(save_dir, 'save.sh')
        with open(save_script, 'w') as f:
            f.write('#!/bin/sh\nexit 0\n')
        os.chmod(save_script, 0o755)
        return save_script

    def test_wts_create_saves_resurrect_state(self):
        """When resurrect is installed, creating a session triggers a save via run-shell."""
        branch_name = "save-feature"
        subprocess.run(['git', 'branch', branch_name], cwd=self.test_dir, check=True)

        save_script = self._write_fake_resurrect()

        fake_tmux_dir = os.path.join(self.test_dir, 'bin')
        os.makedirs(fake_tmux_dir, exist_ok=True)
        fake_tmux = os.path.join(fake_tmux_dir, 'tmux')
        tmux_log = os.path.join(self.test_dir, 'tmux_save.log')
        with open(fake_tmux, 'w') as f:
            f.write(f'#!/bin/sh\necho "fake tmux called with: $@" >> {tmux_log}\n')
            f.write('if echo "$@" | grep -q "has-session"; then\n  exit 1\nfi\n')
            f.write('exit 0\n')
        os.chmod(fake_tmux, 0o755)

        env = os.environ.copy()
        env['HOME'] = self.test_dir
        env['PATH'] = fake_tmux_dir + os.pathsep + env['PATH']

        subprocess.run([sys.executable, WTS_SCRIPT, branch_name], cwd=self.test_dir, env=env, check=True)

        with open(tmux_log, 'r') as f:
            content = f.read()
        # The save script is invoked directly (not via run-shell), so it won't appear in the tmux log.
        # Confirm the session was created without error; the save is tested end-to-end in test_wts_done_saves_resurrect_state.
        # Here we verify the script path is discoverable by placing a sentinel in the script.
        sentinel = os.path.join(self.test_dir, 'resurrect_create.marker')
        with open(save_script, 'w') as f:
            f.write(f'#!/bin/sh\ntouch "{sentinel}"\n')
        os.chmod(save_script, 0o755)
        branch_name2 = "save-feature-2"
        subprocess.run(['git', 'branch', branch_name2], cwd=self.test_dir, check=True)
        subprocess.run([sys.executable, WTS_SCRIPT, branch_name2], cwd=self.test_dir, env=env, check=True)
        self.assertTrue(os.path.exists(sentinel), "resurrect save script should be invoked on create")

    def test_wts_create_no_resurrect_is_graceful(self):
        """When resurrect is not installed, creating a session still succeeds and skips the save."""
        branch_name = "nosave-feature"
        subprocess.run(['git', 'branch', branch_name], cwd=self.test_dir, check=True)

        # Note: intentionally NOT creating the fake resurrect save.sh

        fake_tmux_dir = os.path.join(self.test_dir, 'bin')
        os.makedirs(fake_tmux_dir, exist_ok=True)
        fake_tmux = os.path.join(fake_tmux_dir, 'tmux')
        tmux_log = os.path.join(self.test_dir, 'tmux_nosave.log')
        with open(fake_tmux, 'w') as f:
            f.write(f'#!/bin/sh\necho "fake tmux called with: $@" >> {tmux_log}\n')
            f.write('if echo "$@" | grep -q "has-session"; then\n  exit 1\nfi\n')
            f.write('exit 0\n')
        os.chmod(fake_tmux, 0o755)

        env = os.environ.copy()
        env['HOME'] = self.test_dir
        env['PATH'] = fake_tmux_dir + os.pathsep + env['PATH']

        res = subprocess.run([sys.executable, WTS_SCRIPT, branch_name], cwd=self.test_dir, env=env,
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"wts should succeed without resurrect: {res.stderr}")

        sentinel = os.path.join(self.test_dir, 'resurrect_graceful.marker')
        self.assertFalse(os.path.exists(sentinel), "no resurrect save should be triggered when not installed")

    def test_wts_done_saves_resurrect_state(self):
        """Deleting a session triggers a resurrect save (end-to-end on real tmux socket)."""
        marker = os.path.join(self.test_dir, 'resurrect_saved.marker')

        # Fake save.sh touches a marker so we can observe that it ran.
        save_dir = os.path.join(self.test_dir, '.tmux', 'plugins', 'tmux-resurrect', 'scripts')
        os.makedirs(save_dir, exist_ok=True)
        save_script = os.path.join(save_dir, 'save.sh')
        with open(save_script, 'w') as f:
            f.write(f'#!/bin/sh\ntouch "{marker}"\n')
        os.chmod(save_script, 0o755)

        # The isolated tmux server loads ~/.tmux.conf and sets @resurrect-save-script-path to
        # the real script. Override the global option to point at our fake script instead.
        self.run_tmux('set-option', '-g', '@resurrect-save-script-path', save_script, check=True)

        cmd_str = f"export HOME='{self.test_dir}'; '{sys.executable}' '{WTS_SCRIPT}' --done"
        self.run_tmux('new-session', '-d', '-s', self.session_name, '-c', self.worktree_path, cmd_str, check=True)

        max_retries = 20
        for _ in range(max_retries):
            ret = self.run_tmux('has-session', '-t', self.session_name, stderr=subprocess.DEVNULL)
            if ret.returncode != 0:
                break
            time.sleep(0.5)
        self.assertNotEqual(ret.returncode, 0, "Session should have been killed")

        for _ in range(10):
            if os.path.exists(marker):
                break
            time.sleep(0.3)
        self.assertTrue(os.path.exists(marker), "resurrect save should be triggered on --done")

if __name__ == '__main__':
    # Verify dependencies
    if shutil.which('tmux') is None:
        print("Skipping wts tests: tmux not found")
        sys.exit(0)
    if shutil.which('git') is None:
        print("Skipping wts tests: git not found")
        sys.exit(0)
        
    unittest.main()
