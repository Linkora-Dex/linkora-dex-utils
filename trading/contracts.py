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

import json
from typing import Dict, Any, List, Optional, Tuple
from web3 import Web3
from web3.contract import Contract
from dataclasses import dataclass
from pathlib import Path
import logging


@dataclass
class OrderInfo:
    id: int
    user: str
    token_in: str
    token_out: str
    amount_in: int
    target_price: int
    min_amount_out: int
    order_type: int
    is_long: bool
    executed: bool
    created_at: int
    self_executable: bool


@dataclass
class PositionInfo:
    id: int
    user: str
    token: str
    collateral_amount: int
    leverage: int
    position_type: int
    entry_price: int
    size: int
    created_at: int
    is_open: bool


@dataclass
class SystemState:
    emergency_paused: bool
    total_orders: int
    total_positions: int
    network_gas_price: int
    router_balance: int


class ContractManager:
    def __init__(self, w3: Web3, config):
        self.w3 = w3
        self.config = config
        self.contracts: Dict[str, Contract] = {}
        self.logger = logging.getLogger(__name__)
        self._load_contracts()

    def _load_contracts(self):
        base_path = self.config.config_path.parent.parent
        router_address = self.config.get_contract_address('Router')

        if router_address:
            try:
                abi_path = base_path / 'artifacts/contracts/upgradeable/RouterUpgradeable.sol/RouterUpgradeable.json'
                abi = self._load_abi(abi_path)
                self.contracts['Router'] = self.w3.eth.contract(
                    address=Web3.to_checksum_address(router_address),
                    abi=abi
                )
                self.logger.info(f"Loaded contract Router at {router_address}")
            except Exception as e:
                self.logger.error(f"Failed to load contract Router: {e}")

        access_control_address = self.config.get_contract_address('AccessControl')
        if access_control_address:
            try:
                abi_path = base_path / 'artifacts/contracts/access/AccessControl.sol/AccessControlContract.json'
                abi = self._load_abi(abi_path)
                self.contracts['AccessControl'] = self.w3.eth.contract(
                    address=Web3.to_checksum_address(access_control_address),
                    abi=abi
                )
                self.logger.info(f"Loaded contract AccessControl at {access_control_address}")
            except Exception as e:
                self.logger.warning(f"Failed to load AccessControl: {e}")

    def _load_abi(self, abi_path) -> List[Dict]:
        path = Path(abi_path)
        if not path.exists():
            raise FileNotFoundError(f"ABI file not found: {abi_path}")
        with open(path, 'r') as f:
            contract_json = json.load(f)
        return contract_json.get('abi', [])

    def get_contract(self, name: str) -> Optional[Contract]:
        return self.contracts.get(name)

    def get_router(self) -> Optional[Contract]:
        return self.get_contract('Router')

    def get_access_control(self) -> Optional[Contract]:
        return self.get_contract('AccessControl')

    def validate_contract_state(self) -> Tuple[bool, Dict[str, Any]]:
        """Проверка состояния контрактов перед операциями"""
        state = {
            'router_available': False,
            'emergency_paused': False,
            'gas_price_acceptable': False,
            'network_responsive': False
        }

        try:
            router = self.get_router()
            state['router_available'] = router is not None

            if router:
                state['emergency_paused'] = self.is_emergency_paused()

            gas_price = self.w3.eth.gas_price
            state['gas_price_acceptable'] = gas_price <= self.config.config.max_gas_price

            latest_block = self.w3.eth.block_number
            state['network_responsive'] = latest_block > 0

            all_ok = all([
                state['router_available'],
                not state['emergency_paused'],
                state['gas_price_acceptable'],
                state['network_responsive']
            ])

            return all_ok, state

        except Exception as e:
            self.logger.error(f"Contract state validation failed: {e}")
            return False, state

    def is_emergency_paused(self) -> bool:
        """Проверка состояния emergency pause"""
        try:
            access_control = self.get_access_control()
            if access_control:
                return bool(access_control.functions.emergencyStop().call())
            return False
        except Exception as e:
            self.logger.debug(f"Could not check emergency pause: {e}")
            return False

    def validate_user_balance(self, user_address: str, token_address: str, required_amount: int) -> Tuple[bool, Dict[str, int]]:
        """Валидация баланса пользователя для операции"""
        balances = {
            'wallet_balance': 0,
            'pool_balance': 0,
            'available_balance': 0,
            'required_amount': required_amount
        }

        try:
            if token_address == "0x0000000000000000000000000000000000000000":
                balances['wallet_balance'] = self.w3.eth.get_balance(user_address)
                balances['pool_balance'] = self.get_balance(user_address, token_address)
                balances['available_balance'] = self.get_available_balance(user_address, token_address)
            else:
                balances['pool_balance'] = self.get_balance(user_address, token_address)
                balances['available_balance'] = self.get_available_balance(user_address, token_address)

            sufficient = balances['available_balance'] >= required_amount
            return sufficient, balances

        except Exception as e:
            self.logger.error(f"Balance validation failed: {e}")
            return False, balances

    def get_system_state(self) -> SystemState:
        """Получение текущего состояния системы"""
        try:
            router = self.get_router()

            emergency_paused = self.is_emergency_paused()
            total_orders = self.get_next_order_id() - 1 if router else 0
            total_positions = self.get_next_position_id() - 1 if router else 0
            network_gas_price = self.w3.eth.gas_price
            router_balance = self.w3.eth.get_balance(router.address) if router else 0

            return SystemState(
                emergency_paused=emergency_paused,
                total_orders=total_orders,
                total_positions=total_positions,
                network_gas_price=network_gas_price,
                router_balance=router_balance
            )

        except Exception as e:
            self.logger.error(f"Failed to get system state: {e}")
            return SystemState(False, 0, 0, 0, 0)

    def check_liquidity_requirements(self, token_in: str, token_out: str, amount_in: int) -> Tuple[bool, Dict[str, int]]:
        """Проверка требований ликвидности для свапа"""
        liquidity_info = {
            'token_in_pool': 0,
            'token_out_pool': 0,
            'estimated_out': 0,
            'sufficient_liquidity': False
        }

        try:
            router = self.get_router()
            if not router:
                return False, liquidity_info

            liquidity_info['token_in_pool'] = self.get_pool_balance(token_in)
            liquidity_info['token_out_pool'] = self.get_pool_balance(token_out)

            try:
                liquidity_info['estimated_out'] = router.functions.getAmountOut(amount_in, token_in, token_out).call()
                liquidity_info['sufficient_liquidity'] = liquidity_info['estimated_out'] > 0 and liquidity_info['token_out_pool'] >= liquidity_info[
                    'estimated_out']
            except:
                liquidity_info['sufficient_liquidity'] = False

            return liquidity_info['sufficient_liquidity'], liquidity_info

        except Exception as e:
            self.logger.error(f"Liquidity check failed: {e}")
            return False, liquidity_info

    def get_next_order_id(self) -> int:
        router = self.get_router()
        if not router:
            return 1
        try:
            return int(router.functions.getNextOrderId().call())
        except Exception as e:
            self.logger.debug(f"Could not get next order ID: {e}")
            return 1

    def get_next_position_id(self) -> int:
        router = self.get_router()
        if not router:
            return 1
        try:
            return int(router.functions.getNextPositionId().call())
        except Exception as e:
            self.logger.debug(f"Could not get next position ID: {e}")
            return 1

    def get_order(self, order_id: int) -> Optional[OrderInfo]:
        router = self.get_router()
        if not router:
            return None
        try:
            order_data = router.functions.getOrder(order_id).call()
            if len(order_data) >= 12:
                return OrderInfo(
                    id=int(order_data[0]),
                    user=order_data[1],
                    token_in=order_data[2],
                    token_out=order_data[3],
                    amount_in=int(order_data[4]),
                    target_price=int(order_data[5]),
                    min_amount_out=int(order_data[6]),
                    order_type=int(order_data[7]),
                    is_long=bool(order_data[8]),
                    executed=bool(order_data[9]),
                    created_at=int(order_data[10]),
                    self_executable=bool(order_data[11]) if len(order_data) > 11 else False
                )
            return None
        except Exception as e:
            self.logger.debug(f"Could not get order {order_id}: {e}")
            return None

    def get_position(self, position_id: int) -> Optional[PositionInfo]:
        router = self.get_router()
        if not router:
            return None
        try:
            position_data = router.functions.getPosition(position_id).call()
            if len(position_data) >= 10:
                return PositionInfo(
                    id=int(position_data[0]),
                    user=position_data[1],
                    token=position_data[2],
                    collateral_amount=int(position_data[3]),
                    leverage=int(position_data[4]),
                    position_type=int(position_data[5]),
                    entry_price=int(position_data[6]),
                    size=int(position_data[7]),
                    created_at=int(position_data[8]),
                    is_open=bool(position_data[9])
                )
            return None
        except Exception as e:
            self.logger.debug(f"Could not get position {position_id}: {e}")
            return None

    def should_execute_order(self, order_id: int) -> bool:
        router = self.get_router()
        if not router:
            return False
        try:
            return bool(router.functions.shouldExecuteOrder(order_id).call())
        except Exception as e:
            self.logger.debug(f"Could not check execution condition for order {order_id}: {e}")
            return False

    def execute_order(self, order_id: int, account) -> Optional[str]:
        router = self.get_router()
        if not router:
            return None
        try:
            tx_hash = router.functions.selfExecuteOrder(order_id).transact({
                'from': account.address,
                'gas': self.config.config.gas_limit,
                'gasPrice': self.config.config.max_gas_price
            })
            return tx_hash.hex()
        except Exception as e:
            self.logger.error(f"Failed to execute order {order_id}: {e}")
            return None

    def liquidate_position(self, position_id: int, account) -> Optional[str]:
        router = self.get_router()
        if not router:
            return None
        try:
            tx_hash = router.functions.liquidatePosition(position_id).transact({
                'from': account.address,
                'gas': self.config.config.gas_limit,
                'gasPrice': self.config.config.max_gas_price
            })
            return tx_hash.hex()
        except Exception as e:
            self.logger.error(f"Failed to liquidate position {position_id}: {e}")
            return None

    def get_price(self, token_address: str) -> Optional[int]:
        router = self.get_router()
        if not router:
            return None
        try:
            return int(router.functions.getPrice(token_address).call())
        except Exception as e:
            self.logger.debug(f"Could not get price for {token_address}: {e}")
            return None

    def get_balance(self, user_address: str, token_address: str) -> int:
        router = self.get_router()
        if not router:
            return 0
        try:
            return int(router.functions.getBalance(user_address, token_address).call())
        except Exception as e:
            self.logger.debug(f"Could not get balance for {user_address}: {e}")
            return 0

    def get_available_balance(self, user_address: str, token_address: str) -> int:
        router = self.get_router()
        if not router:
            return 0
        try:
            return int(router.functions.getAvailableBalance(user_address, token_address).call())
        except Exception as e:
            self.logger.debug(f"Could not get available balance for {user_address}: {e}")
            return self.get_balance(user_address, token_address)

    def get_pool_balance(self, token_address: str) -> int:
        router = self.get_router()
        if not router:
            return 0
        try:
            if token_address == "0x0000000000000000000000000000000000000000":
                return self.w3.eth.get_balance(router.address)
            else:
                return int(router.functions.getBalance(router.address, token_address).call())
        except Exception as e:
            self.logger.debug(f"Could not get pool balance for {token_address}: {e}")
            return 0

    def close_position(self, position_id: int, account) -> Optional[str]:
        return self.liquidate_position(position_id, account)

    def can_execute_order(self, order_id: int) -> bool:
        return self.should_execute_order(order_id)

    def get_order_safe(self, order_id: int) -> Optional[OrderInfo]:
        try:
            order = self.get_order(order_id)
            if order and not order.executed:
                return order
            return None
        except Exception:
            return None

    def is_price_valid(self, token_address: str) -> bool:
        try:
            price = self.get_price(token_address)
            return price is not None and price > 0
        except:
            return False

    def get_order_user(self, order_id: int) -> Optional[str]:
        order = self.get_order(order_id)
        return order.user if order else None

    def get_position_user(self, position_id: int) -> Optional[str]:
        position = self.get_position(position_id)
        return position.user if position else None

    def get_user_orders(self, user_address: str) -> List[int]:
        orders = []
        try:
            next_order_id = self.get_next_order_id()
            for order_id in range(1, next_order_id):
                order = self.get_order(order_id)
                if order and order.user.lower() == user_address.lower():
                    orders.append(order_id)
        except Exception as e:
            self.logger.debug(f"Could not get user orders: {e}")
        return orders

    def get_user_positions(self, user_address: str) -> List[int]:
        positions = []
        try:
            next_position_id = self.get_next_position_id()
            for position_id in range(1, next_position_id):
                position = self.get_position(position_id)
                if position and position.user.lower() == user_address.lower():
                    positions.append(position_id)
        except Exception as e:
            self.logger.debug(f"Could not get user positions: {e}")
        return positions

    def get_current_price(self, token_in: str, token_out: str) -> Optional[int]:
        return self.get_price(token_out)

    def calculate_min_amount_out(self, token_in: str, token_out: str, amount_in: int) -> Optional[int]:
        try:
            router = self.get_router()
            if not router:
                return None
            return int(router.functions.getAmountOut(amount_in, token_in, token_out).call())
        except Exception as e:
            self.logger.debug(f"Could not calculate min amount out: {e}")
            return None

    def get_amount_out(self, amount_in: int, token_in: str, token_out: str) -> Optional[int]:
        return self.calculate_min_amount_out(token_in, token_out, amount_in)

    def validate_operation_safety(self, operation_type: str, user_address: str, amount: int = 0, token_address: str = None) -> Tuple[bool, List[str]]:
        """Комплексная проверка безопасности операции"""
        issues = []

        try:
            state_ok, state = self.validate_contract_state()
            if not state_ok:
                if not state['router_available']:
                    issues.append("Router contract not available")
                if state['emergency_paused']:
                    issues.append("System in emergency pause")
                if not state['gas_price_acceptable']:
                    issues.append("Gas price too high")
                if not state['network_responsive']:
                    issues.append("Network not responsive")

            if amount > 0 and token_address:
                balance_ok, balance_info = self.validate_user_balance(user_address, token_address, amount)
                if not balance_ok:
                    issues.append(f"Insufficient balance: {balance_info['available_balance']} < {amount}")

            if operation_type in ['swap', 'limit_order', 'stop_loss'] and token_address:
                liquidity_ok, liquidity_info = self.check_liquidity_requirements(
                    token_address,
                    "0x0000000000000000000000000000000000000000",  # ETH as default out
                    amount
                )
                if not liquidity_ok:
                    issues.append("Insufficient pool liquidity")

            return len(issues) == 0, issues

        except Exception as e:
            issues.append(f"Safety validation failed: {e}")
            return False, issues