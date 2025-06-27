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
import requests
import pandas as pd
from datetime import datetime

# Подключение к TimescaleDB
conn = psycopg2.connect("dbname=crypto user=youruser password=yourpass")
cur = conn.cursor()


async def get_binance_klines(symbol="ETHUSDT", interval="1m", limit=100):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        print(data)
        if data:
            columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                       'quote_volume', 'trades', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
            df = pd.DataFrame(data, columns=columns)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_volume',
                               'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['trades'] = pd.to_numeric(df['trades'], errors='coerce', downcast='integer')

            for _, row in df.iterrows():
                cur.execute("""
                            INSERT INTO candles (timestamp, symbol, open, high, low, close, volume,
                                                 close_time, quote_volume, trades, taker_buy_volume,
                                                 taker_buy_quote_volume, ignore)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
                            """, (row['timestamp'], symbol, row['open'], row['high'], row['low'], row['close'],
                                  row['volume'], row['close_time'], row['quote_volume'], row['trades'],
                                  row['taker_buy_volume'], row['taker_buy_quote_volume'], row['ignore']))
            conn.commit()
            print(f"Binance REST: Сохранено {len(df)} свечей для {symbol}")
        return data
    except requests.RequestException as e:
        print(f"Ошибка REST API Binance: {e}")
        return []


async def binance_websocket(symbol="ethusdt", interval="1m"):
    uri = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_{interval}"
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                print(data)
                if data.get('k') and data['k']['x']:  # Закрытая свеча
                    kline = data['k']
                    timestamp = pd.to_datetime(kline['t'], unit='ms')
                    open_price = float(kline['o'])
                    high_price = float(kline['h'])
                    low_price = float(kline['l'])
                    close_price = float(kline['c'])
                    volume = float(kline['v'])
                    close_time = pd.to_datetime(kline['T'], unit='ms')
                    quote_volume = float(kline['q'])
                    trades = int(kline['n'])
                    taker_buy_volume = float(kline['V'])
                    taker_buy_quote_volume = float(kline['Q'])
                    ignore = float(kline['B'])

                    cur.execute("""
                                INSERT INTO candles (timestamp, symbol, open, high, low, close, volume,
                                                     close_time, quote_volume, trades, taker_buy_volume,
                                                     taker_buy_quote_volume, ignore)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
                                """, (timestamp, symbol.upper(), open_price, high_price, low_price, close_price,
                                      volume, close_time, quote_volume, trades, taker_buy_volume,
                                      taker_buy_quote_volume, ignore))
                    conn.commit()
                    print(f"Binance WebSocket: Сохранена свеча: {timestamp}, {close_price}")
            except Exception as e:
                print(f"Ошибка WebSocket Binance: {e}")
                break


# Запуск
if __name__ == "__main__":
    # Запустите REST API для исторических данных
    asyncio.run(get_binance_klines())
    # Раскомментируйте для WebSocket
    # asyncio.run(binance_websocket())