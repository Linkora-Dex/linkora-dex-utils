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
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple

from web3 import Web3
from web3.exceptions import BlockNotFound, TransactionNotFound

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('polygon_scanner')

ERC20_TRANSFER_EVENT = Web3.keccak(text="Transfer(address,address,uint256)").hex()
ERC721_TRANSFER_EVENT = Web3.keccak(text="Transfer(address,address,uint256)").hex()
ERC1155_TRANSFER_SINGLE_EVENT = Web3.keccak(text="TransferSingle(address,address,address,uint256,uint256)").hex()
ERC1155_TRANSFER_BATCH_EVENT = Web3.keccak(text="TransferBatch(address,address,address,uint256[],uint256[])").hex()


class TokenTransferEvent:

    def __init__(self, tx_hash: str, block_number: int, token_address: str,
                 token_type: str, from_address: str, to_address: str,
                 token_id: Optional[int] = None, value: Optional[int] = None,
                 token_symbol: str = "UNKNOWN", token_decimals: int = 18):
        self.tx_hash = tx_hash
        self.block_number = block_number
        self.token_address = token_address
        self.token_type = token_type
        self.from_address = from_address
        self.to_address = to_address
        self.token_id = token_id
        self.value = value
        self.token_symbol = token_symbol
        self.token_decimals = token_decimals
        self.timestamp = int(time.time())

    def get_formatted_value(self) -> str:
        if self.value is None:
            return "N/A"

        if self.token_type in ['ERC20', 'NATIVE']:
            formatted_value = self.value / (10 ** self.token_decimals)
            return f"{formatted_value:.8f}".rstrip('0').rstrip('.') if '.' in f"{formatted_value:.8f}" else f"{formatted_value:.8f}"
        else:
            return str(self.value)

    def __str__(self):
        if self.token_type in ['ERC20', 'NATIVE']:
            return (f"[{self.token_type}] Block: {self.block_number} | "
                    f"Tx: {self.tx_hash} | Token: {self.token_symbol} ({self.token_address}) | "
                    f"From: {self.from_address} | To: {self.to_address} | "
                    f"Value: {self.get_formatted_value()} {self.token_symbol}")
        else:
            return (f"[{self.token_type}] Block: {self.block_number} | "
                    f"Tx: {self.tx_hash} | Token: {self.token_symbol} ({self.token_address}) | "
                    f"From: {self.from_address} | To: {self.to_address} | "
                    f"TokenID: {self.token_id} | Value: {self.get_formatted_value()}")


class BalanceChangeEvent:

    def __init__(self, wallet_address: str, token_address: str, token_type: str,
                 old_balance: int, new_balance: int, block_number: int,
                 token_symbol: str = "UNKNOWN", token_decimals: int = 18):
        self.wallet_address = wallet_address
        self.token_address = token_address
        self.token_type = token_type
        self.old_balance = old_balance
        self.new_balance = new_balance
        self.change = new_balance - old_balance
        self.block_number = block_number
        self.token_symbol = token_symbol
        self.token_decimals = token_decimals
        self.timestamp = int(time.time())

    def get_formatted_change(self) -> str:
        if self.token_type in ['ERC20', 'NATIVE']:
            formatted_change = self.change / (10 ** self.token_decimals)
            return f"{formatted_change:+.8f}".rstrip('0').rstrip('.') if '.' in f"{formatted_change:+.8f}" else f"{formatted_change:+.8f}"
        else:
            return f"{self.change:+d}"

    def __str__(self):
        return (f"[BALANCE] Address: {self.wallet_address} | "
                f"Token: {self.token_symbol} ({self.token_address}) | "
                f"Change: {self.get_formatted_change()} {self.token_symbol} | "
                f"Block: {self.block_number}")


