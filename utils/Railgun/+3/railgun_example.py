#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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


from railgun_bridge import RailgunBridge, RailgunConfig
import logging
import time
import os
import sys
from dotenv import load_dotenv


# Загрузка переменных окружения из файла .env
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_env_vars():
    required_vars = {
        'PRIVATE_KEY': os.getenv('PRIVATE_KEY'),
        'WALLET_MNEMONIC': os.getenv('WALLET_MNEMONIC'),
        'TOKEN_SYMBOL': os.getenv('TOKEN_SYMBOL', 'MATIC'),
        'AMOUNT': os.getenv('AMOUNT'),
        'RECIPIENT_ADDRESS': os.getenv('RECIPIENT_ADDRESS'),
        'NETWORK': os.getenv('NETWORK', 'polygon')
    }

    optional_vars = {
        'RPC_URL': os.getenv('RPC_URL'),
        'GAS_PRICE': os.getenv('GAS_PRICE'),
        'WAIT_TIME': int(os.getenv('WAIT_TIME', '30'))
    }

    missing_required = [key for key, value in required_vars.items() if not value]

    if missing_required:
        print("Missing required environment variables:")
        for var in missing_required:
            print(f"  {var}")
        print("\nRequired variables:")
        print("  PRIVATE_KEY - Your Ethereum private key")
        print("  WALLET_MNEMONIC - Your Railgun wallet mnemonic")
        print("  AMOUNT - Amount to transfer (in wei for native tokens)")
        print("  RECIPIENT_ADDRESS - Final recipient address (0x...)")
        print("\nOptional variables:")
        print("  RPC_URL - Custom RPC endpoint")
        print("  TOKEN_SYMBOL - Token to transfer (default: MATIC)")
        print("  NETWORK - Network to use (default: polygon)")
        print("  GAS_PRICE - Custom gas price")
        print("  WAIT_TIME - Wait time between operations (default: 30)")
        return None, None

    return required_vars, optional_vars


def validate_inputs(required_vars, config):
    network = required_vars['NETWORK']
    token_symbol = required_vars['TOKEN_SYMBOL']
    amount = required_vars['AMOUNT']
    recipient = required_vars['RECIPIENT_ADDRESS']

    try:
        config.get_token_address(network, token_symbol)
    except ValueError as e:
        print(f"Error: {e}")
        return False

    try:
        int(amount)
    except ValueError:
        print(f"Error: Invalid amount '{amount}'. Must be a number.")
        return False

    if not recipient.startswith('0x') or len(recipient) != 42:
        print(f"Error: Invalid recipient address '{recipient}'")
        return False

    return True


def display_transfer_info(required_vars, optional_vars, token_address):
    print("RAILGUN Automatic Transfer")
    print("=" * 50)
    print(f"Network: {required_vars['NETWORK']}")
    print(f"Token: {required_vars['TOKEN_SYMBOL']} ({token_address})")
    print(f"Amount: {required_vars['AMOUNT']}")
    print(f"Recipient: {required_vars['RECIPIENT_ADDRESS']}")
    print(f"RPC URL: {optional_vars['RPC_URL'] or 'Default'}")
    print(f"Wait Time: {optional_vars['WAIT_TIME']} seconds")
    print("=" * 50)


