import subprocess
import platform
import os
import shutil
import argparse
from macos_settings import set_macos_preferences


def run_command(command, check=True):
    """Runs a command and checks for errors."""
    try:
        subprocess.run(command, check=check)
    except FileNotFoundError:
        print(f"Warning: Command ''{command[0]}'' not found. Skipping.")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Command ''{' '.join(command)}'' failed with error: {e}")


def symlink_file(source, destination):
    """Creates a symlink, overwriting if it exists."""
    home_dir = os.environ.get('HOME', '')
    source_path = os.path.join(os.path.dirname(__file__), source)
    destination_path = os.path.join(home_dir, destination)
    
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    if os.path.islink(destination_path):
        os.remove(destination_path)
    elif os.path.exists(destination_path):
        print(f"Warning: {destination_path} exists and is not a symlink. Backing it up to {destination_path}.bak.")
        shutil.move(destination_path, f"{destination_path}.bak")
        
    os.symlink(source_path, destination_path)
    print(f"{source} symlinked to {destination_path}")


def symlink_agent_files():
    """Symlinks each agent file to the ~/.claude/agents directory."""
    home_dir = os.environ.get('HOME', '')
    agents_dir = os.path.join(os.path.dirname(__file__), 'agents')
    claude_agents_dir = os.path.join(home_dir, '.claude', 'agents')

    if not os.path.isdir(agents_dir):
        print(f"Warning: {agents_dir} not found. Skipping agent symlinking.")
        return

    os.makedirs(claude_agents_dir, exist_ok=True)

    for filename in os.listdir(agents_dir):
        source_path = os.path.join(agents_dir, filename)
        destination_path = os.path.join(claude_agents_dir, filename)

        if os.path.islink(destination_path):
            os.remove(destination_path)
        elif os.path.exists(destination_path):
            print(f"Warning: {destination_path} exists and is not a symlink. Skipping.")
            continue
        
        os.symlink(source_path, destination_path)
        print(f"{filename} symlinked to {destination_path}")


def symlink_scripts():
    """Symlinks the scripts directory to ~/.gemini/scripts and ~/.claude/scripts."""
    home_dir = os.environ.get('HOME', '')
    scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts')
    
    if not os.path.isdir(scripts_dir):
        print(f"Warning: {scripts_dir} not found. Skipping scripts symlinking.")
        return

    for tool in ['.gemini', '.claude']:
        tool_scripts_dir = os.path.join(home_dir, tool, 'scripts')
        os.makedirs(os.path.dirname(tool_scripts_dir), exist_ok=True)

        if os.path.islink(tool_scripts_dir):
            os.remove(tool_scripts_dir)
        elif os.path.exists(tool_scripts_dir):
            print(f"Warning: {tool_scripts_dir} exists and is not a symlink. Backing it up.")
            shutil.move(tool_scripts_dir, f"{tool_scripts_dir}.bak")
        
        os.symlink(scripts_dir, tool_scripts_dir)
        print(f"scripts symlinked to {tool_scripts_dir}")


def install_dotfiles(args):
    """Installs dotfiles and software."""
    print("Starting bootstrap process...")

    script_dir = os.path.dirname(__file__)

    if platform.system() == 'Darwin':
        print("Detected macOS. Installing Homebrew and software...")
        if not shutil.which('brew'):
            print("Homebrew not found. Installing Homebrew...")
            run_command(['/bin/bash', '-c', '$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/LATEST/install.sh)'])
        else:
            print("Homebrew is already installed. Updating...")
            run_command(['brew', 'update'])

        brewfile = os.path.join(script_dir, 'Brewfile')
        if os.path.exists(brewfile):
            print("Installing software from Brewfile...")
            run_command(['brew', 'bundle', f'--file={brewfile}'])
        else:
            print("No Brewfile found. Skipping software installation.")

        brewfile_opt = os.path.join(script_dir, 'Brewfile.opt')
        if os.path.exists(brewfile_opt) and not args.skip_optional:
            print("Checking for optional software in Brewfile.opt...")
            with open(brewfile_opt, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split()
                    if len(parts) != 2:
                        print(f"Warning: Skipping malformed line in Brewfile.opt: {line}")
                        continue

                    command, package = parts
                    package = package.strip('"')

                    if args.yes:
                        response = 'y'
                    else:
                        response = input(f"Do you want to install optional software '{package}'? (y/n) ")
                    
                    if response.lower() == 'y':
                        print(f"Installing {package}...")
                        if command == 'cask':
                            run_command(['brew', 'install', '--cask', package])
                        else:
                            run_command(['brew', 'install', package])
                    else:
                        print(f"Skipping {package}.")
        else:
            if args.skip_optional:
                print("Skipping optional software as requested.")
            else:
                print("No Brewfile.opt found. Skipping optional software installation.")

        set_macos_preferences()
    else:
        print("Not on MacOS. Skipping homebrew and macOS settings installation.")

    print("Symlinking dotfiles...")
    symlink_file('gitconfig', '.gitconfig')
    symlink_file('.zshrc', '.zshrc')
    symlink_file('.tmux.conf', '.tmux.conf')
    symlink_file('.vimrc', '.vimrc')
    symlink_file('ghostty/config', '.config/ghostty/config')
    symlink_file('AGENT.md', os.path.join('.gemini', 'GEMINI.md'))
    symlink_file('AGENT.md', os.path.join('.claude', 'CLAUDE.md'))
    symlink_file('gemini-settings.json', os.path.join('.gemini', 'settings.json'))
    symlink_file('claude-settings.json', os.path.join('.claude', 'settings.json'))
    symlink_agent_files()
    symlink_scripts()

    # Create empty .tmux.conf.local if it doesn't exist
    home_dir = os.environ.get('HOME', '')
    tmux_conf_local = os.path.join(home_dir, '.tmux.conf.local')
    if not os.path.exists(tmux_conf_local):
        open(tmux_conf_local, 'a').close()
        print(f"Created empty {tmux_conf_local}")

    print("Reloading tmux configuration...")
    # Explicitly unset deprecated hooks and clear status-right to avoid ghosting from previous versions
    tmux_cleanup = 'tmux set-hook -ug client-attached; tmux set-hook -ug pane-focus-in; tmux set-option -g status-right ""'
    run_command(['/bin/bash', '-c', f'if tmux info &>/dev/null; then {tmux_cleanup}; tmux source-file ~/.tmux.conf; echo "Tmux config reloaded."; else echo "Tmux not running, skipping reload."; fi'], check=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Install dotfiles and software.")
    parser.add_argument('--skip-optional', action='store_true', help="Skip optional software installation.")
    parser.add_argument('--yes', '-y', action='store_true', help="Answer yes to all prompts.")
    args = parser.parse_args()
    
    install_dotfiles(args)
