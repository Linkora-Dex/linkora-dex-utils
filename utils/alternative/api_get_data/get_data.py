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

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import time
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="numpy")

print(f"Версия pandas: {pd.__version__}")
print(f"Версия requests: {requests.__version__}")
print(f"Версия numpy: {np.__version__}")

print("\nФормат минутных данных (1m) из Binance API:")
print("Каждая свеча содержит 12 элементов, все сохраняются в CSV:")
print("1. timestamp: Время открытия свечи (Unix timestamp в мс)")
print("2. open: Цена открытия")
print("3. high: Максимальная цена за минуту")
print("4. low: Минимальная цена за минуту")
print("5. close: Цена закрытия")
print("6. volume: Объем торгов в ETH")
print("7. close_time: Время закрытия свечи (Unix timestamp в мс)")
print("8. quote_volume: Объем торгов в USDT")
print("9. trades: Количество сделок")
print("10. taker_buy_volume: Объем покупок маркет-тейкерами в ETH")
print("11. taker_buy_quote_volume: Объем покупок маркет-тейкерами в USDT")
print("12. ignore: Зарезервировано, игнорируется")
print("\nСкрипт начнет скачивание данных...\n")


def get_binance_klines(symbol, interval, start_time, end_time, limit=1000):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": int(start_time.timestamp() * 1000),
        "endTime": int(end_time.timestamp() * 1000),
        "limit": limit
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if not data:
            print(f"Пустой ответ от API для периода {start_time} - {end_time}")
        return data
    except requests.RequestException as e:
        print(f"Ошибка запроса к API: {e}")
        return []


symbol = "ETHUSDT"
interval = "1m"
start_date_default = datetime(2020, 1, 2)
end_date = datetime.now()
output_dir = "ETH_USDT"
last_timestamp_file = os.path.join(output_dir, "last_timestamp.txt")

os.makedirs(output_dir, exist_ok=True)

if os.path.exists(last_timestamp_file):
    with open(last_timestamp_file, 'r') as f:
        last_timestamp = f.read().strip()
        start_date = datetime.fromisoformat(last_timestamp) + timedelta(minutes=1)
    print(f"Возобновление с последнего сохраненного времени: {start_date}")
else:
    start_date = start_date_default
    print(f"Начало с даты по умолчанию: {start_date}")

output_file = os.path.join(output_dir, "eth_usdt_1m.csv")
columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
           'quote_volume', 'trades', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']

if not os.path.exists(output_file):
    pd.DataFrame(columns=columns).to_csv(output_file, index=False)

current_time = start_date
while current_time < end_date:
    data = get_binance_klines(symbol, interval, current_time, end_date)
    print(f"Получено {len(data)} записей для периода начиная с {current_time}")

    if not data:
        print("Данные не получены. Пропуск итерации.")
        current_time += timedelta(minutes=1000)
        time.sleep(1)
        continue

    try:
        df = pd.DataFrame(data, columns=columns)

        numeric_columns = ['open', 'high', 'low', 'close', 'volume',
                           'quote_volume', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df['trades'] = pd.to_numeric(df['trades'], errors='coerce', downcast='integer')

        df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
        df['close_time'] = pd.to_numeric(df['close_time'], errors='coerce')

        df = df.dropna()

        if len(df) == 0:
            print("Все записи содержат невалидные данные. Пропуск.")
            current_time += timedelta(minutes=1000)
            time.sleep(1)
            continue

        df.to_csv(output_file, mode='a', header=False, index=False)
        print(f"Сохранено {len(df)} записей")

        last_timestamp_ms = int(df['timestamp'].iloc[-1])
        last_timestamp_dt = datetime.fromtimestamp(last_timestamp_ms / 1000)

        with open(last_timestamp_file, 'w') as f:
            f.write(last_timestamp_dt.isoformat())

        current_time = datetime.fromtimestamp(data[-1][6] / 1000) + timedelta(minutes=1)

    except Exception as e:
        print(f"Ошибка обработки данных: {e}")
        print(f"Данные API: {data[:3] if data else 'Нет данных'}")
        current_time += timedelta(minutes=1000)
        time.sleep(1)
        continue

    time.sleep(1)

print(f"Скачивание завершено. Данные сохранены в {output_file}")