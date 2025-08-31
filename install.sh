#!/bin/bash

set -e

echo "Starting bootstrap process..."

OS=$(uname -s)

if [[ "$OS" == "Darwin" ]]; then
    echo "Detected macOS. Installing Homebrew and software from Brewfile.mac..."

    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/LATEST/install.sh)"

        (echo; echo 'eval "$(/opt/homebrew/bin/brew shellenv)"') >> /Users/$USER/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        echo "Homebrew is already installed. Updating..."
        brew update
    fi

    if [ -f "Brewfile" ]; then
        echo "Installing software from Brewfile.mac..."
        brew bundle --file="Brewfile"
    else
        echo "No Brewfile found. Skipping software installation."
    fi

else
    echo "Not on MacOS. Skipping homebrew installation."
fi

echo "Symlinking dotfiles..."
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

ln -sf "$SCRIPT_DIR/.gitconfig" "$HOME/.gitconfig"
echo ".gitconfig symlinked to $HOME/.gitconfig"

ln -sf "$SCRIPT_DIR/.zshrc" "$HOME/.zshrc"
echo ".zshrc symlinked to $HOME/.zshrc"

ln -sf "$SCRIPT_DIR/.screenrc" "$HOME/.screenrc"
echo ".screenrc symlinked to $HOME/.screenrc"
