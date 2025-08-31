#!/bin/bash

# Sets macOS preferences.

echo "Setting macOS preferences..."

# --- Trackpad ---
# Disable "natural" scroll direction.
defaults write NSGlobalDomain com.apple.swipescrolldirection -bool false

# --- Keyboard Shortcuts ---

# This is complex. We are modifying the binary plist file that stores shortcuts.
# A logout/login is often required for these to take effect.

# Function to set a keyboard shortcut.
# Usage: set_shortcut <action_id> <key_code> <modifiers>
set_shortcut() {
  local action_id="$1"
  local key_code="$2"
  local modifiers="$3"
  
  # The complex plist structure for a shortcut.
  # We target the `AppleSymbolicHotKeys` dictionary within the `com.apple.symbolichotkeys` domain.
  local shortcut_plist="<dict><key>enabled</key><true/><key>value</key><dict><key>type</key><string>standard</string><key>parameters</key><array><integer>65535</integer><integer>${key_code}</integer><integer>${modifiers}</integer></array></dict></dict>"
  
  /usr/bin/defaults write com.apple.symbolichotkeys AppleSymbolicHotKeys -dict-add "${action_id}" "${shortcut_plist}"
}

echo "Configuring keyboard shortcuts..."

# Modifier key masks:
# Ctrl: 131072
# Opt:  524288
# Cmd: 1048576
# Ctrl+Opt+Cmd = 1703936
MODIFIERS=1703936

# Key codes:
# Left Arrow:  123
# Right Arrow: 124
LEFT_ARROW=123
RIGHT_ARROW=124

# Action IDs for window tiling:
TILE_LEFT_ID=118
TILE_RIGHT_ID=119

# Set "Tile Window to Left of Screen" to Ctrl+Opt+Cmd+Left
set_shortcut $TILE_LEFT_ID $LEFT_ARROW $MODIFIERS

# Set "Tile Window to Right of Screen" to Ctrl+Opt+Cmd+Right
set_shortcut $TILE_RIGHT_ID $RIGHT_ARROW $MODIFIERS

echo "Keyboard shortcuts configured."

# --- Dock ---
# Auto-hide the Dock with no delay.
defaults write com.apple.dock autohide -bool true
defaults write com.apple.dock autohide-delay -float 0

# --- Keyboard ---
# Set a faster key repeat rate.
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write NSGlobalDomain InitialKeyRepeat -int 12

# Enable full keyboard access for all controls.
defaults write NSGlobalDomain AppleKeyboardUIMode -int 3

# Disable auto-correct.
defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false

# Disable automatic capitalization.
defaults write NSGlobalDomain NSAutomaticCapitalizationEnabled -bool false

# --- Stage Manager ---
# Enable Stage Manager.
defaults write com.apple.WindowManager GloballyEnabled -bool true

# --- Finder ---
# Show hidden files.
defaults write com.apple.finder AppleShowAllFiles -bool true

# Show all file extensions.
defaults write NSGlobalDomain AppleShowAllExtensions -bool true

# Show status bar.
defaults write com.apple.finder ShowStatusBar -bool true

# Show path bar.
defaults write com.apple.finder ShowPathbar -bool true

echo "Attempting to reload settings by restarting the Dock, Finder, and WindowManager..."
killall Dock
killall Finder
killall WindowManager

echo "macOS preferences have been set. A logout or restart may be required for all changes to take effect."