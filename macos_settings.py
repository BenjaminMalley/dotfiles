
import subprocess
import platform

def run_command(command):
    """Runs a command and checks for errors."""
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        print(f"Warning: Command '{command[0]}' not found. Skipping.")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Command '{' '.join(command)}' failed with error: {e}")


def set_shortcut(action_id, key_code, modifiers):
    """Sets a keyboard shortcut."""
    shortcut_plist = f"""
    <dict>
        <key>enabled</key><true/>
        <key>value</key><dict>
            <key>type</key><string>standard</string>
            <key>parameters</key><array>
                <integer>65535</integer>
                <integer>{key_code}</integer>
                <integer>{modifiers}</integer>
            </array>
        </dict>
    </dict>
    """
    run_command(['/usr/bin/defaults', 'write', 'com.apple.symbolichotkeys', 'AppleSymbolicHotKeys', '-dict-add', str(action_id), shortcut_plist])


def set_macos_preferences():
    """Sets macOS preferences."""
    if platform.system() != 'Darwin':
        print("Not on MacOS. Skipping macOS settings.")
        return

    print("Setting macOS preferences...")

    # --- Trackpad ---
    run_command(['defaults', 'write', 'NSGlobalDomain', 'com.apple.swipescrolldirection', '-bool', 'false'])

    # --- Keyboard Shortcuts ---
    print("Configuring keyboard shortcuts...")
    MODIFIERS = 1703936
    LEFT_ARROW = 123
    RIGHT_ARROW = 124
    TILE_LEFT_ID = 118
    TILE_RIGHT_ID = 119
    set_shortcut(TILE_LEFT_ID, LEFT_ARROW, MODIFIERS)
    set_shortcut(TILE_RIGHT_ID, RIGHT_ARROW, MODIFIERS)
    print("Keyboard shortcuts configured.")

    # --- Dock ---
    run_command(['defaults', 'write', 'com.apple.dock', 'autohide', '-bool', 'true'])
    run_command(['defaults', 'write', 'com.apple.dock', 'autohide-delay', '-float', '0'])

    # --- Menu Bar ---
    run_command(['defaults', 'write', 'NSGlobalDomain', '_HIHideMenuBar', '-bool', 'true'])

    # --- Keyboard ---
    run_command(['defaults', 'write', 'NSGlobalDomain', 'KeyRepeat', '-int', '2'])
    run_command(['defaults', 'write', 'NSGlobalDomain', 'InitialKeyRepeat', '-int', '12'])
    run_command(['defaults', 'write', 'NSGlobalDomain', 'AppleKeyboardUIMode', '-int', '3'])
    run_command(['defaults', 'write', 'NSGlobalDomain', 'NSAutomaticSpellingCorrectionEnabled', '-bool', 'false'])
    run_command(['defaults', 'write', 'NSGlobalDomain', 'NSAutomaticCapitalizationEnabled', '-bool', 'false'])

    # --- Stage Manager ---
    run_command(['defaults', 'write', 'com.apple.WindowManager', 'GloballyEnabled', '-bool', 'true'])

    # --- Finder ---
    run_command(['defaults', 'write', 'com.apple.finder', 'AppleShowAllFiles', '-bool', 'true'])
    run_command(['defaults', 'write', 'NSGlobalDomain', 'AppleShowAllExtensions', '-bool', 'true'])
    run_command(['defaults', 'write', 'com.apple.finder', 'ShowStatusBar', '-bool', 'true'])
    run_command(['defaults', 'write', 'com.apple.finder', 'ShowPathbar', '-bool', 'true'])

    print("Attempting to reload settings by restarting the Dock, Finder, and WindowManager...")
    run_command(['killall', 'Dock'])
    run_command(['killall', 'Finder'])
    run_command(['killall', 'WindowManager'])
    run_command(['killall', 'SystemUIServer'])

    print("macOS preferences have been set. A logout or restart may be required for all changes to take effect.")


if __name__ == '__main__':
    set_macos_preferences()
