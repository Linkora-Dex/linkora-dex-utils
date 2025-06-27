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
import json
import requests
import time
import asciichartpy
from datetime import datetime

# Настройки для Mantle Network
MANTLE_RPC_URL = "https://rpc.mantle.xyz"  # Альтернатива: https://rpc.ankr.com/mantle
web3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL))

# Проверка подключения
if not web3.is_connected():
    print("Ошибка: Не удалось подключиться к Mantle Network. Проверьте RPC URL.")
    exit()
else:
    print(f"Подключено к Mantle Network. Текущий блок: {web3.eth.block_number}")

# ABI для Chainlink Price Feed
PRICE_FEED_ABI = [
    {
        "inputs": [],
        "name": "latestRoundData",
        "outputs": [
            {"internalType": "uint80", "name": "roundId", "type": "uint80"},
            {"internalType": "int256", "name": "answer", "type": "int256"},
            {"internalType": "uint256", "name": "startedAt", "type": "uint256"},
            {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
            {"internalType": "uint80", "name": "answeredInRound", "type": "uint80"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "description",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    }
]

# Список адресов Price Feeds для Mantle Network
PRICE_FEEDS = {
    "ETH/USD": "0x5bc7Cf88EB131DB18b5d7930e793095140799aD5",
    "BTC/USD": "0x7db2275279F52D0914A481e14c4Ce5a59705A25b",
    "MNT/USD": "0xD97F20bEbeD74e8144134C4b148fE93417dd0F96",
}

# Хранилище для истории цен
price_history = {
    "ETH/USD": [],
    "BTC/USD": [],
    "MNT/USD": [],
}
timestamps = []


def get_price_feed_data(feed_address):
    try:
        feed_address = web3.to_checksum_address(feed_address)
        contract = web3.eth.contract(address=feed_address, abi=PRICE_FEED_ABI)
        latest_data = contract.functions.latestRoundData().call()
        decimals = contract.functions.decimals().call()
        description = contract.functions.description().call()
        price = latest_data[1] / 10 ** decimals
        return {
            "pair": description,
            "price": price,
            "updated_at": latest_data[3]
        }
    except Exception as e:
        return {"pair": feed_address, "error": f"{type(e).__name__}: {str(e)}"}


def get_all_prices():
    global price_history, timestamps  # Явно указываем, что используем глобальные переменные
    prices = []
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamps.append(current_time)

    for pair, address in PRICE_FEEDS.items():
        data = get_price_feed_data(address)
        if "error" not in data:
            price_history[pair].append(data["price"])
        prices.append(data)

    # Ограничим историю до 50 точек
    for pair in price_history:
        if len(price_history[pair]) > 50:
            price_history[pair] = price_history[pair][-50:]
    if len(timestamps) > 50:
        timestamps = timestamps[-50:]

    return prices


def plot_prices():
    print("\033[H\033[J", end="")  # Очистка консоли
    for pair in price_history:
        if price_history[pair]:
            print(f"\nГрафик цен для {pair}:")
            print(asciichartpy.plot(price_history[pair], {"height": 10, "format": "{:8.2f}"}))
            print(f"Последняя цена: {price_history[pair][-1]:.2f} USD")
            print(f"Время: {timestamps[-1]}")
        else:
            print(f"\nНет данных для {pair}")


def main():
    print("Получение цен из Chainlink Price Feeds в Mantle Network каждые 10 секунд...")
    print("Нажмите Ctrl+C для остановки.")

    try:
        while True:
            prices = get_all_prices()
            for price_data in prices:
                if "error" in price_data:
                    print(f"Ошибка для {price_data['pair']}: {price_data['error']}")
                else:
                    print(f"Пара: {price_data['pair']}, Цена: {price_data['price']:.2f}, Обновлено: {price_data['updated_at']}")

            # Построение графика
            plot_prices()

            # Ожидание 10 секунд
            time.sleep(10)

    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")
        print("Итоговые данные:")
        plot_prices()


if __name__ == "__main__":
    main()