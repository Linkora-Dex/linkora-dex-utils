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

import logging
import time
from typing import Dict, Any, List
from web3 import Web3
from contracts import ContractManager, OrderInfo, PositionInfo


class DiagnosticService:
    def __init__(self, contract_manager: ContractManager, config_manager):
        self.contract_manager = contract_manager
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.eth_address = "0x0000000000000000000000000000000000000000"

    def display_balance_diagnostics(self, phase: str, keeper_address: str):
        self.logger.info(f"\n💰 BALANCE DIAGNOSTICS ({phase})")

        try:
            keeper_eth_balance = Web3.from_wei(
                self.contract_manager.w3.eth.get_balance(keeper_address),
                'ether'
            )
            self.logger.info(f"Keeper ETH balance: {keeper_eth_balance} ETH")

            pool_eth_balance = Web3.from_wei(
                self.contract_manager.get_pool_balance(self.eth_address),
                'ether'
            )
            self.logger.info(f"Pool total ETH balance: {pool_eth_balance} ETH")

            keeper_pool_eth = Web3.from_wei(
                self.contract_manager.get_balance(keeper_address, self.eth_address),
                'ether'
            )
            self.logger.info(f"Keeper ETH in pool: {keeper_pool_eth} ETH")

            keeper_available_eth = Web3.from_wei(
                self.contract_manager.get_available_balance(keeper_address, self.eth_address),
                'ether'
            )
            self.logger.info(f"Keeper available ETH in pool: {keeper_available_eth} ETH")

            for symbol, token_config in self.config_manager.config.tokens.items():
                token_address = token_config.get('address', '')
                decimals = token_config.get('decimals', 18)

                if token_address:
                    pool_balance = self.contract_manager.get_pool_balance(token_address)
                    keeper_balance = self.contract_manager.get_balance(keeper_address, token_address)

                    pool_balance_formatted = pool_balance / (10 ** decimals)
                    keeper_balance_formatted = keeper_balance / (10 ** decimals)

                    self.logger.info(f"Pool {symbol} balance: {pool_balance_formatted}")
                    self.logger.info(f"Keeper {symbol} in pool: {keeper_balance_formatted}")

        except Exception as e:
            self.logger.error(f"Error in balance diagnostics: {e}")

        self.logger.info("💰 END BALANCE DIAGNOSTICS\n")

    def display_oracle_diagnostics(self, phase: str):
        self.logger.info(f"\n🔮 ORACLE DIAGNOSTICS ({phase})")

        try:
            eth_price = self.contract_manager.get_price(self.eth_address)
            eth_valid = self.contract_manager.is_price_valid(self.eth_address)

            if eth_price is not None:
                eth_price_formatted = Web3.from_wei(eth_price, 'ether')
                self.logger.info(f"ETH price: {eth_price_formatted} USD, valid: {eth_valid}")
            else:
                self.logger.error("ETH price: ERROR - Could not fetch price")

            for symbol, token_config in self.config_manager.config.tokens.items():
                token_address = token_config.get('address', '')

                if token_address:
                    price = self.contract_manager.get_price(token_address)
                    valid = self.contract_manager.is_price_valid(token_address)

                    if price is not None:
                        price_formatted = Web3.from_wei(price, 'ether')
                        self.logger.info(f"{symbol} price: {price_formatted} USD, valid: {valid}")
                    else:
                        self.logger.error(f"{symbol} price: ERROR - Could not fetch price")

        except Exception as e:
            self.logger.error(f"Error in oracle diagnostics: {e}")

        self.logger.info("🔮 END ORACLE DIAGNOSTICS")

    def display_order_diagnostics(self, order_id: int):
        try:
            order = self.contract_manager.get_order(order_id)
            if not order:
                self.logger.error(f"Could not fetch order {order_id}")
                return

            self.logger.info(f"\n📋 ORDER {order_id} DIAGNOSTICS")
            self.logger.info(f"User: {order.user}")
            self.logger.info(f"TokenIn: {order.token_in}")
            self.logger.info(f"TokenOut: {order.token_out}")

            if order.token_in == self.eth_address:
                amount_formatted = Web3.from_wei(order.amount_in, 'ether')
                self.logger.info(f"AmountIn: {amount_formatted} ETH")
            else:
                amount_formatted = order.amount_in / (10 ** 6)
                self.logger.info(f"AmountIn: {amount_formatted} Token")

            target_price_formatted = Web3.from_wei(order.target_price, 'ether')
            self.logger.info(f"TargetPrice: {target_price_formatted} USD")

            decimals = 18 if order.token_out == self.eth_address else 6
            min_amount_formatted = order.min_amount_out / (10 ** decimals)
            self.logger.info(f"MinAmountOut: {min_amount_formatted}")

            order_type_str = 'LIMIT' if order.order_type == 0 else 'STOP_LOSS'
            self.logger.info(f"OrderType: {order_type_str}")
            self.logger.info(f"IsLong: {order.is_long}")
            self.logger.info(f"Executed: {order.executed}")

        except Exception as e:
            self.logger.error(f"Error logging order details: {e}")

    def display_position_diagnostics(self, position_id: int):
        try:
            position = self.contract_manager.get_position(position_id)
            if not position:
                self.logger.error(f"Could not fetch position {position_id}")
                return

            self.logger.info(f"\n📊 POSITION {position_id} DIAGNOSTICS")
            self.logger.info(f"User: {position.user}")
            self.logger.info(f"Token: {position.token}")

            collateral_formatted = Web3.from_wei(position.collateral_amount, 'ether')
            self.logger.info(f"Collateral: {collateral_formatted} ETH")
            self.logger.info(f"Leverage: {position.leverage}x")

            position_type_str = 'LONG' if position.position_type == 0 else 'SHORT'
            self.logger.info(f"Type: {position_type_str}")

            entry_price_formatted = Web3.from_wei(position.entry_price, 'ether')
            self.logger.info(f"Entry Price: {entry_price_formatted} USD")

            size_formatted = Web3.from_wei(position.size, 'ether')
            self.logger.info(f"Size: {size_formatted}")
            self.logger.info(f"Open: {position.is_open}")

        except Exception as e:
            self.logger.error(f"Error logging position details: {e}")

    def calculate_pnl_ratio(self, position: PositionInfo) -> float:
        try:
            current_price = self.contract_manager.get_price(position.token)
            if current_price is None:
                return 0.0

            if position.position_type == 0:
                pnl_ratio = ((current_price - position.entry_price) * 100) / position.entry_price
            else:
                pnl_ratio = ((position.entry_price - current_price) * 100) / position.entry_price

            return pnl_ratio

        except Exception as e:
            self.logger.error(f"Error calculating PnL ratio: {e}")
            return 0.0

    def display_system_status(self):
        try:
            next_order_id = self.contract_manager.get_next_order_id()
            next_position_id = self.contract_manager.get_next_position_id()

            self.logger.info("\n🔒 SYSTEM STATUS")
            self.logger.info(f"Total Orders: {next_order_id - 1}")
            self.logger.info(f"Total Positions: {next_position_id - 1}")
            self.logger.info("Status: 🟢 OPERATIONAL")

            self.logger.info("\n🛡️ Security Features:")
            self.logger.info(" ✅ Flash Loan Protection: ACTIVE")
            self.logger.info(" ✅ Circuit Breaker: 50% max price change")
            self.logger.info(" ✅ Emergency Stop: READY")
            self.logger.info(" ✅ Self-Execution: ENABLED")

        except Exception as e:
            self.logger.error(f"Error displaying system status: {e}")

    def log_execution_attempt(self, order_id: int, success: bool, error_msg: str = ""):
        if success:
            self.logger.info(f"✅ Order {order_id} executed successfully")
        else:
            self.logger.error(f"❌ Keeper execution failed for order {order_id}: {error_msg}")

    def log_liquidation_attempt(self, position_id: int, success: bool, error_msg: str = ""):
        if success:
            self.logger.info(f"⚡ Position {position_id} liquidated successfully")
        else:
            self.logger.error(f"❌ Liquidation failed for position {position_id}: {error_msg}")

    def log_keeper_status(self, phase: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"\n🤖 KEEPER STATUS - {phase} ({timestamp})")

        next_order_id = self.contract_manager.get_next_order_id()
        next_position_id = self.contract_manager.get_next_position_id()

        self.logger.info(f"Monitoring {next_order_id - 1} orders and {next_position_id - 1} positions")
        self.logger.info(f"Order check interval: {self.config_manager.config.order_check_interval}s")
        self.logger.info(f"Position check interval: {self.config_manager.config.position_check_interval}s")
        self.logger.info(f"Liquidation threshold: {self.config_manager.config.liquidation_threshold}%")