def auto_transfer():
    required_vars, optional_vars = get_env_vars()
    if not required_vars:
        return False

    config = RailgunConfig()

    if not validate_inputs(required_vars, config):
        return False

    try:
        token_address = config.get_token_address(required_vars['NETWORK'], required_vars['TOKEN_SYMBOL'])

        display_transfer_info(required_vars, optional_vars, token_address)

        bridge = RailgunBridge(required_vars['NETWORK'])

        print("\n1. Initializing Railgun...")
        init_result = bridge.initialize(optional_vars['RPC_URL'], required_vars['PRIVATE_KEY'])

        if not init_result.get('success'):
            print(f"✗ Initialization failed: {init_result.get('error')}")
            return False

        print(f"✓ Initialized on {required_vars['NETWORK']}")

        print("\n2. Loading Railgun wallet...")
        wallet_result = bridge.load_wallet(required_vars['WALLET_MNEMONIC'])

        if not wallet_result.get('success'):
            print(f"✗ Wallet loading failed: {wallet_result.get('error')}")
            return False

        print(f"✓ Wallet loaded: {bridge.wallet.address}")

        print("\n3. Starting shield operation...")
        shield_result = bridge.shield_tokens(
            token_address,
            required_vars['AMOUNT'],
            optional_vars['GAS_PRICE']
        )

        if not shield_result.success:
            print(f"✗ Shield failed: {shield_result.error}")
            return False

        print(f"✓ Shield completed: {shield_result.tx_hash}")
        print(f"  Gas used: {shield_result.gas_used}")
        print(f"  Block: {shield_result.block_number}")

        print(f"\n4. Waiting {optional_vars['WAIT_TIME']} seconds for confirmation...")
        time.sleep(optional_vars['WAIT_TIME'])

        print("\n5. Starting private transfer...")
        transfer_result = bridge.private_transfer(
            token_address,
            required_vars['AMOUNT'],
            bridge.wallet.address,
            optional_vars['GAS_PRICE']
        )

        if not transfer_result.success:
            print(f"✗ Private transfer failed: {transfer_result.error}")
            return False

        print(f"✓ Private transfer completed: {transfer_result.tx_hash}")
        print(f"  Gas used: {transfer_result.gas_used}")
        print(f"  Block: {transfer_result.block_number}")

        print(f"\n6. Waiting {optional_vars['WAIT_TIME']} seconds for confirmation...")
        time.sleep(optional_vars['WAIT_TIME'])

        print("\n7. Starting unshield operation...")
        unshield_result = bridge.unshield_tokens(
            token_address,
            required_vars['AMOUNT'],
            required_vars['RECIPIENT_ADDRESS'],
            optional_vars['GAS_PRICE']
        )

        if not unshield_result.success:
            print(f"✗ Unshield failed: {unshield_result.error}")
            return False

        print(f"✓ Unshield completed: {unshield_result.tx_hash}")
        print(f"  Gas used: {unshield_result.gas_used}")
        print(f"  Block: {unshield_result.block_number}")

        print("\n🎉 Complete transfer process finished successfully!")
        print("\nSummary:")
        print(f"  Shield TX: {shield_result.tx_hash}")
        print(f"  Transfer TX: {transfer_result.tx_hash}")
        print(f"  Unshield TX: {unshield_result.tx_hash}")
        print(f"  Total gas used: {int(shield_result.gas_used or 0) + int(transfer_result.gas_used or 0) + int(unshield_result.gas_used or 0)}")

        return True

    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Transfer process failed: {e}")
        print(f"\n✗ Transfer process failed: {e}")
        return False


def interactive_mode():
    print("RAILGUN Interactive Transfer")
    print("=" * 40)

    network = input("Enter network (ethereum/polygon/bsc) [polygon]: ").strip() or "polygon"
    private_key = input("Enter your private key: ").strip()
    mnemonic = input("Enter wallet mnemonic: ").strip()
    token_symbol = input("Enter token symbol [MATIC]: ").strip() or "MATIC"
    amount = input("Enter amount (in wei): ").strip()
    recipient = input("Enter recipient address: ").strip()

    os.environ['NETWORK'] = network
    os.environ['PRIVATE_KEY'] = private_key
    os.environ['WALLET_MNEMONIC'] = mnemonic
    os.environ['TOKEN_SYMBOL'] = token_symbol
    os.environ['AMOUNT'] = amount
    os.environ['RECIPIENT_ADDRESS'] = recipient

    return auto_transfer()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        success = interactive_mode()
    else:
        success = auto_transfer()

    if success:
        print("\n✓ Process completed successfully")
        sys.exit(0)
    else:
        print("\n✗ Process failed")
        sys.exit(1)


if __name__ == "__main__":
    main()