class PolygonScanner:

    def __init__(self, wallet_addresses: List[str], start_block: Optional[int] = None,
                 scan_interval: int = 30, balance_check_interval: int = 300):
        # Конвертируем адреса в checksum формат и сохраняем оба варианта
        self.wallet_addresses_original = [Web3.to_checksum_address(addr) for addr in wallet_addresses]
        self.wallet_addresses = [addr.lower() for addr in self.wallet_addresses_original]
        self.wallet_set = set(self.wallet_addresses)
        self.scan_interval = scan_interval
        self.balance_check_interval = balance_check_interval
        self.token_info_cache = {}
        self.wallet_balances = {}
        self.tracked_tokens = set()

        # ankr_rpc_url = "https://rpc.ankr.com/polygon/fb00ba52a7de8c2eb4acca0df5590553673491333704db7739fbdf8a40d0f1ad" #poligon

        ankr_rpc_url = "https://rpc.ankr.com/bsc/fb00ba52a7de8c2eb4acca0df5590553673491333704db7739fbdf8a40d0f1ad"  # bnd

        self.w3 = Web3(Web3.HTTPProvider(ankr_rpc_url))

        # Добавляем POA middleware для BSC/Polygon
        try:
            # Попытка использовать новый POA middleware
            from web3.middleware import ExtraDataToPOAMiddleware
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            logger.info("Успешно добавлен ExtraDataToPOAMiddleware")
        except ImportError:
            try:
                # Альтернативный способ
                from web3.middleware import construct_simple_cache_middleware
                cache_middleware = construct_simple_cache_middleware()
                self.w3.middleware_onion.add(cache_middleware)
                logger.info("Добавлен cache middleware вместо POA middleware")
            except ImportError:
                logger.warning("POA middleware недоступен, возможны проблемы с POA сетями")

        if not self.w3.is_connected():
            raise ConnectionError("Не удалось подключиться к блокчейну")

        self.chain_id = self.w3.eth.chain_id
        logger.info(f"Успешное подключение к сети. Chain ID: {self.chain_id}")

        self.native_currency = self._get_native_currency_info()
        logger.info(f"Нативная валюта сети: {self.native_currency['symbol']}")

        self.last_processed_block = start_block or self.w3.eth.block_number - 10
        logger.info(f"Начало сканирования с блока {self.last_processed_block}")

    def _get_native_currency_info(self) -> Dict[str, Any]:
        if self.chain_id == 56:  # BSC
            return {"symbol": "BNB", "decimals": 18}
        elif self.chain_id == 137:  # Polygon
            return {"symbol": "MATIC", "decimals": 18}
        else:
            logger.warning(f"Неизвестная сеть с Chain ID {self.chain_id}, используем стандартные параметры")
            return {"symbol": "NATIVE", "decimals": 18}

    async def run(self):
        balance_check_task = asyncio.create_task(self.check_balances_loop())
        scan_task = asyncio.create_task(self.scan_blocks_loop())

        await asyncio.gather(scan_task, balance_check_task)

    async def check_balances_loop(self):
        await self.initialize_balances()

        while True:
            try:
                logger.info("Проверка изменений балансов...")
                current_block = self.w3.eth.block_number

                for wallet_address in self.wallet_addresses_original:
                    await self.check_native_balance(wallet_address, current_block)

                    for token_address in self.tracked_tokens:
                        await self.check_token_balance(wallet_address, token_address, current_block)

                await asyncio.sleep(self.balance_check_interval)
            except Exception as e:
                logger.error(f"Ошибка при проверке балансов: {str(e)}")
                await asyncio.sleep(5)

    async def initialize_balances(self):
        logger.info("Инициализация начальных балансов...")
        current_block = self.w3.eth.block_number

        for wallet_address in self.wallet_addresses_original:
            # Инициализация баланса нативной валюты
            balance_key = f"{wallet_address.lower()}:NATIVE"
            balance = await asyncio.to_thread(self.w3.eth.get_balance, wallet_address)
            self.wallet_balances[balance_key] = balance
            logger.info(f"Начальный баланс {self.native_currency['symbol']} для {wallet_address}: {balance / (10 ** self.native_currency['decimals'])}")

    async def check_native_balance(self, wallet_address: str, block_number: int):
        balance_key = f"{wallet_address.lower()}:NATIVE"
        old_balance = self.wallet_balances.get(balance_key, 0)

        try:
            new_balance = await asyncio.to_thread(self.w3.eth.get_balance, wallet_address)

            if new_balance != old_balance:
                event = BalanceChangeEvent(
                    wallet_address=wallet_address.lower(),
                    token_address="NATIVE",
                    token_type="NATIVE",
                    old_balance=old_balance,
                    new_balance=new_balance,
                    block_number=block_number,
                    token_symbol=self.native_currency["symbol"],
                    token_decimals=self.native_currency["decimals"]
                )
                print(event)
                logger.info(f"Обнаружено изменение баланса нативной валюты: {event}")

                self.wallet_balances[balance_key] = new_balance
        except Exception as e:
            logger.error(f"Ошибка при проверке нативного баланса {wallet_address}: {str(e)}")

    async def check_token_balance(self, wallet_address: str, token_address: str, block_number: int):
        balance_key = f"{wallet_address.lower()}:{token_address}"
        old_balance = self.wallet_balances.get(balance_key, 0)

        try:
            token_type = await self._determine_token_type(token_address)
            token_symbol, token_decimals = await self._get_token_info(token_address, token_type)

            if token_type == 'ERC20':
                checksum_address = Web3.to_checksum_address(token_address)
                erc20_abi = [
                    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
                     "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}],
                     "type": "function"}
                ]

                contract = self.w3.eth.contract(address=checksum_address, abi=erc20_abi)
                new_balance = await asyncio.to_thread(
                    contract.functions.balanceOf(wallet_address).call
                )

                if new_balance != old_balance:
                    event = BalanceChangeEvent(
                        wallet_address=wallet_address.lower(),
                        token_address=token_address,
                        token_type=token_type,
                        old_balance=old_balance,
                        new_balance=new_balance,
                        block_number=block_number,
                        token_symbol=token_symbol,
                        token_decimals=token_decimals
                    )
                    print(event)
                    logger.info(f"Обнаружено изменение баланса ERC20: {event}")

                    self.wallet_balances[balance_key] = new_balance

        except Exception as e:
            logger.error(f"Ошибка при проверке баланса токена {token_address} для {wallet_address}: {str(e)}")

    async def scan_blocks_loop(self):
        while True:
            try:
                current_block = self.w3.eth.block_number
                if current_block > self.last_processed_block:
                    logger.info(f"Сканирование блоков с {self.last_processed_block + 1} по {current_block}")
                    await self.process_blocks(self.last_processed_block + 1, current_block)
                    self.last_processed_block = current_block
                else:
                    logger.info(f"Ожидание новых блоков. Текущий блок: {current_block}")

                await asyncio.sleep(self.scan_interval)
            except Exception as e:
                logger.error(f"Ошибка в цикле сканирования: {str(e)}")
                await asyncio.sleep(5)

    async def process_blocks(self, from_block: int, to_block: int):
        tasks = [self.process_block(block_num) for block_num in range(from_block, to_block + 1)]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def process_block(self, block_number: int):
        try:
            # Используем альтернативный способ получения блока для POA сетей
            block = await asyncio.to_thread(self._safe_get_block, block_number)
            if not block:
                return

            for tx in block.transactions:
                await self.process_transaction(tx, block_number)

        except BlockNotFound:
            logger.warning(f"Блок {block_number} не найден")
        except Exception as e:
            logger.error(f"Ошибка при обработке блока {block_number}: {str(e)}")

    def _safe_get_block(self, block_number: int):
        """Безопасное получение блока с обработкой POA специфики"""
        try:
            return self.w3.eth.get_block(block_number, full_transactions=True)
        except ValueError as e:
            if "extraData" in str(e):
                logger.debug(f"POA блок {block_number}, пропускаем из-за extraData")
                return None
            raise e

    async def process_transaction(self, tx, block_number: int):
        tx_hash = tx['hash'].hex()
        try:
            from_address = tx['from'].lower()
            to_address = tx.get('to', '').lower() if tx.get('to') else None

            if from_address in self.wallet_set or to_address in self.wallet_set:
                # Проверка на нативный перевод
                if to_address and tx.get('value', 0) > 0 and (not tx.get('input') or tx.get('input') == '0x'):
                    value = tx.get('value', 0)
                    event = TokenTransferEvent(
                        tx_hash=tx_hash,
                        block_number=block_number,
                        token_address="NATIVE",
                        token_type="NATIVE",
                        from_address=from_address,
                        to_address=to_address,
                        value=value,
                        token_symbol=self.native_currency["symbol"],
                        token_decimals=self.native_currency["decimals"]
                    )
                    print(event)
                    logger.info(f"Обнаружен нативный перевод: {event}")

                try:
                    receipt = await asyncio.to_thread(self.w3.eth.get_transaction_receipt, tx_hash)
                except TransactionNotFound:
                    logger.debug(f"Транзакция {tx_hash} не найдена, пропускаем")
                    return

                if not receipt or not hasattr(receipt, 'logs'):
                    logger.debug(f"Отсутствуют логи для транзакции {tx_hash}")
                    return

                for log in receipt.logs:
                    contract_address = log['address'].lower()
                    topics = [t.hex() if isinstance(t, bytes) else t for t in log['topics']]

                    if not topics:
                        continue

                    event_signature = topics[0]

                    if event_signature == ERC20_TRANSFER_EVENT:
                        if len(topics) >= 3:
                            from_addr = '0x' + topics[1][26:].lower()
                            to_addr = '0x' + topics[2][26:].lower()

                            if from_addr in self.wallet_set or to_addr in self.wallet_set:
                                # Добавляем токен в список отслеживаемых
                                self.tracked_tokens.add(contract_address)

                                token_type = await self._determine_token_type(contract_address)
                                token_symbol, token_decimals = await self._get_token_info(contract_address, token_type)

                                data_str = self._normalize_data(log['data'])

                                if token_type == 'ERC721':
                                    try:
                                        token_id = int(data_str, 16) if data_str != '0x' else None
                                    except ValueError:
                                        logger.warning(f"Невозможно преобразовать данные в токен ID: {data_str}")
                                        token_id = None

                                    event = TokenTransferEvent(
                                        tx_hash=tx_hash,
                                        block_number=block_number,
                                        token_address=contract_address,
                                        token_type='ERC721',
                                        from_address=from_addr,
                                        to_address=to_addr,
                                        token_id=token_id,
                                        value=1,
                                        token_symbol=token_symbol,
                                        token_decimals=0
                                    )
                                else:
                                    try:
                                        value = int(data_str, 16) if data_str != '0x' else 0
                                    except ValueError:
                                        logger.warning(f"Невозможно преобразовать данные в значение: {data_str}")
                                        value = 0

                                    event = TokenTransferEvent(
                                        tx_hash=tx_hash,
                                        block_number=block_number,
                                        token_address=contract_address,
                                        token_type='ERC20',
                                        from_address=from_addr,
                                        to_address=to_addr,
                                        value=value,
                                        token_symbol=token_symbol,
                                        token_decimals=token_decimals
                                    )

                                print(event)

                                # Обновляем состояние баланса после обнаружения перевода
                                for wallet in [from_addr, to_addr]:
                                    if wallet in self.wallet_set:
                                        # Находим соответствующий checksum адрес
                                        checksum_wallet = None
                                        for orig_addr in self.wallet_addresses_original:
                                            if orig_addr.lower() == wallet:
                                                checksum_wallet = orig_addr
                                                break

                                        if checksum_wallet:
                                            balance_key = f"{wallet}:{contract_address}"
                                            try:
                                                if token_type == 'ERC20':
                                                    checksum_address = Web3.to_checksum_address(contract_address)
                                                    erc20_abi = [
                                                        {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
                                                         "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}],
                                                         "type": "function"}
                                                    ]

                                                    contract = self.w3.eth.contract(address=checksum_address, abi=erc20_abi)
                                                    new_balance = await asyncio.to_thread(
                                                        contract.functions.balanceOf(checksum_wallet).call
                                                    )
                                                    self.wallet_balances[balance_key] = new_balance
                                                    logger.debug(f"Обновлен баланс: {wallet} {token_symbol} = {new_balance / (10 ** token_decimals)}")
                                            except Exception as e:
                                                logger.error(f"Ошибка при обновлении баланса: {str(e)}")

                    elif event_signature == ERC1155_TRANSFER_SINGLE_EVENT:
                        if len(topics) >= 4:
                            from_addr = '0x' + topics[2][26:].lower()
                            to_addr = '0x' + topics[3][26:].lower()

                            if from_addr in self.wallet_set or to_addr in self.wallet_set:
                                # Добавляем токен в список отслеживаемых
                                self.tracked_tokens.add(contract_address)

                                token_symbol, token_decimals = await self._get_token_info(contract_address, 'ERC1155')
                                data_str = self._normalize_data(log['data'])
                                if data_str.startswith('0x'):
                                    data_str = data_str[2:]

                                if len(data_str) >= 128:
                                    try:
                                        token_id = int(data_str[:64], 16)
                                        value = int(data_str[64:128], 16)
                                    except ValueError as e:
                                        logger.warning(f"Ошибка при преобразовании данных ERC1155: {str(e)}")
                                        token_id = 0
                                        value = 0

                                    event = TokenTransferEvent(
                                        tx_hash=tx_hash,
                                        block_number=block_number,
                                        token_address=contract_address,
                                        token_type='ERC1155',
                                        from_address=from_addr,
                                        to_address=to_addr,
                                        token_id=token_id,
                                        value=value,
                                        token_symbol=token_symbol,
                                        token_decimals=0
                                    )
                                    print(event)

                    elif event_signature == ERC1155_TRANSFER_BATCH_EVENT:
                        if len(topics) >= 4:
                            from_addr = '0x' + topics[2][26:].lower()
                            to_addr = '0x' + topics[3][26:].lower()

                            if from_addr in self.wallet_set or to_addr in self.wallet_set:
                                # Добавляем токен в список отслеживаемых
                                self.tracked_tokens.add(contract_address)

                                token_symbol, token_decimals = await self._get_token_info(contract_address, 'ERC1155')
                                event = TokenTransferEvent(
                                    tx_hash=tx_hash,
                                    block_number=block_number,
                                    token_address=contract_address,
                                    token_type='ERC1155-Batch',
                                    from_address=from_addr,
                                    to_address=to_addr,
                                    token_id=None,
                                    value=None,
                                    token_symbol=token_symbol,
                                    token_decimals=0
                                )
                                print(f"{event} (Batch transfer - подробности в транзакции)")

        except TransactionNotFound:
            logger.debug(f"Транзакция {tx_hash} не найдена при обработке")
        except Exception as e:
            logger.error(f"Ошибка при обработке транзакции {tx_hash}: {str(e)}")

    def _normalize_data(self, data) -> str:
        if isinstance(data, bytes):
            data_hex = data.hex()
            if not data_hex.startswith('0x'):
                data_hex = '0x' + data_hex
            return data_hex
        elif isinstance(data, str):
            if not data.startswith('0x'):
                return '0x' + data
            return data
        else:
            return '0x' + str(data)

    async def _determine_token_type(self, contract_address: str) -> str:
        try:
            checksum_address = Web3.to_checksum_address(contract_address)
            abi = [{"constant": True, "inputs": [{"name": "interfaceId", "type": "bytes4"}],
                    "name": "supportsInterface", "outputs": [{"name": "", "type": "bool"}],
                    "payable": False, "stateMutability": "view", "type": "function"}]

            contract = self.w3.eth.contract(address=checksum_address, abi=abi)

            try:
                supports_erc721 = await asyncio.to_thread(
                    contract.functions.supportsInterface(Web3.to_bytes(hexstr='0x80ac58cd')).call
                )
                if supports_erc721:
                    return 'ERC721'

                supports_erc1155 = await asyncio.to_thread(
                    contract.functions.supportsInterface(Web3.to_bytes(hexstr='0xd9b67a26')).call
                )
                if supports_erc1155:
                    return 'ERC1155'
            except Exception:
                pass

            erc20_abi = [
                {"constant": True, "inputs": [], "name": "decimals",
                 "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
                {"constant": True, "inputs": [], "name": "symbol",
                 "outputs": [{"name": "", "type": "string"}], "type": "function"}
            ]

            erc20_contract = self.w3.eth.contract(address=checksum_address, abi=erc20_abi)
            try:
                await asyncio.to_thread(erc20_contract.functions.decimals().call) or \
                await asyncio.to_thread(erc20_contract.functions.symbol().call)
                return 'ERC20'
            except Exception:
                pass

            return 'ERC20'
        except Exception as e:
            logger.debug(f"Ошибка определения типа токена {contract_address}: {str(e)}")
            return 'ERC20'

    async def _get_token_info(self, contract_address: str, token_type: str) -> Tuple[str, int]:
        cache_key = contract_address.lower()
        if cache_key in self.token_info_cache:
            return self.token_info_cache[cache_key]

        symbol = "UNKNOWN"
        decimals = 18

        try:
            checksum_address = Web3.to_checksum_address(contract_address)

            if token_type == 'ERC20':
                erc20_abi = [
                    {"constant": True, "inputs": [], "name": "decimals",
                     "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
                    {"constant": True, "inputs": [], "name": "symbol",
                     "outputs": [{"name": "", "type": "string"}], "type": "function"}
                ]

                contract = self.w3.eth.contract(address=checksum_address, abi=erc20_abi)

                try:
                    symbol = await asyncio.to_thread(contract.functions.symbol().call)
                except Exception as e:
                    logger.debug(f"Не удалось получить символ токена {contract_address}: {str(e)}")

                try:
                    decimals = await asyncio.to_thread(contract.functions.decimals().call)
                except Exception as e:
                    logger.debug(f"Не удалось получить decimals токена {contract_address}: {str(e)}")

            elif token_type in ['ERC721', 'ERC1155']:
                nft_abi = [
                    {"constant": True, "inputs": [], "name": "symbol",
                     "outputs": [{"name": "", "type": "string"}], "type": "function"},
                    {"constant": True, "inputs": [], "name": "name",
                     "outputs": [{"name": "", "type": "string"}], "type": "function"}
                ]

                contract = self.w3.eth.contract(address=checksum_address, abi=nft_abi)

                try:
                    symbol = await asyncio.to_thread(contract.functions.symbol().call)
                except Exception:
                    try:
                        symbol = await asyncio.to_thread(contract.functions.name().call)
                    except Exception as e:
                        logger.debug(f"Не удалось получить имя/символ NFT {contract_address}: {str(e)}")
                        symbol = f"{token_type}-{contract_address[-6:]}"

                decimals = 0

            self.token_info_cache[cache_key] = (symbol, decimals)
            return symbol, decimals

        except Exception as e:
            logger.warning(f"Ошибка при получении информации о токене {contract_address}: {str(e)}")
            self.token_info_cache[cache_key] = (symbol, decimals)
            return symbol, decimals


async def main():
    wallets = [
        # '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        # '0x123456789abcdef123456789abcdef123456789a',
        # '0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff',
        # '0x8dFf5E27EA6b7A60262716b3c4f4b81c8c4aB2b9',
        # '0x2953399124F0cBB46d2CbACD8A89cF0599974963',
        # '0x40ec5B33f54e0E8A33A975908C5BA1c14e5BbbDf',
        # '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
        '0x9320D18D37777F6897aaa57Df36251633A5925D2',
        '0x6d3dED44834e559D0238A0622A82DAB845E66CAd'
    ]

    scanner = PolygonScanner(wallets, balance_check_interval=300)

    logger.info("Запуск сканера блокчейна")
    await scanner.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Сканирование остановлено пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}")