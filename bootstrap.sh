#!/bin/bash

set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "Starting bootstrap process..."

# Install Homebrew if not installed
if ! command_exists brew; then
    echo "Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "Homebrew is already installed."
fi

# Install Ansible if not installed
if ! command_exists ansible; then
    echo "Ansible not found. Installing via Homebrew..."
    brew install ansible
else
    echo "Ansible is already installed."
fi

# Run the playbook
echo "Running Ansible playbook..."
ansible-playbook ansible/local.yml "$@"
