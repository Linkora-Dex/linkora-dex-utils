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


# Simple RAILGUN installation script with peer dependency resolution

echo "RAILGUN Simple Installation"
echo "=========================="

# Install with legacy peer deps to resolve conflicts
echo "Installing dependencies with legacy peer deps resolution..."

npm install --legacy-peer-deps

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"

    # Test installation
    echo "Testing installation..."
    node -e "
    try {
        const { RailgunEngine } = require('@railgun-community/engine');
        const { NetworkName } = require('@railgun-community/shared-models');
        const { createRailgunWallet } = require('@railgun-community/wallet');
        const { ethers } = require('ethers');
        console.log('✓ All modules loaded successfully');
    } catch (error) {
        console.log('✗ Module loading failed:', error.message);
        process.exit(1);
    }
    "

    if [ $? -eq 0 ]; then
        echo "✓ Installation test passed"
        echo ""
        echo "🎉 Ready to use!"
        echo ""
        echo "Set environment variables:"
        echo "export PRIVATE_KEY=your_private_key"
        echo "export WALLET_MNEMONIC=\"your mnemonic phrase\""
        echo "export AMOUNT=2000000000000000000"
        echo "export RECIPIENT_ADDRESS=0x..."
        echo ""
        echo "Run: python3 railgun_example.py"
    else
        echo "✗ Installation test failed"
        exit 1
    fi
else
    echo "✗ Failed to install dependencies"
    exit 1
fi