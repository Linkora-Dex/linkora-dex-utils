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

# Конфигурация
RPC_URL = "https://rpc.ankr.com/polygon/fb00ba52a7de8c2eb4acca0df5590553673491333704db7739fbdf8a40d0f1ad"
USER1 = os.getenv('USER1')
USER1_PRIVATE_KEY = os.getenv('USER1_PRIVATE_KEY')

# Подключение к сети
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Проверка подключения и получение баланса
if w3.is_connected():
   balance_wei = w3.eth.get_balance(USER1)
   balance_matic = w3.from_wei(balance_wei, 'ether')
   print(f"Баланс: {balance_matic} MATIC")
else:
   print("Ошибка подключения к сети")