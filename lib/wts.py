import subprocess
import os
import sys
import shlex
from pathlib import Path
from lib.utils import run_command

class WtsManager:
    """Manages git worktrees and tmux sessions."""
    
    def __init__(self, name=None, no_worktree=False, attach=False):
        self.name = name
        self.no_worktree = no_worktree
        self.attach = attach
        self.user = os.environ.get('USER', '').lower()
        self.repo_root = None
        self.repo_name = None
        self.in_git = False
        self.branch_name = name
        self.full_branch_name = None
        self.session_name = None
        self.target_dir = Path.cwd()
        
        self._detect_git()
        self._setup_names()

    def _detect_git(self):
        """Detects if we are inside a git repository and sets repo info."""
        try:
            res = run_command(['git', 'rev-parse', '--git-common-dir'], capture_output=True, check=False)
            if res and res.returncode == 0:
                common_dir = os.path.abspath(res.stdout.strip())
                if common_dir.endswith('/.git'):
                    self.repo_root = os.path.dirname(common_dir)
                else:
                    self.repo_root = common_dir
                self.in_git = True
                self.repo_name = os.path.basename(self.repo_root)
        except Exception:
            self.in_git = False

    def _setup_names(self):
        """Sets up session and branch names based on git state."""
        if not self.in_git:
            if not self.name:
                self.name = os.path.basename(os.getcwd())
            self.session_name = self.name
            self.branch_name = self.name
            return

        # In git
        if self.no_worktree:
            self.session_name = self.name or self.repo_name
            self.target_dir = Path(self.repo_root)
            return

        if not self.branch_name:
            res = run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True)
            self.branch_name = res.stdout.strip()

        # Prefix format: {user}/{repo}-{branch}
        prefix = f"{self.user}/{self.repo_name}-"
        if self.user and self.branch_name.startswith(prefix):
            self.session_name = self.branch_name[len(prefix):]
        else:
            self.session_name = self.branch_name

        self.full_branch_name = self.branch_name
        if self.user and not self.branch_name.startswith(f"{self.user}/"):
            self.full_branch_name = f"{self.user}/{self.repo_name}-{self.branch_name}"

    def create_session(self):
        """Creates or attaches to a session."""
        if self.attach:
            self._attach()
            return

        if self.in_git and not self.no_worktree:
            self.target_dir = Path.home() / "worktrees" / self.repo_name / self.branch_name
            self._ensure_worktree()

        self._ensure_tmux_session()
        self._switch()

    def _attach(self):
        """Attaches to an existing session."""
        res = subprocess.run(['tmux', 'has-session', '-t', f'={self.session_name}'], capture_output=True)
        if res.returncode == 0:
            self._switch()
        else:
            sys.exit(0)

    def _ensure_worktree(self):
        """Ensures the git worktree exists."""
        if self.target_dir.exists():
            return

        self.target_dir.parent.mkdir(parents=True, exist_ok=True)
        
        target_branch = self.full_branch_name
        # Check if the fully prefixed branch exists
        if subprocess.run(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{self.full_branch_name}']).returncode != 0:
            # Check for the unprefixed branch (backward compatibility)
            if subprocess.run(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{self.branch_name}']).returncode == 0:
                target_branch = self.branch_name
            else:
                try:
                    create = input(f"Branch '{self.full_branch_name}' does not exist. Create it? (y/n) ")
                    if create.lower() == 'y':
                        run_command(['git', 'branch', self.full_branch_name])
                        target_branch = self.full_branch_name
                    else:
                        print("Aborting.")
                        sys.exit(0)
                except (EOFError, KeyboardInterrupt):
                    print("\nAborting.")
                    sys.exit(0)

        print(f"Creating worktree for branch '{target_branch}' at {self.target_dir}...")
        run_command(['git', 'worktree', 'add', str(self.target_dir), target_branch])

    def _ensure_tmux_session(self):
        """Ensures the tmux session exists with the desired layout."""
        res = subprocess.run(['tmux', 'has-session', '-t', f'={self.session_name}'], capture_output=True)
        if res.returncode == 0:
            return

        print(f"Creating new tmux session '{self.session_name}'...")
        run_command(['tmux', 'new-session', '-d', '-s', self.session_name, '-c', str(self.target_dir)])
        
        # Initial layout
        run_command(['tmux', 'rename-window', '-t', f'{self.session_name}:0', 'Agent'])
        run_command(['tmux', 'split-window', '-h', '-t', f'{self.session_name}:0', '-c', str(self.target_dir)])
        run_command(['tmux', 'send-keys', '-t', f'{self.session_name}:0.1', 'nvim .', 'Enter'])
        
        agent_cmd = os.environ.get('WTS_AGENT_CMD')
        if agent_cmd:
            run_command(['tmux', 'send-keys', '-t', f'{self.session_name}:0.0', agent_cmd, 'Enter'])
        
        run_command(['tmux', 'select-pane', '-t', f'{self.session_name}:0.0'])

    def _switch(self):
        """Switches the current client to the session."""
        if 'TMUX' in os.environ:
            run_command(['tmux', 'refresh-client', '-S'])
            os.execvp('tmux', ['tmux', 'switch-client', '-t', self.session_name])
        else:
            os.execvp('tmux', ['tmux', 'attach-session', '-t', self.session_name])

    @staticmethod
    def cleanup_session():
        """Cleans up the current worktree and tmux session."""
        if 'TMUX' not in os.environ:
            print("Error: Must be run inside a tmux session.", file=sys.stderr)
            sys.exit(1)

        # Get current session name
        res = run_command(['tmux', 'display-message', '-p', '#S'], capture_output=True)
        session_name = res.stdout.strip() if res else None
        if not session_name:
            print("Error: Could not determine current tmux session name.", file=sys.stderr)
            sys.exit(1)

        # Detect git and worktree info
        worktree_path = None
        main_repo = "."
        should_remove_worktree = False

        try:
            res = run_command(['git', 'rev-parse', '--is-inside-work-tree'], capture_output=True, check=False)
            if res and res.returncode == 0:
                # Check for uncommitted changes
                status = run_command(['git', 'status', '--porcelain'], capture_output=True)
                if status and status.stdout.strip():
                    print("Error: Uncommitted changes present. Please commit or stash first.", file=sys.stderr)
                    sys.exit(1)
                
                # Get paths
                res = run_command(['git', 'rev-parse', '--show-toplevel'], capture_output=True)
                worktree_path = Path(res.stdout.strip()) if res else None
                
                res = run_command(['git', 'rev-parse', '--git-common-dir'], capture_output=True)
                if res:
                    common_dir = os.path.abspath(res.stdout.strip())
                    main_repo = os.path.dirname(common_dir) if common_dir.endswith('/.git') else common_dir

                # Determine if we should remove the worktree (only if in ~/worktrees)
                if worktree_path:
                    try:
                        worktree_path.relative_to(Path.home() / "worktrees")
                        should_remove_worktree = True
                    except ValueError:
                        should_remove_worktree = False
        except Exception:
            pass

        # Construct cleanup command
        quoted_session = shlex.quote(session_name)
        if should_remove_worktree:
            quoted_path = shlex.quote(str(worktree_path))
            quoted_main_repo = shlex.quote(main_repo)
            print(f"Cleaning up session '{session_name}' and worktree '{worktree_path}'...")
            cleanup_cmd = f"cd / && git -C {quoted_main_repo} worktree remove --force {quoted_path}; tmux kill-session -t {quoted_session}"
        else:
            print(f"Cleaning up session '{session_name}'...")
            cleanup_cmd = f"cd / && tmux kill-session -t {quoted_session}"

        # Run cleanup on the server
        run_command(['tmux', 'run-shell', '-b', f"{cleanup_cmd}; tmux refresh-client -S"])

# Compatibility wrappers
def create_session(args):
    manager = WtsManager(name=args.name, no_worktree=args.no_worktree, attach=args.attach)
    manager.create_session()

def cleanup_session():
    WtsManager.cleanup_session()
