import os
import sys
from lib.utils import run_command, is_darwin

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

def set_terminal_profile_setting(profile, key, type, value):
    """Sets a setting in a Terminal profile using PlistBuddy."""
    plist = os.path.expanduser('~/Library/Preferences/com.apple.Terminal.plist')
    # Use double quotes for path components to handle spaces correctly
    path = f':"Window Settings":"{profile}":{key}'
    # Try to set it first
    try:
        run_command(['/usr/libexec/PlistBuddy', '-c', f"Set {path} {value}", plist], check=True)
    except Exception:
        # If set fails, it probably doesn't exist, so try to add it
        run_command(['/usr/libexec/PlistBuddy', '-c', f"Add {path} {type} {value}", plist])

def set_macos_preferences():
    """Sets macOS preferences."""
    if not is_darwin():
        print("Not on MacOS. Skipping macOS settings.")
        return

    print("Setting macOS preferences...")

    # Define settings as a list of tuples (domain, key, type, value)
    # Types: -bool, -int, -float, -string
    SETTINGS = [
        # Trackpad
        ('NSGlobalDomain', 'com.apple.swipescrolldirection', '-bool', 'false'),
        # Dock
        ('com.apple.dock', 'autohide', '-bool', 'true'),
        ('com.apple.dock', 'autohide-delay', '-float', '0'),
        # Menu Bar
        ('NSGlobalDomain', '_HIHideMenuBar', '-bool', 'true'),
        # Keyboard
        ('NSGlobalDomain', 'KeyRepeat', '-int', '2'),
        ('NSGlobalDomain', 'InitialKeyRepeat', '-int', '12'),
        ('NSGlobalDomain', 'AppleKeyboardUIMode', '-int', '3'),
        ('NSGlobalDomain', 'NSAutomaticSpellingCorrectionEnabled', '-bool', 'false'),
        ('NSGlobalDomain', 'NSAutomaticCapitalizationEnabled', '-bool', 'false'),
        ('NSGlobalDomain', 'NSAutomaticQuoteSubstitutionEnabled', '-bool', 'false'),
        ('NSGlobalDomain', 'NSAutomaticDashSubstitutionEnabled', '-bool', 'false'),
        # Stage Manager
        ('com.apple.WindowManager', 'GloballyEnabled', '-bool', 'true'),
        # Finder
        ('com.apple.finder', 'AppleShowAllFiles', '-bool', 'true'),
        ('NSGlobalDomain', 'AppleShowAllExtensions', '-bool', 'true'),
        ('com.apple.finder', 'ShowStatusBar', '-bool', 'true'),
        ('com.apple.finder', 'ShowPathbar', '-bool', 'true'),
        # Sound
        ('NSGlobalDomain', 'com.apple.sound.beep.feedback', '-int', '0'),
        ('NSGlobalDomain', 'com.apple.sound.beep.volume', '-float', '0'),
        # Terminal
        ('com.apple.Terminal', 'VisualBell', '-bool', 'false'),
        ('com.apple.Terminal', 'AudibleBell', '-bool', 'false'),
    ]

    for domain, key, type_arg, value in SETTINGS:
        run_command(['defaults', 'write', domain, key, type_arg, value])

    # --- Keyboard Shortcuts ---
    MODIFIERS = 1703936
    LEFT_ARROW = 123
    RIGHT_ARROW = 124
    TILE_LEFT_ID = 118
    TILE_RIGHT_ID = 119
    set_shortcut(TILE_LEFT_ID, LEFT_ARROW, MODIFIERS)
    set_shortcut(TILE_RIGHT_ID, RIGHT_ARROW, MODIFIERS)

    # --- GH CLI ---
    run_command(['gh', 'config', 'set', 'prompt', 'disabled'], check=False)

    # --- Terminal Profiles ---
    for profile in ["Basic", "Pro", "Clear Dark"]:
        set_terminal_profile_setting(profile, "shellExitAction", "integer", "1")
        set_terminal_profile_setting(profile, "BackgroundAlphaInactive", "real", "0.5")
        set_terminal_profile_setting(profile, "BackgroundSettingsForInactiveWindows", "bool", "true")

    # --- Sound (Immediate) ---
    run_command(['osascript', '-e', 'set volume alert volume 0'])

    print("Reloading system services (Dock, Finder, etc.)...")
    SERVICES = ['Dock', 'Finder', 'WindowManager', 'SystemUIServer']
    for service in SERVICES:
        run_command(['killall', service], check=False)

    # Only kill Terminal if we aren't running inside it or if explicitly asked
    # (Leaving it for now as per original logic but we could be more careful)
    # run_command(['killall', 'Terminal'], check=False)

    print("macOS preferences have been set.")

if __name__ == '__main__':
    set_macos_preferences()