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
from web3 import Web3
from dotenv import load_dotenv
import json

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение переменных окружения
PRIVATE_KEY = os.getenv('PRIVATE_KEY')  # Приватный ключ отправителя
RECEIVER_ADDRESS = os.getenv('RECEIVER_ADDRESS')  # Адрес получателя (для вывода)
TORNADO_CONTRACT_ADDRESS = os.getenv('TORNADO_CONTRACT_ADDRESS')  # Адрес контракта Tornado Cash для MATIC

# Проверка наличия переменных окружения
if not all([PRIVATE_KEY, RECEIVER_ADDRESS, TORNADO_CONTRACT_ADDRESS]):
    raise ValueError("Не все переменные окружения установлены в .env файле")

# Преобразование адреса контракта в checksum-формат
try:
    TORNADO_CONTRACT_ADDRESS = Web3.to_checksum_address(TORNADO_CONTRACT_ADDRESS)
except ValueError as e:
    raise ValueError(f"Неверный адрес контракта: {TORNADO_CONTRACT_ADDRESS}. Ошибка: {e}")

# Подключение к сети Polygon через RPC
POLYGON_RPC_URL = "https://polygon-rpc.com"  # Можно заменить на Alchemy/Infura
w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))

# Проверка подключения
if not w3.is_connected():
    raise ConnectionError("Не удалось подключиться к сети Polygon")

# Инициализация аккаунта отправителя
account = w3.eth.account.from_key(PRIVATE_KEY)
sender_address = account.address

# Проверка баланса кошелька
balance = w3.eth.get_balance(sender_address)
DEPOSIT_AMOUNT = w3.to_wei(0.1, 'ether')  # 0.1 MATIC для депозита
MINIMUM_GAS_COST = w3.to_wei(0.015, 'ether')  # Примерная стоимость газа (300000 * 50 Gwei)
if balance < DEPOSIT_AMOUNT + MINIMUM_GAS_COST:
    raise ValueError(f"Недостаточно средств на кошельке {sender_address}. "
                     f"Баланс: {w3.from_wei(balance, 'ether')} MATIC, "
                     f"Требуется: {w3.from_wei(DEPOSIT_AMOUNT + MINIMUM_GAS_COST, 'ether')} MATIC")

# ABI смарт-контракта Tornado Cash (упрощённый, для депозита)
TORNADO_ABI = [
    {
        "constant": False,
        "inputs": [{"name": "_commitment", "type": "bytes32"}],
        "name": "deposit",
        "outputs": [],
        "payable": True,
        "stateMutability": "payable",
        "type": "function"
    }
]

# Инициализация контракта
tornado_contract = w3.eth.contract(address=TORNADO_CONTRACT_ADDRESS, abi=TORNADO_ABI)

# Генерация обязательства (commitment) для депозита
# В реальном приложении это делается с использованием snarkjs (JS)
# Здесь используется заглушка, замените на реальное значение
commitment = w3.to_bytes(hexstr="0x" + "0" * 64)  # Замените на реальное commitment

# Создание транзакции для депозита

try:
    # Оценка газа
    gas = tornado_contract.functions.deposit(commitment).estimate_gas({
        'from': sender_address,
        'value': DEPOSIT_AMOUNT
    })
    # Получение текущей цены газа
    gas_price = w3.eth.gas_price
    tx = tornado_contract.functions.deposit(commitment).build_transaction({
        'from': sender_address,
        'value': DEPOSIT_AMOUNT,
        'nonce': w3.eth.get_transaction_count(sender_address),
        'gas': gas,
        'gasPrice': gas_price
    })

    # Подписание транзакции
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)

    # Отправка транзакции
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Транзакция отправлена. Хэш: {w3.to_hex(tx_hash)}")

    # Ожидание подтверждения транзакции
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Транзакция подтверждена. Статус: {'Успех' if tx_receipt.status == 1 else 'Неудача'}")

except Exception as e:
    print(f"Ошибка при выполнении транзакции: {e}")

# Инструкции для вывода (не реализовано в коде, так как требует zk-доказательства):
# 1. Сохраните "ноту" (секретный ключ), возвращённый при депозите.
# 2. Используйте JavaScript-библиотеку snarkjs для генерации zk-доказательства.
# 3. Вызовите функцию withdraw на контракте Tornado Cash с доказательством и RECEIVER_ADDRESS.