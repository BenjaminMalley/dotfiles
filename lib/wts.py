import subprocess
import os
import sys
import shlex
from pathlib import Path
from lib.utils import run_command

def cleanup_session():
    """Cleans up the current worktree and tmux session."""
    if 'TMUX' not in os.environ:
        print("Error: Must be run inside a tmux session.", file=sys.stderr)
        sys.exit(1)

    # Check for uncommitted changes
    try:
        run_command(['git', 'rev-parse', '--is-inside-work-tree'], capture_output=True)
        in_git = True
    except Exception:
        in_git = False

    if in_git:
        status_result = run_command(['git', 'status', '--porcelain'], capture_output=True)
        if status_result and status_result.stdout.strip():
            print("Error: Uncommitted changes or untracked files present. Please commit or stash them first.", file=sys.stderr)
            sys.exit(1)
        
        # Get worktree path
        worktree_path_res = run_command(['git', 'rev-parse', '--show-toplevel'], capture_output=True)
        worktree_path = Path(worktree_path_res.stdout.strip()) if worktree_path_res else None
    else:
        worktree_path = None

    # Get current session name
    session_res = run_command(['tmux', 'display-message', '-p', '#S'], capture_output=True)
    session_name = session_res.stdout.strip() if session_res else None

    if not session_name:
        print("Error: Could not determine current tmux session name.", file=sys.stderr)
        sys.exit(1)

    # Determine if we should remove the worktree
    should_remove_worktree = False
    if worktree_path:
        home_worktrees = Path.home() / "worktrees"
        try:
            worktree_path.relative_to(home_worktrees)
            should_remove_worktree = True
        except ValueError:
            should_remove_worktree = False

    # Construct the cleanup command
    # We use ; instead of && to ensure the session is killed even if worktree removal has issues.
    # We use --force to handle untracked/ignored files.
    # We use git -C to ensure we have the right context even if we cd / to unlock the directory.
    quoted_session = shlex.quote(session_name)
    if should_remove_worktree:
        quoted_path = shlex.quote(str(worktree_path))
        # Get the main repo path to use with -C
        common_dir_res = run_command(['git', 'rev-parse', '--git-common-dir'], capture_output=True)
        main_repo = os.path.dirname(os.path.abspath(common_dir_res.stdout.strip())) if common_dir_res else "."
        quoted_main_repo = shlex.quote(main_repo)
        
        print(f"Cleaning up session '{session_name}' and worktree '{worktree_path}'...")
        cleanup_cmd = f"cd / && git -C {quoted_main_repo} worktree remove --force {quoted_path}; tmux kill-session -t {quoted_session}"
    else:
        print(f"Cleaning up session '{session_name}'...")
        cleanup_cmd = f"cd / && tmux kill-session -t {quoted_session}"

    # Switch client first to avoid being attached to a session that is about to be killed
    ret = subprocess.run(['tmux', 'switch-client', '-l'], capture_output=True)
    if ret.returncode != 0:
        subprocess.run(['tmux', 'detach-client'], capture_output=True)
    
    # Queue the cleanup on the tmux server
    run_command(['tmux', 'run-shell', '-b', cleanup_cmd])

