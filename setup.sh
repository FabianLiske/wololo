#!/usr/bin/bash
set -euo pipefail

# 1. Check for Python 3.13
if ! command -v python3.13 > /dev/null 2>&1; then
    echo "Error: Python 3.13 is not installed or not in PATH!"
    echo "Please install Python 3.13, for example via 'sudo apt install python3.13 python3.13-venv') and try again."
    exit 1
fi

# 2. Remove existing venv
if [ -d "venv" ]; then
    echo "Directory 'venv' already exists, removing ..."
    rm -rf venv
fi

# 3. apt-packages
sudo apt update
sudo xargs -a apt-packages.txt apt install -y

# 4. Create venv
echo "Create venv with Python 3.13 ..."
python3.13 -m venv --system-site-packages venv

# 5. Activate and upgrade pip
echo "Activate venv and upgrade pip ..."
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# 6. Install Python packages
echo "Installing Python packages ..."
pip install -r python-packages.txt

# 7. Add user to GPIO-group
#sudo usermod -aG gpio $USER
echo "Done. Python 3.13 venv set up. Reboot RaspberryPi now."