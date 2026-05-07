#!/bin/bash

set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "Starting bootstrap process..."

# Ensure macOS Command Line Tools are installed
if [ "$(uname -s)" = "Darwin" ]; then
    if ! xcode-select -p >/dev/null 2>&1; then
        echo "Command Line Tools not found. Installing..."
        touch /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
        CLT_PACKAGE=$(softwareupdate -l | grep "\*.*Command Line" | tail -n 1 | awk -F"*" '{print $2}' | sed -e 's/^ *//' | tr -d '\n')
        if [ -n "$CLT_PACKAGE" ]; then
            sudo softwareupdate -i "$CLT_PACKAGE" --verbose
            rm /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
        else
            rm /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
            xcode-select --install
            exit 1
        fi
    fi
fi

# Create a virtual environment for Ansible
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Install Ansible in the venv
echo "Installing Ansible in virtual environment..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install ansible

# Run the playbook using the venv's ansible-playbook
echo "Running Ansible playbook..."
"$VENV_DIR/bin/ansible-playbook" ansible/local.yml "$@"
