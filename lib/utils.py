import subprocess
import os
import sys
import shutil
import platform

def run_command(command, check=True, capture_output=False, text=True):
    """
    Unified wrapper for subprocess.run.
    Returns the result object.
    """
    try:
        return subprocess.run(command, check=check, capture_output=capture_output, text=text)
    except FileNotFoundError:
        print(f"Warning: Command '{command[0]}' not found. Skipping.", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        if check:
            raise e
        else:
            print(f"Warning: Command '{' '.join(command)}' failed with error: {e}", file=sys.stderr)
            return e

def symlink_resource(source_relative_path, destination_path_from_home):
    """
    Creates a symlink from source_relative_path (relative to repo root)
    to destination_path_from_home (relative to $HOME).
    Handles backups of existing files.
    """
    home_dir = os.environ.get('HOME', '')
    repo_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    
    source_path = os.path.join(repo_root, source_relative_path)
    destination_path = os.path.join(home_dir, destination_path_from_home)
    
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    
    if os.path.islink(destination_path):
        os.remove(destination_path)
    elif os.path.exists(destination_path):
        backup_path = f"{destination_path}.bak"
        print(f"Warning: {destination_path} exists and is not a symlink. Backing up to {backup_path}")
        shutil.move(destination_path, backup_path)
        
    os.symlink(source_path, destination_path)
    print(f"Symlinked: {source_relative_path} -> ~/{destination_path_from_home}")

def get_repo_root():
    """Returns the absolute path to the repository root."""
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def is_darwin():
    """Returns True if the current system is macOS."""
    return platform.system() == 'Darwin'