def create_session(args):
    """Core logic to create or attach to a worktree/tmux session."""
    branch_name = args.name

    # Check if we are in a git repository
    try:
        run_command(['git', 'rev-parse', '--is-inside-work-tree'], capture_output=True)
        in_git = True
    except Exception:
        in_git = False

    session_name = None
    target_dir = None

    user_prefix = os.environ.get('USER', '').lower()

    if in_git:
        # Get the real repository root, even if we are in a worktree
        common_dir_res = run_command(['git', 'rev-parse', '--git-common-dir'], capture_output=True)
        if common_dir_res:
            common_dir = os.path.abspath(common_dir_res.stdout.strip())
            # If common_dir is just ".git", we are in the main repo. 
            # If it's an absolute path ending in .git, we want its parent.
            if common_dir.endswith('/.git'):
                repo_toplevel = os.path.dirname(common_dir)
            else:
                # In some cases git-common-dir might be the repo root itself if not a .git dir
                repo_toplevel = common_dir
        else:
            repo_toplevel_res = run_command(['git', 'rev-parse', '--show-toplevel'], capture_output=True)
            repo_toplevel = repo_toplevel_res.stdout.strip()
            
        repo_name = os.path.basename(repo_toplevel)

        if args.no_worktree:
            session_name = branch_name or repo_name
        else:
            if not branch_name:
                branch_name_res = run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True)
                branch_name = branch_name_res.stdout.strip()
                
            # If the branch name already has the expected prefix, strip it for the session name
            # Prefix format: {user}/{repo}-{branch}
            prefix = f"{user_prefix}/{repo_name}-"
            if user_prefix and branch_name.startswith(prefix):
                session_name = branch_name[len(prefix):]
            else:
                session_name = branch_name

            full_branch_name = branch_name
            if user_prefix and not branch_name.startswith(f"{user_prefix}/"):
                full_branch_name = f"{user_prefix}/{repo_name}-{branch_name}"
            
        target_dir = Path(repo_toplevel)
    else:
        if not branch_name:
            branch_name = os.path.basename(os.getcwd())
        session_name = branch_name
        target_dir = Path.cwd()
        full_branch_name = branch_name

    if args.attach:
        session_exists_res = subprocess.run(['tmux', 'has-session', '-t', f'={session_name}'], capture_output=True)
        if session_exists_res.returncode == 0:
            if 'TMUX' in os.environ:
                os.execvp('tmux', ['tmux', 'switch-client', '-t', session_name])
            else:
                os.execvp('tmux', ['tmux', 'attach-session', '-t', session_name])
        else:
            sys.exit(0)

    # Handle worktree creation
    if in_git and not args.no_worktree:
        worktree_path = Path.home() / "worktrees" / repo_name / branch_name
        target_dir = worktree_path

        if not worktree_path.exists():
            worktree_path.parent.mkdir(parents=True, exist_ok=True)
            
            branch_exists = False
            target_branch = full_branch_name
            
            # Check for the fully prefixed branch first
            if subprocess.run(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{full_branch_name}']).returncode == 0:
                branch_exists = True
            # Then check for the unprefixed branch (backward compatibility)
            elif subprocess.run(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch_name}']).returncode == 0:
                branch_exists = True
                target_branch = branch_name

            if not branch_exists:
                try:
                    create_branch = input(f"Branch '{full_branch_name}' does not exist. Create it? (y/n) ")
                    if create_branch.lower() == 'y':
                        run_command(['git', 'branch', full_branch_name])
                        target_branch = full_branch_name
                    else:
                        print("Aborting.")
                        sys.exit(0)
                except (EOFError, KeyboardInterrupt):
                    print("\nAborting.")
                    sys.exit(0)

            print(f"Creating worktree for branch '{target_branch}' at {worktree_path}...")
            run_command(['git', 'worktree', 'add', str(worktree_path), target_branch])
    
    # Finalize tmux session
    session_exists_res = subprocess.run(['tmux', 'has-session', '-t', f'={session_name}'], capture_output=True)

    if session_exists_res.returncode != 0:
        print(f"Creating new tmux session '{session_name}'...")
        run_command(['tmux', 'new-session', '-d', '-s', session_name, '-c', str(target_dir)])
        
        # Layout
        run_command(['tmux', 'rename-window', '-t', f'{session_name}:0', 'Agent'])
        run_command(['tmux', 'split-window', '-h', '-t', f'{session_name}:0', '-c', str(target_dir)])
        run_command(['tmux', 'send-keys', '-t', f'{session_name}:0.1', 'nvim .', 'Enter'])
        
        agent_cmd = os.environ.get('WTS_AGENT_CMD')
        if agent_cmd:
            run_command(['tmux', 'send-keys', '-t', f'{session_name}:0.0', agent_cmd, 'Enter'])
        
        run_command(['tmux', 'select-pane', '-t', f'{session_name}:0.0'])

    if 'TMUX' in os.environ:
        os.execvp('tmux', ['tmux', 'switch-client', '-t', session_name])
    else:
        os.execvp('tmux', ['tmux', 'attach-session', '-t', session_name])
