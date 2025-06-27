#!/bin/bash

# Copyright (C) 2025 Linkora DEX
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For commercial licensing, contact: licensing@linkora.info


# RAILGUN JavaScript SDK Setup Script

echo "RAILGUN JavaScript SDK Setup"
echo "============================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    echo "Please install Node.js from https://nodejs.org/"
    echo "Minimum version required: 18.0.0"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | sed 's/v//')
MIN_VERSION="18.0.0"

if [ "$(printf '%s\n' "$MIN_VERSION" "$NODE_VERSION" | sort -V | head -n1)" != "$MIN_VERSION" ]; then
    echo "Error: Node.js version $NODE_VERSION is too old"
    echo "Minimum version required: $MIN_VERSION"
    exit 1
fi

echo "✓ Node.js version: $NODE_VERSION"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed"
    exit 1
fi

echo "✓ npm version: $(npm -v)"

# Install RAILGUN SDK dependencies
echo ""
echo "Installing RAILGUN SDK dependencies..."
echo "This may take several minutes..."

npm install @railgun-community/engine@^9.4.0 \
           @railgun-community/shared-models@^7.6.1 \
           @railgun-community/wallet@^10.3.3 \
           ethers@6.13.1 --legacy-peer-deps

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
else
    echo "✗ Failed to install dependencies"
    exit 1
fi

# Test the installation
echo ""
echo "Testing installation..."
node -e "
const { RailgunEngine } = require('@railgun-community/engine');
const { NetworkName } = require('@railgun-community/shared-models');
const { createRailgunWallet } = require('@railgun-community/wallet');
const { ethers } = require('ethers');
console.log('✓ All modules loaded successfully');
console.log('✓ Installation test passed');
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "Usage instructions:"
    echo "1. Set your private key: export PRIVATE_KEY=your_private_key"
    echo "2. (Optional) Set RPC URL: export RPC_URL=your_rpc_url"
    echo "3. Run the example: python3 railgun_example.py"
    echo ""
    echo "Available networks: ethereum, polygon, bsc, arbitrum"
    echo ""
else
    echo "✗ Installation test failed"
    exit 1
fi