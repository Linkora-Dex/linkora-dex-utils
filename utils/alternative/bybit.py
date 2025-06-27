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

import asyncio
import websockets
import json
import psycopg2
from datetime import datetime
import requests

async def get_bybit_klines(symbol="ETHUSDT", interval="1", limit=100):
    url = "https://api.bybit.com/v5/market/kline"
    params = {"category": "spot", "symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    data = response.json()
    print(data)
    if data["retCode"] == 0:
        return data["result"]["list"]
    return []


async def bybit_websocket(symbol="ETHUSDT", interval="1"):
    uri = f"wss://stream.bybit.com/v5/public/spot"
    async with websockets.connect(uri) as websocket:
        # Подписка на канал свечей
        subscribe_msg = {
            "op": "subscribe",
            "args": [f"kline.{interval}.{symbol}"]
        }
        await websocket.send(json.dumps(subscribe_msg))
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                print(data)
            except Exception as e:
                print(f"Ошибка WebSocket Bybit: {e}")
                break

# Запуск
asyncio.run(get_bybit_klines())
# asyncio.run(bybit_websocket())