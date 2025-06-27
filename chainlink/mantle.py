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

# Настройки для Mantle Network
MANTLE_RPC_URL = "https://rpc.mantle.xyz"  # Попробуйте также https://rpc.ankr.com/mantle
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

# Список адресов Price Feeds для Mantle Network (замените на актуальные!)
#https://docs.chain.link/data-feeds/price-feeds/addresses?page=1&testnetPage=1&network=mantle
#https://www.mantle.xyz/blog/announcements/mantle-network-joins-chainlink-scale
#https://explorer.mantle.xyz/
PRICE_FEEDS = {
    "ETH/USD": "0x5bc7Cf88EB131DB18b5d7930e793095140799aD5",  # Проверьте адрес
    "BTC/USD": "0x7db2275279F52D0914A481e14c4Ce5a59705A25b",  # Проверьте адрес
    "MNT/USD": "0xD97F20bEbeD74e8144134C4b148fE93417dd0F96",  # Проверьте адрес
}

def get_price_feed_data(feed_address):
    try:
        # Приведение адреса к формату EIP-55
        feed_address = web3.to_checksum_address(feed_address)
        contract = web3.eth.contract(address=feed_address, abi=PRICE_FEED_ABI)
        latest_data = contract.functions.latestRoundData().call()
        decimals = contract.functions.decimals().call()
        description = contract.functions.description().call()
        price = latest_data[1] / 10**decimals
        return {
            "pair": description,
            "price": price,
            "updated_at": latest_data[3]
        }
    except Exception as e:
        return {"pair": feed_address, "error": str(e)}

def get_all_prices():
    prices = []
    for pair, address in PRICE_FEEDS.items():
        data = get_price_feed_data(address)
        prices.append(data)
    return prices

if __name__ == "__main__":
    print("Получение цен из Chainlink Price Feeds в Mantle Network...")
    prices = get_all_prices()
    for price_data in prices:
        if "error" in price_data:
            print(f"Ошибка для {price_data['pair']}: {price_data['error']}")
        else:
            print(f"Пара: {price_data['pair']}, Цена: {price_data['price']}, Обновлено: {price_data['updated_at']}")