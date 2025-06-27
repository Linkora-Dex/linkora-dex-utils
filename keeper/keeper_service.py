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
import signal
import sys
import time
from typing import Optional, List
from web3 import Web3
from eth_account import Account

from config import ConfigManager
from contracts import ContractManager
from diagnostics import DiagnosticService

class KeeperService:
   def __init__(self, config_path: str = "../../config/deployment-config.json"):
       self.config_manager = ConfigManager(config_path)
       self.running = False
       self.logger = self._setup_logging()
       self._validate_config()
       self._setup_web3()
       self._setup_account()
       self.contract_manager = ContractManager(self.w3, self.config_manager)
       self.diagnostic_service = DiagnosticService(self.contract_manager, self.config_manager)
       self.order_check_counter = 0
       self.position_check_counter = 0
       if not self._verify_contracts():
           self.logger.error("❌ Contracts verification failed")
           raise ValueError("Contract verification failed")
       signal.signal(signal.SIGINT, self._signal_handler)
       signal.signal(signal.SIGTERM, self._signal_handler)

   def _setup_logging(self) -> logging.Logger:
       logging.basicConfig(
           level=getattr(logging, self.config_manager.config.log_level),
           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
           handlers=[
               logging.StreamHandler(sys.stdout),
               logging.FileHandler('keeper.log')
           ]
       )
       return logging.getLogger(__name__)

   def _validate_config(self):
       errors = self.config_manager.validate_config()
       if errors:
           for error in errors:
               self.logger.error(f"Config error: {error}")
           raise ValueError("Invalid configuration")

   def _setup_web3(self):
       self.w3 = Web3(Web3.HTTPProvider(self.config_manager.config.rpc_url))
       if not self.w3.is_connected():
           raise ConnectionError(f"Failed to connect to {self.config_manager.config.rpc_url}")
       self.logger.info(f"Connected to network: {self.w3.eth.chain_id}")

   def _setup_account(self):
       if not self.config_manager.config.private_key:
           raise ValueError("Private key not configured")
       self.account = Account.from_key(self.config_manager.config.private_key)
       self.logger.info(f"Keeper address: {self.account.address}")
       if self.config_manager.config.keeper_address:
           expected_address = self.config_manager.config.keeper_address
           if self.account.address.lower() != expected_address.lower():
               self.logger.warning(f"Address mismatch: {self.account.address} != {expected_address}")

   def _verify_contracts(self) -> bool:
       try:
           router_address = self.config_manager.get_contract_address('Router')
           if not router_address:
               self.logger.error("Router address not found in config")
               return False

           router_code = self.w3.eth.get_code(router_address)
           self.logger.info(f"Router code length: {len(router_code)} bytes")

           if len(router_code) <= 2:
               self.logger.error(f"Router contract not deployed at {router_address}")
               return False

           router = self.contract_manager.get_router()
           if not router:
               self.logger.error("Failed to load Router contract")
               return False

           try:
               price = router.functions.getPrice("0x0000000000000000000000000000000000000000").call()
               self.logger.info(f"✅ Router verified - ETH price: {price}")
               return True
           except Exception as e:
               self.logger.error(f"Router method call failed: {e}")
               try:
                   next_order_id = router.functions.getNextOrderId().call()
                   self.logger.info(f"✅ Router verified - Next order ID: {next_order_id}")
                   return True
               except Exception as e2:
                   self.logger.error(f"Router alternative method failed: {e2}")
                   return False
       except Exception as e:
           self.logger.error(f"Contract verification error: {e}")
           return False

   def _signal_handler(self, signum, frame):
       self.logger.info(f"Received signal {signum}, shutting down...")
       self.stop()

   async def start(self):
       if self.running:
           self.logger.warning("Keeper already running")
           return
       self.running = True
       self.logger.info("🚀 Keeper Service started")
       if self.config_manager.config.enable_diagnostics:
           self.diagnostic_service.display_system_status()
           self.diagnostic_service.display_balance_diagnostics("INITIALIZATION", self.account.address)
           self.diagnostic_service.display_oracle_diagnostics("INITIALIZATION")
       self.diagnostic_service.log_keeper_status("STARTUP")
       await self._main_loop()

   def stop(self):
       self.running = False
       self.logger.info("🛑 Keeper Service stopped")

   async def _main_loop(self):
       last_diagnostics_time = time.time()
       while self.running:
           try:
               current_time = time.time()
               if self.config_manager.config.enable_order_execution:
                   await self._check_orders()
               if self.config_manager.config.enable_position_liquidation:
                   if self.order_check_counter % 2 == 0:
                       await self._check_positions()
               if (self.config_manager.config.enable_diagnostics and
                       current_time - last_diagnostics_time >= self.config_manager.config.diagnostics_interval):
                   self.diagnostic_service.log_keeper_status("RUNNING")
                   last_diagnostics_time = current_time
               self.order_check_counter += 1
               await asyncio.sleep(self.config_manager.config.order_check_interval)
           except Exception as e:
               self.logger.error(f"🚨 Main loop error: {e}")
               await asyncio.sleep(self.config_manager.config.retry_delay)

   async def _check_orders(self):
       try:
           next_order_id = self.contract_manager.get_next_order_id()
           total_orders = next_order_id - 1
           if total_orders <= 0:
               self.logger.debug("No orders to check")
               return
           executed_count = 0
           for order_id in range(1, min(next_order_id, self.config_manager.config.max_orders_per_batch + 1)):
               try:
                   order = self.contract_manager.get_order(order_id)
                   if not order or order.executed:
                       continue
                   should_execute = self.contract_manager.should_execute_order(order_id)
                   if should_execute:
                       order_type_str = 'LIMIT' if order.order_type == 0 else 'STOP_LOSS'
                       self.logger.info(f"🎯 {order_type_str} Order {order_id}: Execution condition met - EXECUTING")
                       if self.config_manager.config.enable_diagnostics:
                           self.diagnostic_service.display_order_diagnostics(order_id)
                           self.diagnostic_service.display_balance_diagnostics(
                               f"BEFORE ORDER {order_id} EXECUTION", self.account.address)
                           self.diagnostic_service.display_oracle_diagnostics(
                               f"BEFORE ORDER {order_id} EXECUTION")
                       success = await self._execute_order_with_retry(order_id)
                       self.diagnostic_service.log_execution_attempt(order_id, success)
                       if success:
                           executed_count += 1
                           if self.config_manager.config.enable_diagnostics:
                               self.diagnostic_service.display_balance_diagnostics(
                                   f"AFTER SUCCESSFUL ORDER {order_id} EXECUTION", self.account.address)
                               self.diagnostic_service.display_oracle_diagnostics(
                                   f"AFTER SUCCESSFUL ORDER {order_id} EXECUTION")
                       else:
                           if self.config_manager.config.enable_diagnostics:
                               self.diagnostic_service.display_balance_diagnostics(
                                   f"AFTER FAILED ORDER {order_id} EXECUTION", self.account.address)
                               self.diagnostic_service.display_oracle_diagnostics(
                                   f"AFTER FAILED ORDER {order_id} EXECUTION")
               except Exception as order_error:
                   self.logger.warning(f"⚠️ Error checking order {order_id}: {order_error}")
           if executed_count > 0:
               self.logger.info(f"📊 Executed {executed_count} orders in this cycle")
       except Exception as e:
           self.logger.error(f"Error in order checking: {e}")

   async def _check_positions(self):
       try:
           next_position_id = self.contract_manager.get_next_position_id()
           total_positions = next_position_id - 1
           if total_positions <= 0:
               self.logger.debug("No positions to check")
               return
           liquidated_count = 0
           for position_id in range(1, next_position_id):
               try:
                   position = self.contract_manager.get_position(position_id)
                   if not position or not position.is_open:
                       continue
                   pnl_ratio = self.diagnostic_service.calculate_pnl_ratio(position)
                   if pnl_ratio <= self.config_manager.config.liquidation_threshold:
                       self.logger.warning(f"⚠️ Position {position_id} at {pnl_ratio:.2f}% loss - liquidation candidate")
                       if self.config_manager.config.enable_diagnostics:
                           self.diagnostic_service.display_position_diagnostics(position_id)
                       success = await self._liquidate_position_with_retry(position_id)
                       self.diagnostic_service.log_liquidation_attempt(position_id, success)
                       if success:
                           liquidated_count += 1
               except Exception as position_error:
                   self.logger.warning(f"⚠️ Error checking position {position_id}: {position_error}")
           if liquidated_count > 0:
               self.logger.info(f"📊 Liquidated {liquidated_count} positions in this cycle")
       except Exception as e:
           self.logger.error(f"Error in position checking: {e}")

   async def _execute_order_with_retry(self, order_id: int) -> bool:
       for attempt in range(self.config_manager.config.retry_attempts):
           try:
               tx_hash = self.contract_manager.execute_order(order_id, self.account)
               if tx_hash:
                   receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                   if receipt.status == 1:
                       self.logger.info(f"✅ Order {order_id} executed successfully. Tx: {tx_hash}")
                       return True
                   else:
                       self.logger.error(f"❌ Order {order_id} execution failed in transaction")
           except Exception as e:
               self.logger.error(f"❌ Attempt {attempt + 1} failed for order {order_id}: {e}")
               if attempt < self.config_manager.config.retry_attempts - 1:
                   await asyncio.sleep(self.config_manager.config.retry_delay)
       return False

   async def _liquidate_position_with_retry(self, position_id: int) -> bool:
       for attempt in range(self.config_manager.config.retry_attempts):
           try:
               tx_hash = self.contract_manager.close_position(position_id, self.account)
               if tx_hash:
                   receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                   if receipt.status == 1:
                       self.logger.info(f"⚡ Position {position_id} liquidated successfully. Tx: {tx_hash}")
                       return True
                   else:
                       self.logger.error(f"❌ Position {position_id} liquidation failed in transaction")
           except Exception as e:
               self.logger.error(f"❌ Attempt {attempt + 1} failed for position {position_id}: {e}")
               if attempt < self.config_manager.config.retry_attempts - 1:
                   await asyncio.sleep(self.config_manager.config.retry_delay)
       return False

   def update_config(self, **kwargs):
       self.config_manager.update_config(**kwargs)
       self.logger.info(f"Config updated: {kwargs}")

   def get_status(self) -> dict:
       return {
           'running': self.running,
           'keeper_address': self.account.address,
           'network_id': self.w3.eth.chain_id,
           'order_check_counter': self.order_check_counter,
           'position_check_counter': self.position_check_counter,
           'config': {
               'order_check_interval': self.config_manager.config.order_check_interval,
               'position_check_interval': self.config_manager.config.position_check_interval,
               'liquidation_threshold': self.config_manager.config.liquidation_threshold,
               'enable_order_execution': self.config_manager.config.enable_order_execution,
               'enable_position_liquidation': self.config_manager.config.enable_position_liquidation,
               'enable_oracle_monitoring': self.config_manager.config.enable_oracle_monitoring
           }
       }

   async def manual_execute_order(self, order_id: int) -> bool:
       self.logger.info(f"🔧 Manual execution requested for order {order_id}")
       return await self._execute_order_with_retry(order_id)

   async def manual_liquidate_position(self, position_id: int) -> bool:
       self.logger.info(f"🔧 Manual liquidation requested for position {position_id}")
       return await self._liquidate_position_with_retry(position_id)

   def get_order_info(self, order_id: int) -> Optional[dict]:
       order = self.contract_manager.get_order(order_id)
       if not order:
           return None
       return {
           'id': order.id,
           'user': order.user,
           'token_in': order.token_in,
           'token_out': order.token_out,
           'amount_in': order.amount_in,
           'target_price': order.target_price,
           'min_amount_out': order.min_amount_out,
           'order_type': 'LIMIT' if order.order_type == 0 else 'STOP_LOSS',
           'is_long': order.is_long,
           'executed': order.executed,
           'created_at': order.created_at,
           'self_executable': order.self_executable,
           'should_execute': self.contract_manager.should_execute_order(order_id)
       }

   def get_position_info(self, position_id: int) -> Optional[dict]:
       position = self.contract_manager.get_position(position_id)
       if not position:
           return None
       pnl_ratio = self.diagnostic_service.calculate_pnl_ratio(position)
       return {
           'id': position.id,
           'user': position.user,
           'token': position.token,
           'collateral_amount': position.collateral_amount,
           'leverage': position.leverage,
           'position_type': 'LONG' if position.position_type == 0 else 'SHORT',
           'entry_price': position.entry_price,
           'size': position.size,
           'created_at': position.created_at,
           'is_open': position.is_open,
           'pnl_ratio': pnl_ratio,
           'liquidation_candidate': pnl_ratio <= self.config_manager.config.liquidation_threshold
       }

   def get_all_orders(self) -> List[dict]:
       orders = []
       next_order_id = self.contract_manager.get_next_order_id()
       for order_id in range(1, next_order_id):
           order_info = self.get_order_info(order_id)
           if order_info:
               orders.append(order_info)
       return orders

   def get_all_positions(self) -> List[dict]:
       positions = []
       next_position_id = self.contract_manager.get_next_position_id()
       for position_id in range(1, next_position_id):
           position_info = self.get_position_info(position_id)
           if position_info:
               positions.append(position_info)
       return positions

   def force_diagnostics(self):
       if self.config_manager.config.enable_diagnostics:
           self.diagnostic_service.display_system_status()
           self.diagnostic_service.display_balance_diagnostics("MANUAL_TRIGGER", self.account.address)
           self.diagnostic_service.display_oracle_diagnostics("MANUAL_TRIGGER")
           self.diagnostic_service.log_keeper_status("MANUAL_TRIGGER")
       else:
           self.logger.warning("Diagnostics are disabled in config")