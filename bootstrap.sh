#!/bin/bash

set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "Starting bootstrap process..."

# 1. Ensure Python 3 is available
if ! command_exists python3; then
    echo "Error: python3 is required but not found."
    exit 1
fi

# 2. Setup Homebrew on macOS (required for the playbook tasks)
if [ "$(uname -s)" = "Darwin" ]; then
    if ! command_exists brew; then
        echo "Homebrew not found. Installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        if [ -f /opt/homebrew/bin/brew ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -f /usr/local/bin/brew ]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    fi
fi

# 3. Create a virtual environment for Ansible
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# 4. Install Ansible in the venv
echo "Installing Ansible in virtual environment..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install ansible

# 5. Run the playbook using the venv's ansible-playbook
echo "Running Ansible playbook..."
"$VENV_DIR/bin/ansible-playbook" ansible/local.yml "$@"
