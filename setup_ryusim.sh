#!/usr/bin/env bash
set -euo pipefail

echo "=== Setting up taxi-on-ryusim ==="

# 1. Initialize submodule
git submodule update --init --recursive

# 2. Install RyuSim
if ! command -v ryusim &>/dev/null; then
    echo "Installing RyuSim..."
    curl -fsSL https://ryusim.seiraiyu.com/install.sh | bash
    export PATH="$HOME/.ryusim/bin:$PATH"
fi
echo "RyuSim: $(ryusim --version)"

# 3. Install Python dependencies
pip install -r requirements.txt
echo "cocotb: $(python -c 'import cocotb; print(cocotb.__version__)')"

echo "=== Setup complete ==="
