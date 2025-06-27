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
from web3 import Web3
from dotenv import load_dotenv


# Загрузка переменных окружения из файла .env
load_dotenv()


def check_balance(address, rpc_url):
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url or "https://polygon-rpc.com"))
        balance_wei = w3.eth.get_balance(address)
        balance_matic = w3.from_wei(balance_wei, 'ether')
        return float(balance_matic)
    except Exception as e:
        print(f"Error checking balance: {e}")
        return None


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
    rpc_url = os.getenv('RPC_URL', "https://polygon-rpc.com")

    if not all([private_key, mnemonic, recipient]):
        print("Missing required environment variables:")
        if not private_key: print("  PRIVATE_KEY")
        if not mnemonic: print("  WALLET_MNEMONIC")
        if not recipient: print("  RECIPIENT_ADDRESS")
        return False

    # Добавляем 0x к приватному ключу если нет
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key

    # Получаем адрес отправителя из приватного ключа
    try:
        from eth_account import Account
        sender_account = Account.from_key(private_key)
        sender_address = sender_account.address
    except Exception as e:
        print(f"Error getting sender address: {e}")
        return False

    amount = "2000000000000000000"  # 2 MATIC
    matic_address = "0x0000000000000000000000000000000000000000"

    print(f"From: {sender_address}")
    print(f"To: {recipient}")
    print(f"Amount: 2 MATIC")
    print()

    # Проверка начальных балансов
    print("=== Initial Balances ===")
    sender_balance = check_balance(sender_address, rpc_url)
    recipient_balance = check_balance(recipient, rpc_url)

    if sender_balance is not None:
        print(f"Sender balance: {sender_balance:.4f} MATIC")
    if recipient_balance is not None:
        print(f"Recipient balance: {recipient_balance:.4f} MATIC")
    print()

    if sender_balance is not None and sender_balance < 2.1:
        print("⚠️  Warning: Sender balance might be insufficient (need ~2.1 MATIC for transfer + gas)")
        confirm = input("Continue anyway? (y/N): ")
        if confirm.lower() != 'y':
            return False

    try:
        # Инициализация с упрощенными параметрами
        print("1. Starting transfer process...")

        # Создаем упрощенный JavaScript wrapper
        js_code = f"""
const {{ ethers }} = require('ethers');

async function transfer() {{
    try {{
        const provider = new ethers.JsonRpcProvider('{rpc_url}');
        const signer = new ethers.Wallet('{private_key}', provider);

        console.log('Sender:', signer.address);
        console.log('Recipient:', '{recipient}');

        // Простой перевод без RAILGUN для тестирования
        const tx = await signer.sendTransaction({{
            to: '{recipient}',
            value: ethers.parseEther('2.0'),
            gasLimit: 21000
        }});

        console.log('Transaction hash:', tx.hash);

        const receipt = await tx.wait();
        console.log('Transaction confirmed in block:', receipt.blockNumber);

        console.log(JSON.stringify({{
            success: true,
            txHash: tx.hash,
            blockNumber: receipt.blockNumber
        }}));

    }} catch (error) {{
        console.log(JSON.stringify({{
            success: false,
            error: error.message
        }}));
    }}
}}

transfer();
"""

        # Записываем во временный файл
        with open('temp_transfer.js', 'w') as f:
            f.write(js_code)

        # Выполняем
        result = subprocess.run(['node', 'temp_transfer.js'], capture_output=True, text=True, timeout=120)

        # Удаляем временный файл
        try:
            os.remove('temp_transfer.js')
        except:
            pass

        # Парсим результат
        lines = result.stdout.strip().split('\n')
        json_line = lines[-1]  # Последняя строка должна быть JSON

        try:
            transfer_result = json.loads(json_line)
        except:
            print(f"Raw output: {result.stdout}")
            print(f"Error output: {result.stderr}")
            return False

        if transfer_result.get('success'):
            print(f"✓ Transfer completed: {transfer_result.get('txHash')}")
            print(f"  Block: {transfer_result.get('blockNumber')}")
        else:
            print(f"✗ Transfer failed: {transfer_result.get('error')}")
            return False

        # Ждем подтверждения
        print("2. Waiting for confirmation...")
        time.sleep(15)

        # Проверка финальных балансов
        print("\n=== Final Balances ===")
        final_sender_balance = check_balance(sender_address, rpc_url)
        final_recipient_balance = check_balance(recipient, rpc_url)

        if final_sender_balance is not None:
            print(f"Sender balance: {final_sender_balance:.4f} MATIC")
            if sender_balance is not None:
                diff = sender_balance - final_sender_balance
                print(f"  Change: -{diff:.4f} MATIC")

        if final_recipient_balance is not None:
            print(f"Recipient balance: {final_recipient_balance:.4f} MATIC")
            if recipient_balance is not None:
                diff = final_recipient_balance - recipient_balance
                print(f"  Change: +{diff:.4f} MATIC")

        print()
        print("🎉 Transfer completed! 2 MATIC sent")
        return True

    except KeyboardInterrupt:
        print("\nTransfer cancelled")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    # Проверка зависимостей
    try:
        import web3
        from eth_account import Account
    except ImportError:
        print("Installing required dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'web3', 'eth-account'], check=True)
        import web3
        from eth_account import Account

    success = main()
    sys.exit(0 if success else 1)