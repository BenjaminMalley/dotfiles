import os
import shutil
import argparse
import platform
from macos_settings import set_macos_preferences
from lib.utils import run_command, symlink_resource, get_repo_root, is_darwin

def symlink_agent_files():
    """Symlinks each agent file to the ~/.claude/agents directory."""
    repo_root = get_repo_root()
    agents_dir = os.path.join(repo_root, 'agents')
    
    if not os.path.isdir(agents_dir):
        print(f"Warning: {agents_dir} not found. Skipping agent symlinking.")
        return

    for filename in os.listdir(agents_dir):
        source_rel = os.path.join('agents', filename)
        dest_rel = os.path.join('.claude', 'agents', filename)
        symlink_resource(source_rel, dest_rel)

def symlink_scripts():
    """Symlinks the scripts directory to ~/.gemini/scripts and ~/.claude/scripts."""
    for tool in ['.gemini', '.claude']:
        dest_rel = os.path.join(tool, 'scripts')
        symlink_resource('scripts', dest_rel)

def install_dotfiles(args):
    """Installs dotfiles and software."""
    print("Starting bootstrap process...")

    repo_root = get_repo_root()

    if is_darwin():
        print("Detected macOS. Installing Homebrew and software...")
        if not shutil.which('brew'):
            print("Homebrew not found. Installing Homebrew...")
            run_command(['/bin/bash', '-c', '$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/LATEST/install.sh)'])
        else:
            print("Homebrew is already installed. Updating...")
            run_command(['brew', 'update'])

        brewfile = os.path.join(repo_root, 'Brewfile')
        if os.path.exists(brewfile):
            print("Installing software from Brewfile...")
            run_command(['brew', 'bundle', f'--file={brewfile}'])

        brewfile_opt = os.path.join(repo_root, 'Brewfile.opt')
        if os.path.exists(brewfile_opt) and not args.skip_optional:
            process_optional_software(brewfile_opt, args.yes)

        set_macos_preferences()
    else:
        print("Not on MacOS. Skipping homebrew and macOS settings installation.")

    print("Symlinking dotfiles...")
    DOTFILES = [
        ('gitconfig', '.gitconfig'),
        ('.zshrc', '.zshrc'),
        ('.tmux.conf', '.tmux.conf'),
        ('.vimrc', '.vimrc'),
        ('nvim', '.config/nvim'),
        ('ghostty/config', '.config/ghostty/config'),
        ('gemini-settings.json', '.gemini/settings.json'),
        ('claude-settings.json', '.claude/settings.json'),
        ('AGENT.md', '.gemini/GEMINI.md'),
        ('AGENT.md', '.claude/CLAUDE.md'),
    ]

    for source, dest in DOTFILES:
        symlink_resource(source, dest)

    symlink_agent_files()
    symlink_scripts()

    reload_tmux()

def process_optional_software(brewfile_opt, auto_yes):
    """Handles installation of optional software from Brewfile.opt."""
    with open(brewfile_opt, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            if len(parts) != 2:
                continue

            cmd_type, package = parts[0], parts[1].strip('"')
            
            if not auto_yes:
                response = input(f"Do you want to install optional software '{package}'? (y/n) ")
                if response.lower() != 'y':
                    continue
            
            print(f"Installing {package}...")
            if cmd_type == 'cask':
                run_command(['brew', 'install', '--cask', package])
            else:
                run_command(['brew', 'install', package])

def reload_tmux():
    """Reloads tmux configuration if tmux is running."""
    print("Reloading tmux configuration...")
    tmux_cleanup = (
        'if tmux info &>/dev/null; then '
        'tmux set-hook -ug client-attached; '
        'tmux set-hook -ug pane-focus-in; '
        'tmux set-option -g status-right ""; '
        'tmux source-file ~/.tmux.conf; '
        'echo "Tmux config reloaded."; '
        'else echo "Tmux not running, skipping reload."; fi'
    )
    run_command(['/bin/bash', '-c', tmux_cleanup], check=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Install dotfiles and software.")
    parser.add_argument('--skip-optional', action='store_true', help="Skip optional software installation.")
    parser.add_argument('--yes', '-y', action='store_true', help="Answer yes to all prompts.")
    args = parser.parse_args()
    
    install_dotfiles(args)
