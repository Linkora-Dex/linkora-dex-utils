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
import requests
import pandas as pd
import psycopg2
from datetime import datetime

# Подключение к TimescaleDB
conn = psycopg2.connect("dbname=crypto user=youruser password=yourpass")
cur = conn.cursor()


async def get_coingecko_klines(coin_id="ethereum", vs_currency="usd", days="1", interval="1m"):
    # CoinGecko использует разные эндпоинты в зависимости от периода
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    params = {"vs_currency": vs_currency, "days": days}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        print(data)
        if data:
            # CoinGecko возвращает [timestamp, open, high, low, close]
            columns = ['timestamp', 'open', 'high', 'low', 'close']
            df = pd.DataFrame(data, columns=columns)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = f"{coin_id.upper()}/{vs_currency.upper()}"
            numeric_columns = ['open', 'high', 'low', 'close']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            for _, row in df.iterrows():
                cur.execute("""
                            INSERT INTO candles (timestamp, symbol, open, high, low, close)
                            VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
                            """, (row['timestamp'], row['symbol'], row['open'], row['high'], row['low'], row['close']))
            conn.commit()
            print(f"CoinGecko REST: Сохранено {len(df)} свечей для {row['symbol']}")
        return data
    except requests.RequestException as e:
        print(f"Ошибка REST API CoinGecko: {e}")
        return []


async def coingecko_polling(coin_id="ethereum", vs_currency="usd", days="1", interval="1m"):
    while True:
        await get_coingecko_klines(coin_id, vs_currency, days, interval)
        await asyncio.sleep(20)  # Опрос каждые 20 секунд (CoinGecko лимит: ~50 запросов/минуту)


# Запуск
if __name__ == "__main__":
    asyncio.run(get_coingecko_klines())
    # Раскомментируйте для периодического опроса
    # asyncio.run(coingecko_polling())