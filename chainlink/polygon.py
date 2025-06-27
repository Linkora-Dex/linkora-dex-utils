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

# Настройки для Polygon Mainnet
POLYGON_RPC_URL = "https://polygon-rpc.com"  # Публичный RPC-узел Polygon
web3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))

# ABI для Chainlink Price Feed (такое же, как выше)
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

# Список адресов Price Feeds для Polygon (обновлено на 1 июня 2025)
# Источник: https://docs.chain.link/data-feeds/price-feeds/addresses?network=polygon
PRICE_FEEDS = {
    "ETH/USD": "0xF9680D99D6C9589e2a93a78A04A279e509205945",
    "BTC/USD": "0xc907E116054Ad103354f2D350FD2514433D57F6f",
    "MATIC/USD": "0xAB594600376Ec9fD91F8e885dADF0CE036862dE0",
    # Добавьте другие пары
}

def get_price_feed_data(feed_address):
    try:
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
    print("Получение цен из Chainlink Price Feeds в Polygon...")
    prices = get_all_prices()
    for price_data in prices:
        if "error" in price_data:
            print(f"Ошибка для {price_data['pair']}: {price_data['error']}")
        else:
            print(f"Пара: {price_data['pair']}, Цена: {price_data['price']}, Обновлено: {price_data['updated_at']}")






