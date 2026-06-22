import subprocess
import os
import signal
import sys
import json
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

        self.full_branch_name = self._prefixed_branch(self.user, self.repo_name, self.branch_name)

    def create_session(self):
        """Creates or attaches to a session."""
        if self.attach:
            self._attach()
            return

        if self.in_git and not self.no_worktree:
            self.target_dir = Path.home() / "worktrees" / self.repo_name / self.branch_name
            run_command(['git', '-C', self.repo_root, 'rst'], check=False)
            self._ensure_worktree()

        created = self._ensure_tmux_session()
        if created:
            self._save_resurrect_state()
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
        """Ensures the tmux session exists. Returns True if a new session was created."""
        res = subprocess.run(['tmux', 'has-session', '-t', f'={self.session_name}'], capture_output=True)
        if res.returncode == 0:
            return False

        print(f"Creating new tmux session '{self.session_name}'...")
        run_command(['tmux', 'new-session', '-d', '-s', self.session_name, '-c', str(self.target_dir)])

        # Initial layout
        run_command(['tmux', 'rename-window', '-t', f'{self.session_name}:0', 'Agent'])
        run_command(['tmux', 'select-pane', '-t', f'{self.session_name}:0.0', '-T', 'Agent'])
        run_command(['tmux', 'split-window', '-h', '-t', f'{self.session_name}:0', '-c', str(self.target_dir)])
        run_command(['tmux', 'select-pane', '-t', f'{self.session_name}:0.1', '-T', 'Editor'])
        run_command(['tmux', 'send-keys', '-t', f'{self.session_name}:0.1', 'nvim .', 'Enter'])

        agent_cmd = os.environ.get('WTS_AGENT_CMD')
        if agent_cmd:
            run_command(['tmux', 'send-keys', '-t', f'{self.session_name}:0.0', agent_cmd, 'Enter'])

        run_command(['tmux', 'select-pane', '-t', f'{self.session_name}:0.0'])
        return True

    def _switch(self):
        """Switches the current client to the session."""
        if 'TMUX' in os.environ:
            run_command(['tmux', 'refresh-client', '-S'])
            os.execvp('tmux', ['tmux', 'switch-client', '-t', self.session_name])
        else:
            os.execvp('tmux', ['tmux', 'attach-session', '-t', self.session_name])

    # ------------------------------------------------------------------
    # Helpers shared between create and --add flows
    # ------------------------------------------------------------------

    @staticmethod
    def _prefixed_branch(user, repo_name, short_name):
        """Returns the fully-prefixed branch name for a given repo and short name."""
        if user and not short_name.startswith(f"{user}/"):
            return f"{user}/{repo_name}-{short_name}"
        return short_name

    @staticmethod
    def _create_worktree(repo_root, worktree_path, full_branch, short_branch):
        """Creates a worktree for repo_root at worktree_path, non-interactively.

        Prefers full_branch (prefixed), falls back to short_branch for backward
        compatibility, and creates full_branch from HEAD if neither exists.
        """
        if worktree_path.exists():
            return

        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        def _branch_exists(branch):
            res = run_command(
                ['git', '-C', str(repo_root), 'show-ref', '--verify', '--quiet',
                 f'refs/heads/{branch}'],
                check=False,
            )
            return res is not None and res.returncode == 0

        if _branch_exists(full_branch):
            target = full_branch
        elif _branch_exists(short_branch):
            target = short_branch
        else:
            run_command(['git', '-C', str(repo_root), 'branch', full_branch])
            target = full_branch

        print(f"Creating worktree for branch '{target}' at {worktree_path}...")
        run_command(['git', '-C', str(repo_root), 'worktree', 'add', str(worktree_path), target])

    # ------------------------------------------------------------------
    # tmux-resurrect integration
    # ------------------------------------------------------------------

    @staticmethod
    def _resurrect_save_script():
        """Returns the path to the resurrect save.sh if installed, else None."""
        # Try the tmux option the plugin sets at load time
        res = subprocess.run(
            ['tmux', 'show-options', '-gv', '@resurrect-save-script-path'],
            capture_output=True, text=True,
        )
        if res.returncode == 0 and res.stdout.strip():
            path = Path(res.stdout.strip())
            if path.exists():
                return path
        # Fallback to the default TPM install location
        fallback = Path.home() / '.tmux' / 'plugins' / 'tmux-resurrect' / 'scripts' / 'save.sh'
        return fallback if fallback.exists() else None

    @staticmethod
    def _save_resurrect_state():
        """Triggers a tmux-resurrect save; silently skips if not installed."""
        script = WtsManager._resurrect_save_script()
        if not script:
            return
        subprocess.run(
            [str(script)],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    # ------------------------------------------------------------------
    # tmux option helpers for tracking cross-repo worktrees
    # ------------------------------------------------------------------

    _TMUX_OPTION = '@wts-added-repos'

    @staticmethod
    def _get_added_repos(session_name):
        """Returns the list of added-repo entries for session_name from the tmux option."""
        res = subprocess.run(
            ['tmux', 'show-options', '-t', session_name, '-v', WtsManager._TMUX_OPTION],
            capture_output=True, text=True,
        )
        if res.returncode != 0 or not res.stdout.strip():
            return []
        try:
            return json.loads(res.stdout.strip())
        except Exception:
            return []

    @staticmethod
    def _set_added_repos(session_name, entries):
        """Persists entries as a tmux option on session_name."""
        subprocess.run(
            ['tmux', 'set-option', '-t', session_name, WtsManager._TMUX_OPTION, json.dumps(entries)],
            check=False,
        )

    @staticmethod
    def _record_added_worktree(session_name, repo_root, worktree_path):
        """Appends a cross-repo worktree entry to the session's tmux option (de-duplicated)."""
        entries = WtsManager._get_added_repos(session_name)
        entry = {"repo_root": str(repo_root), "worktree": str(worktree_path)}
        if entry not in entries:
            entries.append(entry)
        WtsManager._set_added_repos(session_name, entries)

    # ------------------------------------------------------------------
    # --add command
    # ------------------------------------------------------------------

    @staticmethod
    def add_session_repo(repo_path_arg):
        """Adds a worktree for another repo to the current tmux session."""
        if 'TMUX' not in os.environ:
            print("Error: Must be run inside a tmux session.", file=sys.stderr)
            sys.exit(1)

        res = run_command(['tmux', 'display-message', '-p', '#S'], capture_output=True)
        short_name = res.stdout.strip() if res else None
        if not short_name:
            print("Error: Could not determine current tmux session name.", file=sys.stderr)
            sys.exit(1)

        repo_path = Path(repo_path_arg).expanduser().resolve()
        res = run_command(
            ['git', '-C', str(repo_path), 'rev-parse', '--git-common-dir'],
            capture_output=True, check=False,
        )
        if not res or res.returncode != 0:
            print(f"Error: '{repo_path}' is not a git repository.", file=sys.stderr)
            sys.exit(1)

        common_dir = res.stdout.strip()
        if not os.path.isabs(common_dir):
            common_dir = os.path.join(str(repo_path), common_dir)
        common_dir = os.path.abspath(common_dir)
        repo_root = Path(os.path.dirname(common_dir) if common_dir.endswith('/.git') else common_dir)
        repo_name = repo_root.name

        user = os.environ.get('USER', '').lower()
        full_branch = WtsManager._prefixed_branch(user, repo_name, short_name)
        worktree = Path.home() / "worktrees" / repo_name / short_name

        run_command(['git', '-C', str(repo_root), 'rst'], check=False)
        WtsManager._create_worktree(repo_root, worktree, full_branch, short_name)
        WtsManager._record_added_worktree(short_name, repo_root, worktree)

        print(worktree)

    # ------------------------------------------------------------------
    # --done command
    # ------------------------------------------------------------------

    @staticmethod
    def cleanup_session():
        """Cleans up the current worktree and tmux session."""
        if 'TMUX' not in os.environ:
            print("Error: Must be run inside a tmux session.", file=sys.stderr)
            sys.exit(1)

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
                res = run_command(['git', 'rev-parse', '--show-toplevel'], capture_output=True)
                worktree_path = Path(res.stdout.strip()) if res else None

                res = run_command(['git', 'rev-parse', '--git-common-dir'], capture_output=True)
                if res:
                    common_dir = os.path.abspath(res.stdout.strip())
                    main_repo = os.path.dirname(common_dir) if common_dir.endswith('/.git') else common_dir

                if worktree_path:
                    try:
                        worktree_path.relative_to(Path.home() / "worktrees")
                        should_remove_worktree = True
                    except ValueError:
                        should_remove_worktree = False
        except Exception:
            pass

        # Read cross-repo entries before switching away (tmux option stays readable until kill)
        added = WtsManager._get_added_repos(session_name)

        # Switch to another session before killing this one
        other = subprocess.run(
            ['tmux', 'display-message', '-p', '#{session_id}'],
            capture_output=True, text=True,
        ).stdout.strip()
        sessions = subprocess.run(
            ['tmux', 'list-sessions', '-F', '#{session_id} #{session_name}'],
            capture_output=True, text=True,
        ).stdout.strip().splitlines()
        next_session = next(
            (parts[1] for line in sessions if (parts := line.split(None, 1)) and parts[0] != other),
            None,
        )
        if next_session:
            subprocess.run(['tmux', 'switch-client', '-t', next_session])
        else:
            subprocess.run(['tmux', 'detach-client'])

        if should_remove_worktree:
            run_command(['git', '-C', main_repo, 'worktree', 'remove', '--force', str(worktree_path)], check=False)

        for entry in added:
            run_command(
                ['git', '-C', entry['repo_root'], 'worktree', 'remove', '--force', entry['worktree']],
                check=False,
            )

        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        subprocess.run(['tmux', 'kill-session', '-t', session_name])
        WtsManager._save_resurrect_state()


# Compatibility wrappers
def create_session(args):
    manager = WtsManager(name=args.name, no_worktree=args.no_worktree, attach=args.attach)
    manager.create_session()

def cleanup_session():
    WtsManager.cleanup_session()

def add_repo(args):
    WtsManager.add_session_repo(args.add)
