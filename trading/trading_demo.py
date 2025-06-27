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
import os
import json
from typing import Dict, List, Optional, Tuple
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

from demo_config import DemoConfigManager
from config import ConfigManager
from contracts import ContractManager


class TradingDemo:
    def __init__(self, config_path: str = "../config/anvil_final-config.json"):
        load_dotenv()
        self.demo_config = DemoConfigManager(config_path)
        self.keeper_config = ConfigManager(config_path)
        self.logger = self._setup_logging()
        self._setup_web3()
        self._setup_accounts()
        self.contract_manager = ContractManager(self.w3, self.keeper_config)
        self.created_orders = []
        self.tokens = {}
        self._load_token_contracts()
        self.eth_address = "0x0000000000000000000000000000000000000000"

    def _setup_logging(self):
        logging.basicConfig(
            level=getattr(logging, self.demo_config.config.log_level),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def _setup_web3(self):
        rpc_url = os.getenv('RPC_URL', 'http://localhost:8545')
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {rpc_url}")
        self.logger.info(f"Connected to network: {self.w3.eth.chain_id}")

    def _setup_accounts(self):
        required_keys = ['USER1_PRIVATE_KEY', 'USER2_PRIVATE_KEY', 'ANVIL_KEEPER_PRIVATE_KEY', 'ANVIL_DEPLOYER_PRIVATE_KEY']
        keys = {}

        for key_name in required_keys:
            key = os.getenv(key_name)
            if not key:
                raise ValueError(f"Missing {key_name} in environment")
            keys[key_name] = key if key.startswith('0x') else '0x' + key

        self.user1 = Account.from_key(keys['USER1_PRIVATE_KEY'])
        self.user2 = Account.from_key(keys['USER2_PRIVATE_KEY'])
        self.keeper = Account.from_key(keys['ANVIL_KEEPER_PRIVATE_KEY'])
        self.deployer = Account.from_key(keys['ANVIL_DEPLOYER_PRIVATE_KEY'])

        self.logger.info(f"Accounts loaded:")
        self.logger.info(f"  User1: {self.user1.address}")
        self.logger.info(f"  User2: {self.user2.address}")
        self.logger.info(f"  Keeper: {self.keeper.address}")
        self.logger.info(f"  Deployer: {self.deployer.address}")

    def _load_token_contracts(self):
        mock_erc20_abi = [
            {
                "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "account", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
                "name": "mint",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]

        for symbol, token_config in self.demo_config.get_all_tokens().items():
            address = token_config.get('address')
            if address:
                try:
                    contract = self.w3.eth.contract(
                        address=Web3.to_checksum_address(address),
                        abi=mock_erc20_abi
                    )
                    self.tokens[symbol] = contract
                    self.logger.debug(f"Loaded token {symbol} at {address}")
                except Exception as e:
                    self.logger.error(f"Failed to load token {symbol}: {e}")

    def _build_and_send_transaction(self, contract_function, user_account, value=0, gas_limit=None) -> Tuple[bool, str, Optional[dict]]:
        """Построение и отправка транзакции с proper signing"""
        try:
            nonce = self.w3.eth.get_transaction_count(user_account.address, 'pending')

            transaction = contract_function.build_transaction({
                'from': user_account.address,
                'value': value,
                'gas': gas_limit or 500000,
                'gasPrice': min(self.w3.eth.gas_price, 50000000000),
                'nonce': nonce
            })

            signed_txn = self.w3.eth.account.sign_transaction(transaction, user_account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            return receipt.status == 1, tx_hash.hex(), receipt

        except Exception as e:
            self.logger.error(f"Transaction failed: {e}")
            return False, None, None

    def _get_pool_abi(self):
        """Получение ABI для Pool контракта"""
        try:
            base_path = self.keeper_config.config_path.parent.parent
            abi_path = base_path / 'artifacts/contracts/upgradeable/PoolUpgradeable.sol/PoolUpgradeable.json'
            with open(abi_path, 'r') as f:
                contract_json = json.load(f)
            return contract_json.get('abi', [])
        except Exception as e:
            self.logger.warning(f"Could not load Pool ABI: {e}")
            return []

    async def diagnose_system_state(self) -> bool:
        """Полная диагностика состояния системы"""
        self.logger.info("\n🔍 SYSTEM DIAGNOSTICS")

        try:
            chain_id = self.w3.eth.chain_id
            latest_block = self.w3.eth.block_number
            gas_price = self.w3.eth.gas_price

            self.logger.info(f"Network: Chain {chain_id}, Block {latest_block}, Gas {Web3.from_wei(gas_price, 'gwei')} gwei")

            router = self.contract_manager.get_router()
            if not router:
                self.logger.error("❌ Router contract not available")
                return False

            # Проверка ролей Router в Pool
            try:
                pool_address = self.keeper_config.get_contract_address('Pool')
                if pool_address:
                    pool_abi = self._get_pool_abi()
                    if pool_abi:
                        pool = self.w3.eth.contract(
                            address=Web3.to_checksum_address(pool_address),
                            abi=pool_abi
                        )

                        keeper_role = self.w3.keccak(text="KEEPER_ROLE")
                        has_role = pool.functions.hasRole(keeper_role, router.address).call()
                        self.logger.info(f"Router KEEPER_ROLE in Pool: {'✅ GRANTED' if has_role else '❌ MISSING'}")

                        if not has_role:
                            self.logger.error("❌ Router missing KEEPER_ROLE in Pool - transactions will fail")
                            return False
            except Exception as e:
                self.logger.warning(f"⚠️ Could not verify roles: {e}")

            # Проверка баланса Router (пула)
            router_balance = self.w3.eth.get_balance(router.address)
            self.logger.info(f"Router ETH balance: {Web3.from_wei(router_balance, 'ether'):.6f} ETH")

            # Проверка emergency pause
            emergency_paused = await self._check_emergency_pause()
            self.logger.info(f"Emergency pause: {'🔴 ACTIVE' if emergency_paused else '🟢 INACTIVE'}")

            # Проверка балансов пользователей
            for user_name, user in [("User1", self.user1), ("User2", self.user2), ("Deployer", self.deployer)]:
                eth_balance = self.w3.eth.get_balance(user.address)
                try:
                    pool_balance = router.functions.getBalance(user.address, self.eth_address).call()
                    self.logger.info(f"{user_name}: Wallet {Web3.from_wei(eth_balance, 'ether'):.6f} ETH, Pool {Web3.from_wei(pool_balance, 'ether'):.6f} ETH")
                except Exception as e:
                    self.logger.warning(f"{user_name}: Wallet {Web3.from_wei(eth_balance, 'ether'):.6f} ETH, Pool check failed: {e}")

            return True

        except Exception as e:
            self.logger.error(f"❌ System diagnosis failed: {e}")
            return False

    async def _ensure_pool_liquidity(self):
        """Проверка и инициализация ликвидности пула"""
        self.logger.info("\n🏊 CHECKING POOL LIQUIDITY")

        router = self.contract_manager.get_router()
        if not router:
            raise Exception("Router contract not available")

        # Проверка ETH в пуле через Router balance
        pool_eth_balance = self.w3.eth.get_balance(router.address)
        self.logger.info(f"Current pool ETH balance: {Web3.from_wei(pool_eth_balance, 'ether'):.6f} ETH")

        # Если пул пустой - инициализируем
        if pool_eth_balance < Web3.to_wei("0.1", 'ether'):
            self.logger.info("🔧 Pool empty, initializing liquidity from deployer...")

            # Проверка баланса deployer
            deployer_balance = self.w3.eth.get_balance(self.deployer.address)
            self.logger.info(f"Deployer wallet balance: {Web3.from_wei(deployer_balance, 'ether'):.6f} ETH")

            if deployer_balance < Web3.to_wei("11", 'ether'):
                raise Exception(f"Deployer has insufficient ETH balance for pool initialization")

            # Добавляем ETH ликвидность от deployer
            eth_liquidity = Web3.to_wei("10", 'ether')
            success, tx_hash, receipt = self._build_and_send_transaction(
                router.functions.depositETH(),
                self.deployer,
                value=eth_liquidity
            )

            if success:
                self.logger.info(f"✅ Added {Web3.from_wei(eth_liquidity, 'ether')} ETH to pool - TX: {tx_hash}")
            else:
                raise Exception(f"❌ Failed to add ETH liquidity - TX: {tx_hash}")

            # Добавляем токен ликвидность
            await self._add_initial_token_liquidity()

            self.logger.info("✅ Pool liquidity initialization complete")
        else:
            self.logger.info("✅ Pool has sufficient liquidity")

    async def _add_initial_token_liquidity(self):
        """Добавление начальной ликвидности токенов от deployer"""
        router = self.contract_manager.get_router()

        for symbol, token_config in self.demo_config.get_all_tokens().items():
            try:
                token_contract = self.tokens.get(symbol)
                if not token_contract:
                    self.logger.warning(f"⚠️ Token contract {symbol} not available")
                    continue

                decimals = token_config.get('decimals', 18)
                liquidity_amount = 1000 * (10 ** decimals)  # 1000 токенов

                # Проверка баланса deployer и минт если нужно
                deployer_balance = token_contract.functions.balanceOf(self.deployer.address).call()
                if deployer_balance < liquidity_amount:
                    mint_amount = liquidity_amount * 2
                    success, tx_hash, receipt = self._build_and_send_transaction(
                        token_contract.functions.mint(self.deployer.address, mint_amount),
                        self.deployer
                    )
                    if not success:
                        self.logger.error(f"❌ Failed to mint {symbol} for deployer")
                        continue
                    self.logger.debug(f"Minted {mint_amount / (10 ** decimals)} {symbol} for deployer")

                # Approve Router
                success, tx_hash, receipt = self._build_and_send_transaction(
                    token_contract.functions.approve(router.address, liquidity_amount),
                    self.deployer
                )
                if not success:
                    self.logger.error(f"❌ Failed to approve {symbol} for Router")
                    continue

                # Депозит в пул
                success, tx_hash, receipt = self._build_and_send_transaction(
                    router.functions.depositToken(token_config['address'], liquidity_amount),
                    self.deployer
                )

                if success:
                    formatted_amount = liquidity_amount / (10 ** decimals)
                    self.logger.info(f"✅ Added {formatted_amount} {symbol} to pool")
                else:
                    self.logger.error(f"❌ Failed to add {symbol} liquidity")

            except Exception as e:
                self.logger.error(f"❌ {symbol} liquidity initialization failed: {e}")

    async def _check_emergency_pause(self) -> bool:
        """Проверка состояния emergency pause"""
        try:
            access_control_addr = self.keeper_config.get_contract_address('AccessControl')
            if access_control_addr:
                return self.contract_manager.is_emergency_paused()
            return False
        except:
            return False

    async def run_demo(self):
        """Основной запуск демо"""
        try:
            self._print_header()

            # Диагностика системы
            system_ok = await self.diagnose_system_state()
            if not system_ok:
                self.logger.error("❌ System diagnostics failed, aborting demo")
                return

            # Инициализация ликвидности пула
            await self._ensure_pool_liquidity()

            # Проверка цен Oracle
            await self._check_oracle_prices()

            # Выполнение фаз демо
            for phase_name, phase in self.demo_config.config.phases.items():
                if phase.enabled:
                    self.logger.info(f"\n⏳ Starting phase: {phase.name}")
                    await getattr(self, f'_phase_{phase_name}')()
                    await asyncio.sleep(phase.sleep_after)

            self._print_completion()
        except KeyboardInterrupt:
            self.logger.info("🛑 Demo interrupted by user")
        except Exception as e:
            self.logger.error(f"❌ Demo failed: {e}")
            raise

    def _print_header(self):
        self.logger.info("🚀 Enhanced Trading Demo Starting...")
        self.logger.info(f"Network: Chain {self.w3.eth.chain_id}")
        self.logger.info("Features: Router-Centric | Pool Liquidity | Advanced Orders | Security")

    async def _check_oracle_prices(self):
        """Проверка цен в Oracle"""
        self.logger.info("\n🔍 CHECKING ORACLE PRICES")
        try:
            # ETH price
            eth_price = await self._get_price(self.eth_address)
            self.logger.info(f"ETH price: ${eth_price:.2f}")

            # Token prices
            for symbol, token_config in self.demo_config.get_all_tokens().items():
                price = await self._get_price(token_config['address'])
                self.logger.info(f"{symbol} price: ${price:.6f}")
        except Exception as e:
            self.logger.error(f"❌ Failed to check Oracle prices: {e}")

    async def _get_price(self, token_address: str) -> float:
        """Получение цены токена из Oracle"""
        try:
            price = self.contract_manager.get_price(token_address)
            return float(Web3.from_wei(price, 'ether')) if price else 0.0
        except:
            return 0.0

    # === DEMO PHASES ===

    async def _phase_setup(self):
        """Phase 0: Настройка пользователей"""
        self.logger.info("\n⏳ Phase 0: User Funds Setup")
        try:
            await self._deposit_eth_for_users()
            await self._deposit_tokens_for_users()
        except Exception as e:
            self.logger.error(f"❌ Setup phase failed: {e}")

    async def _phase_basic_trading(self):
        """Phase 1: Базовая торговля"""
        self.logger.info("\n⏳ Phase 1: Basic Trading & Security")
        try:
            await self._execute_basic_swap()
        except Exception as e:
            self.logger.error(f"❌ Basic trading phase failed: {e}")

    async def _phase_advanced_orders(self):
        """Phase 2: Продвинутые ордера"""
        self.logger.info("\n⏳ Phase 2: Advanced Order Types")
        try:
            if self.demo_config.config.orders.limit_order_enabled:
                await self._create_limit_order()
            if self.demo_config.config.orders.stop_loss_enabled:
                await self._create_stop_loss_order()
        except Exception as e:
            self.logger.error(f"❌ Advanced orders phase failed: {e}")

    async def _phase_order_management(self):
        """Phase 3: Управление ордерами"""
        self.logger.info("\n⏳ Phase 3: Order Management")
        try:
            if self.created_orders and self.demo_config.config.orders.modification_enabled:
                await self._demonstrate_order_modification()
            if self.created_orders and self.demo_config.config.orders.cancellation_enabled:
                await self._demonstrate_order_cancellation()
        except Exception as e:
            self.logger.error(f"❌ Order management phase failed: {e}")

    async def _phase_emergency_features(self):
        """Phase 4: Безопасность и emergency"""
        self.logger.info("\n⏳ Phase 4: Emergency & Security")
        try:
            if self.demo_config.config.test_emergency_pause:
                await self._test_emergency_pause()
        except Exception as e:
            self.logger.error(f"❌ Emergency features phase failed: {e}")

    async def _phase_self_execution(self):
        """Phase 5: Самовыполнение ордеров"""
        self.logger.info("\n⏳ Phase 5: Self-Execution Demo")
        try:
            if self.demo_config.config.orders.self_executable_enabled:
                await self._create_self_executable_order()
        except Exception as e:
            self.logger.error(f"❌ Self execution phase failed: {e}")

    # === TRADING OPERATIONS ===

    async def _deposit_eth_for_users(self):
        """Депозит ETH для пользователей"""
        self.logger.info("\n💰 DEPOSITING ETH FOR USERS")
        router = self.contract_manager.get_router()
        if not router:
            raise Exception("Router contract not available")

        deposit_amount = Web3.to_wei("2", 'ether')

        for i, user in enumerate([self.user1, self.user2], 1):
            try:
                # Проверка баланса пользователя
                user_balance = self.w3.eth.get_balance(user.address)
                if user_balance < deposit_amount + Web3.to_wei("0.1", 'ether'):
                    self.logger.error(f"❌ User{i} has insufficient ETH balance for deposit")
                    continue

                success, tx_hash, receipt = self._build_and_send_transaction(
                    router.functions.depositETH(),
                    user,
                    value=deposit_amount
                )

                if success:
                    self.logger.info(f"✅ User{i} deposited 2 ETH - TX: {tx_hash}")
                else:
                    self.logger.error(f"❌ User{i} deposit failed - TX: {tx_hash}")

            except Exception as e:
                self.logger.error(f"❌ ETH deposit failed for User{i}: {e}")

    async def _deposit_tokens_for_users(self):
        """Депозит токенов для пользователей"""
        self.logger.info("\n💎 DEPOSITING TOKENS FOR USERS")
        router = self.contract_manager.get_router()
        if not router:
            raise Exception("Router contract not available")

        deposit_results = []

        for symbol, token_config in self.demo_config.get_all_tokens().items():
            try:
                token_contract = self.tokens.get(symbol)
                if not token_contract:
                    deposit_results.append(f"{symbol}: ❌ Contract not loaded")
                    continue

                decimals = token_config.get('decimals', 18)
                required_amount = 200 * (10 ** decimals)

                for i, user in enumerate([self.user1, self.user2], 1):
                    # Проверка и минт токенов для пользователя
                    user_balance = token_contract.functions.balanceOf(user.address).call()
                    if user_balance < required_amount:
                        mint_amount = required_amount * 2
                        success, tx_hash, receipt = self._build_and_send_transaction(
                            token_contract.functions.mint(user.address, mint_amount),
                            self.deployer
                        )
                        if not success:
                            raise Exception(f"Mint failed for User{i}")

                    # Approve Router
                    success, tx_hash, receipt = self._build_and_send_transaction(
                        token_contract.functions.approve(router.address, required_amount),
                        user
                    )
                    if not success:
                        raise Exception(f"Approve failed for User{i}")

                    # Депозит в пул
                    success, tx_hash, receipt = self._build_and_send_transaction(
                        router.functions.depositToken(token_config['address'], required_amount),
                        user
                    )
                    if not success:
                        raise Exception(f"Deposit failed for User{i}")

                deposit_results.append(f"{symbol}: ✅")

            except Exception as e:
                deposit_results.append(f"{symbol}: ❌")
                self.logger.error(f"❌ {symbol} deposit failed: {e}")

        self.logger.info(f"💎 Token deposits: {' | '.join(deposit_results)}")

    async def _execute_basic_swap(self):
        """Выполнение базового свапа"""
        self.logger.info("\n🔄 EXECUTING BASIC SWAP: ETH -> CAPY")
        router = self.contract_manager.get_router()
        capy_config = self.demo_config.get_token_config('CAPY')
        if not router or not capy_config:
            raise Exception("Required contracts not found")

        capy_address = capy_config['address']

        try:
            swap_amount = Web3.to_wei("0.1", 'ether')

            # Получение ожидаемого количества токенов
            expected_out = router.functions.getAmountOut(swap_amount, self.eth_address, capy_address).call()
            min_amount_out = expected_out * 90 // 100  # 10% slippage

            decimals = capy_config.get('decimals', 18)
            expected_amount = expected_out / (10 ** decimals)
            self.logger.info(f"🔄 Swap: 0.1 ETH → {expected_amount:.6f} CAPY (min: {min_amount_out / (10 ** decimals):.6f})")

            success, tx_hash, receipt = self._build_and_send_transaction(
                router.functions.swapTokens(self.eth_address, capy_address, swap_amount, min_amount_out),
                self.user2,
                value=swap_amount
            )

            if success:
                self.logger.info(f"✅ Swap successful - TX: {tx_hash}")
            else:
                raise Exception(f"Swap transaction failed - TX: {tx_hash}")

        except Exception as e:
            self.logger.error(f"❌ Swap failed: {e} | Trying smaller amount...")

            # Retry с меньшей суммой
            try:
                small_swap_amount = Web3.to_wei("0.01", 'ether')
                expected_out = router.functions.getAmountOut(small_swap_amount, self.eth_address, capy_address).call()
                min_amount_out = expected_out * 80 // 100

                success, tx_hash, receipt = self._build_and_send_transaction(
                    router.functions.swapTokens(self.eth_address, capy_address, small_swap_amount, min_amount_out),
                    self.user2,
                    value=small_swap_amount
                )

                if success:
                    self.logger.info(f"✅ Small swap successful - TX: {tx_hash}")
                else:
                    self.logger.error(f"❌ Small swap failed - TX: {tx_hash}")
            except Exception as retry_error:
                self.logger.error(f"❌ Retry swap failed: {retry_error}")

    async def _create_limit_order(self):
        """Создание лимитного ордера"""
        self.logger.info("\n📋 CREATING LIMIT ORDER")
        router = self.contract_manager.get_router()
        capy_config = self.demo_config.get_token_config('CAPY')
        if not router or not capy_config:
            raise Exception("Required contracts not found")

        try:
            current_token_raw_price = router.functions.getPrice(capy_config['address']).call()
            target_price_raw = current_token_raw_price * 105 // 100  # 5% выше текущей цены
            order_amount = Web3.to_wei("0.05", 'ether')

            expected_out = router.functions.getAmountOut(order_amount, self.eth_address, capy_config['address']).call()
            min_amount_out = expected_out * 80 // 100

            self.logger.info(f"📋 Limit Order: {Web3.from_wei(order_amount, 'ether')} ETH @ target {Web3.from_wei(target_price_raw, 'ether')}")

            success, tx_hash, receipt = self._build_and_send_transaction(
                router.functions.createLimitOrder(
                    self.eth_address,
                    capy_config['address'],
                    order_amount,
                    target_price_raw,
                    min_amount_out,
                    True  # isLong
                ),
                self.user2,
                value=order_amount
            )

            if success:
                order_id = router.functions.getNextOrderId().call() - 1
                self.created_orders.append({'id': order_id, 'user': self.user2, 'type': 'LIMIT'})
                self.logger.info(f"✅ Limit order created: ID {order_id} - TX: {tx_hash}")
            else:
                raise Exception(f"Order transaction failed - TX: {tx_hash}")
        except Exception as e:
            self.logger.error(f"❌ Limit order creation failed: {e}")

    async def _create_stop_loss_order(self):
        """Создание стоп-лосс ордера"""
        self.logger.info("\n🛑 CREATING STOP-LOSS ORDER")
        router = self.contract_manager.get_router()
        capy_config = self.demo_config.get_token_config('CAPY')
        if not router or not capy_config:
            return

        try:
            current_eth_raw_price = router.functions.getPrice(self.eth_address).call()
            stop_price_raw = current_eth_raw_price * 95 // 100  # 5% ниже текущей цены
            order_amount = Web3.to_wei("0.05", 'ether')

            expected_out = router.functions.getAmountOut(order_amount, self.eth_address, capy_config['address']).call()
            min_amount_out = expected_out * 80 // 100

            self.logger.info(f"🛑 Stop-Loss: {Web3.from_wei(order_amount, 'ether')} ETH @ stop {Web3.from_wei(stop_price_raw, 'ether')}")

            success, tx_hash, receipt = self._build_and_send_transaction(
                router.functions.createStopLossOrder(
                    self.eth_address,
                    capy_config['address'],
                    order_amount,
                    stop_price_raw,
                    min_amount_out
                ),
                self.user2,
                value=order_amount
            )

            if success:
                order_id = router.functions.getNextOrderId().call() - 1
                self.created_orders.append({'id': order_id, 'user': self.user2, 'type': 'STOP_LOSS'})
                self.logger.info(f"✅ Stop-loss created: ID {order_id} - TX: {tx_hash}")
            else:
                raise Exception(f"Stop-loss transaction failed - TX: {tx_hash}")
        except Exception as e:
            self.logger.error(f"❌ Stop-loss order creation failed: {e}")

    async def _demonstrate_order_modification(self):
        """Демонстрация модификации ордера"""
        if not self.created_orders:
            self.logger.info("⚠️ No orders available for modification")
            return

        last_order = self.created_orders[-1]
        order_id = last_order['id']
        self.logger.info(f"\n✏️ DEMONSTRATING ORDER MODIFICATION for order {order_id}")

        router = self.contract_manager.get_router()
        if not router:
            return

        try:
            # Проверка состояния ордера
            order_data = router.functions.getOrder(order_id).call()
            if order_data[9]:  # executed flag
                self.logger.info(f"⚠️ Order {order_id} already executed, skipping modification")
                return

            # Новые параметры ордера
            current_price = router.functions.getPrice(self.eth_address).call()
            new_target_price = current_price * 98 // 100  # Уменьшаем цель на 2%
            min_amount_out = Web3.to_wei("1", 6)  # Минимальное количество

            success, tx_hash, receipt = self._build_and_send_transaction(
                router.functions.modifyOrder(order_id, new_target_price, min_amount_out),
                last_order['user']
            )

            if success:
                self.logger.info(f"✏️ Order {order_id} modified - New target: {Web3.from_wei(new_target_price, 'ether')} - TX: {tx_hash}")
            else:
                self.logger.error(f"❌ Order modification failed - TX: {tx_hash}")
        except Exception as e:
            self.logger.error(f"❌ Order modification failed: {e}")

    async def _demonstrate_order_cancellation(self):
        """Демонстрация отмены ордера"""
        if not self.created_orders:
            self.logger.info("⚠️ No orders available for cancellation")
            return

        last_order = self.created_orders[-1]
        order_id = last_order['id']
        self.logger.info(f"\n❌ TESTING ORDER CANCELLATION for order {order_id}")

        router = self.contract_manager.get_router()
        if not router:
            return

        try:
            success, tx_hash, receipt = self._build_and_send_transaction(
                router.functions.cancelOrder(order_id),
                last_order['user']
            )

            if success:
                self.logger.info(f"❌ Order {order_id} cancelled - Funds unlocked - TX: {tx_hash}")
            else:
                self.logger.error(f"❌ Order cancellation failed - TX: {tx_hash}")
        except Exception as e:
            self.logger.error(f"❌ Order cancellation failed: {e}")

    async def _test_emergency_pause(self):
        """Тестирование emergency pause функций"""
        self.logger.info("\n🚨 TESTING EMERGENCY PAUSE")
        emergency_paused = await self._check_emergency_pause()
        if emergency_paused:
            self.logger.warning("🚨 System is currently in emergency pause mode")
        else:
            self.logger.info("✅ Emergency pause system ready and inactive")

    async def _create_self_executable_order(self):
        """Создание самовыполняющегося ордера"""
        self.logger.info("\n🎯 CREATING SELF-EXECUTABLE ORDER")
        router = self.contract_manager.get_router()
        capy_config = self.demo_config.get_token_config('CAPY')
        if not router or not capy_config:
            self.logger.warning("⚠️ Required contracts not available for self-executable order")
            return

        try:
            current_token_raw_price = router.functions.getPrice(capy_config['address']).call()
            execution_price_raw = current_token_raw_price * 101 // 100  # 1% выше для быстрого исполнения
            order_amount = Web3.to_wei("0.02", 'ether')

            expected_out = router.functions.getAmountOut(order_amount, self.eth_address, capy_config['address']).call()
            min_amount_out = expected_out * 80 // 100

            self.logger.info(f"🎯 Self-Exec Order: {Web3.from_wei(order_amount, 'ether')} ETH @ {Web3.from_wei(execution_price_raw, 'ether')} | Reward: 0.1%")

            success, tx_hash, receipt = self._build_and_send_transaction(
                router.functions.createLimitOrder(
                    self.eth_address,
                    capy_config['address'],
                    order_amount,
                    execution_price_raw,
                    min_amount_out,
                    True  # isLong
                ),
                self.user1,
                value=order_amount
            )

            if success:
                order_id = router.functions.getNextOrderId().call() - 1
                self.created_orders.append({'id': order_id, 'user': self.user1, 'type': 'SELF_EXEC'})
                self.logger.info(f"✅ Self-executable order created: ID {order_id} - TX: {tx_hash}")

                # Попытка самовыполнения
                await self._attempt_self_execution(order_id)
            else:
                raise Exception(f"Self-executable order transaction failed - TX: {tx_hash}")
        except Exception as e:
            self.logger.error(f"❌ Self-executable order creation failed: {e}")

    async def _attempt_self_execution(self, order_id: int):
        """Попытка самовыполнения ордера"""
        self.logger.info(f"\n🚀 ATTEMPTING SELF-EXECUTION for order {order_id}")
        router = self.contract_manager.get_router()
        if not router:
            return

        try:
            # Проверка возможности выполнения
            can_execute = router.functions.shouldExecuteOrder(order_id).call()
            self.logger.info(f"Order {order_id} can execute: {'✅ YES' if can_execute else '⏳ NO'}")

            if can_execute:
                # Попытка выполнения keeper'ом
                success, tx_hash, receipt = self._build_and_send_transaction(
                    router.functions.selfExecuteOrder(order_id),
                    self.keeper
                )

                if success:
                    self.logger.info(f"🚀 Order {order_id} self-executed by keeper - TX: {tx_hash}")
                else:
                    self.logger.error(f"❌ Self-execution failed - TX: {tx_hash}")
            else:
                self.logger.info("⏳ Order conditions not met for execution")

        except Exception as e:
            self.logger.error(f"❌ Self-execution attempt failed: {e}")

    def _print_completion(self):
        """Вывод информации о завершении демо"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("🎉 TRADING DEMO COMPLETED SUCCESSFULLY!")
        self.logger.info("=" * 60)

        # Статистика созданных ордеров
        if self.created_orders:
            self.logger.info(f"📊 Orders created: {len(self.created_orders)}")
            order_types = {}
            for order in self.created_orders:
                order_type = order['type']
                order_types[order_type] = order_types.get(order_type, 0) + 1

            for order_type, count in order_types.items():
                self.logger.info(f"   {order_type}: {count}")
        else:
            self.logger.info("📊 No orders were created during demo")

        self.logger.info("\n✅ Features Demonstrated:")
        self.logger.info("   🏊 Pool liquidity initialization")
        self.logger.info("   💰 User fund deposits (ETH + Tokens)")
        self.logger.info("   🔄 Basic token swapping")
        self.logger.info("   📋 Limit orders")
        self.logger.info("   🛑 Stop-loss orders")
        self.logger.info("   ✏️ Order modification")
        self.logger.info("   ❌ Order cancellation")
        self.logger.info("   🎯 Self-executable orders")
        self.logger.info("   🔒 Security features & emergency controls")

        self.logger.info("\n🚀 Next Steps:")
        self.logger.info("   - Run keeper: npm run keeper:upgradeable-anvil")
        self.logger.info("   - Price updates: npm run price-generator-anvil")
        self.logger.info("   - Full JS demo: npm run trading-demo")

        self.logger.info("=" * 60)


# === DEMO VARIANTS ===

class QuickDemo(TradingDemo):
    """Быстрая версия демо с минимальными фазами"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.demo_config.quick_setup("fast")


class MinimalDemo(TradingDemo):
    """Минимальная версия демо только с основными функциями"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.demo_config.quick_setup("minimal")


class OrdersOnlyDemo(TradingDemo):
    """Демо только с ордерами, без базовых операций"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.demo_config.quick_setup("orders_only")


class SecurityDemo(TradingDemo):
    """Демо с фокусом на безопасность и emergency функции"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.demo_config.quick_setup("security_focus")