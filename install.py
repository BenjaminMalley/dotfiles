
import subprocess
import platform
import os
import shutil
from macos_settings import set_macos_preferences


def run_command(command):
    """Runs a command and checks for errors."""
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        print(f"Warning: Command '{command[0]}' not found. Skipping.")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Command '{' '.join(command)}' failed with error: {e}")


def symlink_file(source, destination):
    """Creates a symlink, overwriting if it exists."""
    home_dir = os.environ.get('HOME', '')
    source_path = os.path.join(os.path.dirname(__file__), source)
    destination_path = os.path.join(home_dir, destination)
    
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    if os.path.islink(destination_path):
        os.remove(destination_path)
    elif os.path.exists(destination_path):
        print(f"Warning: {destination_path} exists and is not a symlink. Skipping.")
        return
        
    os.symlink(source_path, destination_path)
    print(f"{source} symlinked to {destination_path}")


def install_dotfiles():
    """Installs dotfiles and software."""
    print("Starting bootstrap process...")

    script_dir = os.path.dirname(__file__)

    if platform.system() == 'Darwin':
        print("Detected macOS. Installing Homebrew and software...")
        if not shutil.which('brew'):
            print("Homebrew not found. Installing Homebrew...")
            run_command(['/bin/bash', '-c', '$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/LATEST/install.sh)'])
            # This is tricky to handle in a script, as it modifies the shell environment.
            # For simplicity, we'll assume the user runs this in a new shell or sources their .zprofile.
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
        if os.path.exists(brewfile_opt):
            response = input("Do you want to install optional software from Brewfile.opt? (y/n) ")
            if response.lower() == 'y':
                print("Installing optional software from Brewfile.opt...")
                run_command(['brew', 'bundle', f'--file={brewfile_opt}'])
            else:
                print("Skipping optional software installation.")

        set_macos_preferences()
    else:
        print("Not on MacOS. Skipping homebrew and macOS settings installation.")

    print("Symlinking dotfiles...")
    symlink_file('.gitconfig', '.gitconfig')
    symlink_file('.zshrc', '.zshrc')
    symlink_file('.screenrc', '.screenrc')
    symlink_file('AGENT.md', 'GEMINI.md')
    symlink_file('AGENT.md', 'CLAUDE.md')
    symlink_file('gemini-settings.json', os.path.join('.gemini', 'settings.json'))
    symlink_file('agents', os.path.join('.claude', 'agents'))

    # Create screenlogs directory
    screenlogs_dir = os.path.join(os.environ.get('HOME', ''), '.screenlogs')
    os.makedirs(screenlogs_dir, exist_ok=True)
    print(f"Created {screenlogs_dir} directory for screen logs.")


if __name__ == '__main__':
    install_dotfiles()
