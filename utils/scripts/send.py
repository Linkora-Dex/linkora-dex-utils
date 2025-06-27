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

from web3 import Web3
from dotenv import load_dotenv
import os
load_dotenv()

RPC_URL = "https://rpc.ankr.com/polygon/fb00ba52a7de8c2eb4acca0df5590553673491333704db7739fbdf8a40d0f1ad"
USER1 = os.getenv('USER1')
USER1_PRIVATE_KEY = os.getenv('USER1_PRIVATE_KEY')
RECIPIENT = "0x9320D18D37777F6897aaa57Df36251633A5925D2"
TRANSFER_AMOUNT = 0.5

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    print("Ошибка подключения к сети")
    exit()

if not w3.is_address(RECIPIENT):
    print("Некорректный адрес получателя")
    exit()

balance_wei = w3.eth.get_balance(USER1)
balance_matic = w3.from_wei(balance_wei, 'ether')
transfer_wei = w3.to_wei(TRANSFER_AMOUNT, 'ether')

gas_price = w3.eth.gas_price
gas_limit = 21000
transaction_cost = gas_price * gas_limit
total_cost = transfer_wei + transaction_cost

if balance_wei < total_cost:
    print(f"Недостаточно средств. Баланс: {balance_matic} MATIC, требуется: {w3.from_wei(total_cost, 'ether')} MATIC")
    exit()

nonce = w3.eth.get_transaction_count(USER1)

transaction = {
    'to': RECIPIENT,
    'value': transfer_wei,
    'gas': gas_limit,
    'gasPrice': gas_price,
    'nonce': nonce,
    'chainId': 137,
}

signed_txn = w3.eth.account.sign_transaction(transaction, USER1_PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

print(f"Транзакция отправлена: {tx_hash.hex()}")
print(f"Переведено: {TRANSFER_AMOUNT} MATIC")
print(f"Получатель: {RECIPIENT}")
print(f"Комиссия: {w3.from_wei(transaction_cost, 'ether')} MATIC")