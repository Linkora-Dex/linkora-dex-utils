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


import os
import sys
import subprocess
import json
import time
from dotenv import load_dotenv


# Загрузка переменных окружения из файла .env
load_dotenv()

def run_js_command(command):
    try:
        cmd = ['node', 'railgun_wrapper.js'] + command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            return {"success": False, "error": result.stderr}

        return json.loads(result.stdout)
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    print("RAILGUN Simple Transfer: 2 MATIC")
    print("=" * 40)

    # Проверка переменных
    private_key = os.getenv('PRIVATE_KEY')
    mnemonic = os.getenv('WALLET_MNEMONIC')
    recipient = os.getenv('RECIPIENT_ADDRESS')
    rpc_url = os.getenv('RPC_URL')

    if not all([private_key, mnemonic, recipient]):
        print("Missing required environment variables:")
        if not private_key: print("  PRIVATE_KEY")
        if not mnemonic: print("  WALLET_MNEMONIC")
        if not recipient: print("  RECIPIENT_ADDRESS")
        return False

    # Добавляем 0x к приватному ключу если нет
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key

    amount = "2000000000000000000"  # 2 MATIC
    matic_address = "0x0000000000000000000000000000000000000000"

    print(f"From: Private key wallet")
    print(f"To: {recipient}")
    print(f"Amount: 2 MATIC")
    print()

    try:
        # 1. Initialize
        print("1. Initializing...")
        init_cmd = ['init', 'polygon']
        if rpc_url:
            init_cmd.append(rpc_url)
        init_cmd.append(private_key)

        result = run_js_command(init_cmd)
        if not result.get('success'):
            print(f"✗ Init failed: {result.get('error')}")
            return False
        print("✓ Initialized")

        # 2. Load wallet
        print("2. Loading RAILGUN wallet...")
        result = run_js_command(['load-wallet', mnemonic])
        if not result.get('success'):
            print(f"✗ Wallet failed: {result.get('error')}")
            return False
        print("✓ Wallet loaded")

        # 3. Shield
        print("3. Shield 2 MATIC...")
        result = run_js_command(['shield', matic_address, amount])
        if not result.get('success'):
            print(f"✗ Shield failed: {result.get('error')}")
            return False
        print(f"✓ Shield: {result.get('txHash')}")

        # 4. Wait
        print("4. Waiting 30 seconds...")
        time.sleep(30)

        # 5. Unshield
        print("5. Unshield to recipient...")
        result = run_js_command(['unshield', matic_address, amount, recipient])
        if not result.get('success'):
            print(f"✗ Unshield failed: {result.get('error')}")
            return False
        print(f"✓ Unshield: {result.get('txHash')}")

        print()
        print("🎉 Transfer completed! 2 MATIC sent privately")
        return True

    except KeyboardInterrupt:
        print("\nTransfer cancelled")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)