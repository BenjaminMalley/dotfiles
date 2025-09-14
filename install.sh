#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "Starting bootstrap process..."

OS=$(uname -s)

if [[ "$OS" == "Darwin" ]]; then
    echo "Detected macOS. Installing Homebrew and software from Brewfile..."

    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/LATEST/install.sh)"

        (echo; echo 'eval "$(/opt/homebrew/bin/brew shellenv)"') >> $HOME/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        echo "Homebrew is already installed. Updating..."
        brew update
    fi

    if [ -f "Brewfile" ]; then
        echo "Installing software from Brewfile..."
        brew bundle --file="Brewfile"
    else
        echo "No Brewfile found. Skipping software installation."
    fi

    if [ -f "Brewfile.opt" ]; then
        read -p "Do you want to install optional software from Brewfile.opt? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Installing optional software from Brewfile.opt..."
            brew bundle --file="Brewfile.opt"
        else
            echo "Skipping optional software installation."
        fi
    fi

    echo "Applying macOS settings..."
    "$SCRIPT_DIR/macos_settings.sh"

else
    echo "Not on MacOS. Skipping homebrew installation."
fi

echo "Symlinking dotfiles..."

ln -sf "$SCRIPT_DIR/.gitconfig" "$HOME/.gitconfig"
echo ".gitconfig symlinked to $HOME/.gitconfig"

ln -sf "$SCRIPT_DIR/.zshrc" "$HOME/.zshrc"
echo ".zshrc symlinked to $HOME/.zshrc"

ln -sf "$SCRIPT_DIR/.screenrc" "$HOME/.screenrc"
echo ".screenrc symlinked to $HOME/.screenrc"

ln -sf "$SCRIPT_DIR/AGENT.md" "$HOME/GEMINI.md"
echo "AGENT.md symlinked to $HOME/GEMINI.md"

ln -sf "$SCRIPT_DIR/AGENT.md" "$HOME/CLAUDE.md"
echo "AGENT.md symlinked to $HOME/CLAUDE.md"

mkdir -p "$HOME/.gemini"
ln -sf "$SCRIPT_DIR/gemini-settings.json" "$HOME/.gemini/settings.json"
echo "gemini-settings.json symlinked to $HOME/.gemini/settings.json"

mkdir -p "$HOME/.screenlogs"
echo "Created $HOME/.screenlogs directory for screen logs."
