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

import subprocess
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RailgunWallet:
    id: str
    address: str
    mnemonic: Optional[str] = None


@dataclass
class TransactionResult:
    success: bool
    tx_hash: Optional[str] = None
    status: Optional[str] = None
    gas_used: Optional[str] = None
    block_number: Optional[int] = None
    error: Optional[str] = None


class RailgunBridge:
    def __init__(self, network: str = "polygon"):
        self.network = network
        self.js_wrapper_path = Path(__file__).parent / "railgun_wrapper.js"
        self.is_initialized = False
        self.wallet = None
        self._check_dependencies()

    def _check_dependencies(self):
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise RuntimeError("Node.js not found")
        except Exception as e:
            raise RuntimeError(f"Node.js required: {e}")

    def _run_js_command(self, command: List[str], timeout: int = 60) -> Dict[str, Any]:
        try:
            cmd = ['node', str(self.js_wrapper_path)] + command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

            if result.returncode != 0:
                logger.error(f"JS command failed: {result.stderr}")
                return {"success": False, "error": result.stderr}

            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response: {result.stdout}")
                return {"success": False, "error": "Invalid JSON response"}

        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {command}")
            return {"success": False, "error": "Command timeout"}
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {"success": False, "error": str(e)}

    def initialize(self, rpc_url: Optional[str] = None, private_key: Optional[str] = None) -> Dict[str, Any]:
        try:
            command = ['init', self.network]
            if rpc_url:
                command.append(rpc_url)
            if private_key:
                command.append(private_key)

            result = self._run_js_command(command, timeout=120)

            if result.get('success'):
                self.is_initialized = True
                logger.info(f"Railgun initialized on {self.network}")

            return result
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return {"success": False, "error": str(e)}

    def create_wallet(self, mnemonic: Optional[str] = None, password: str = "defaultPassword") -> Dict[str, Any]:
        try:
            command = ['create-wallet']
            if mnemonic:
                command.append(mnemonic)
            command.append(password)

            result = self._run_js_command(command)

            if result.get('success') and 'wallet' in result:
                wallet_data = result['wallet']
                self.wallet = RailgunWallet(
                    id=wallet_data['id'],
                    address=wallet_data['address'],
                    mnemonic=wallet_data.get('mnemonic')
                )
                logger.info(f"Wallet created: {self.wallet.address}")

            return result
        except Exception as e:
            logger.error(f"Wallet creation failed: {e}")
            return {"success": False, "error": str(e)}

    def load_wallet(self, mnemonic: str, password: str = "defaultPassword") -> Dict[str, Any]:
        try:
            command = ['load-wallet', mnemonic, password]
            result = self._run_js_command(command)

            if result.get('success') and 'wallet' in result:
                wallet_data = result['wallet']
                self.wallet = RailgunWallet(
                    id=wallet_data['id'],
                    address=wallet_data['address']
                )
                logger.info(f"Wallet loaded: {self.wallet.address}")

            return result
        except Exception as e:
            logger.error(f"Wallet loading failed: {e}")
            return {"success": False, "error": str(e)}

    def get_balances(self) -> Dict[str, Any]:
        try:
            if not self.wallet:
                return {"success": False, "error": "No wallet loaded"}

            result = self._run_js_command(['balances'])
            return result
        except Exception as e:
            logger.error(f"Failed to get balances: {e}")
            return {"success": False, "error": str(e)}

    def shield_tokens(self, token_address: str, amount: str, gas_price: Optional[str] = None) -> TransactionResult:
        try:
            if not self.wallet:
                return TransactionResult(success=False, error="No wallet loaded")

            command = ['shield', token_address, amount]
            if gas_price:
                command.append(gas_price)

            result = self._run_js_command(command, timeout=300)

            return TransactionResult(
                success=result.get('success', False),
                tx_hash=result.get('txHash'),
                status=result.get('status'),
                gas_used=result.get('gasUsed'),
                block_number=result.get('blockNumber'),
                error=result.get('error')
            )
        except Exception as e:
            logger.error(f"Shield failed: {e}")
            return TransactionResult(success=False, error=str(e))

    def unshield_tokens(self, token_address: str, amount: str, recipient_address: str,
                        gas_price: Optional[str] = None) -> TransactionResult:
        try:
            if not self.wallet:
                return TransactionResult(success=False, error="No wallet loaded")

            command = ['unshield', token_address, amount, recipient_address]
            if gas_price:
                command.append(gas_price)

            result = self._run_js_command(command, timeout=300)

            return TransactionResult(
                success=result.get('success', False),
                tx_hash=result.get('txHash'),
                status=result.get('status'),
                gas_used=result.get('gasUsed'),
                block_number=result.get('blockNumber'),
                error=result.get('error')
            )
        except Exception as e:
            logger.error(f"Unshield failed: {e}")
            return TransactionResult(success=False, error=str(e))

    def private_transfer(self, token_address: str, amount: str, recipient_railgun_address: str,
                         gas_price: Optional[str] = None) -> TransactionResult:
        try:
            if not self.wallet:
                return TransactionResult(success=False, error="No wallet loaded")

            command = ['transfer', token_address, amount, recipient_railgun_address]
            if gas_price:
                command.append(gas_price)

            result = self._run_js_command(command, timeout=300)

            return TransactionResult(
                success=result.get('success', False),
                tx_hash=result.get('txHash'),
                status=result.get('status'),
                gas_used=result.get('gasUsed'),
                block_number=result.get('blockNumber'),
                error=result.get('error')
            )
        except Exception as e:
            logger.error(f"Private transfer failed: {e}")
            return TransactionResult(success=False, error=str(e))

    def get_transaction_history(self) -> Dict[str, Any]:
        try:
            if not self.wallet:
                return {"success": False, "error": "No wallet loaded"}

            result = self._run_js_command(['history'])
            return result
        except Exception as e:
            logger.error(f"Failed to get transaction history: {e}")
            return {"success": False, "error": str(e)}

    def scan_network(self) -> Dict[str, Any]:
        try:
            result = self._run_js_command(['scan'], timeout=600)
            return result
        except Exception as e:
            logger.error(f"Network scan failed: {e}")
            return {"success": False, "error": str(e)}

    def get_wallet_info(self) -> Dict[str, Any]:
        if not self.wallet:
            return {"error": "No wallet loaded"}

        return {
            "id": self.wallet.id,
            "address": self.wallet.address,
            "network": self.network,
            "mnemonic": self.wallet.mnemonic if self.wallet.mnemonic else "Not available"
        }

    def complete_transfer_process(self, token_address: str, amount: str, recipient_address: str) -> Dict[str, Any]:
        try:
            results = {
                "shield": None,
                "transfer": None,
                "unshield": None,
                "success": False
            }

            logger.info("Starting shield operation...")
            shield_result = self.shield_tokens(token_address, amount)
            results["shield"] = shield_result

            if not shield_result.success:
                return results

            logger.info("Shield completed, waiting before transfer...")
            import time
            time.sleep(30)

            logger.info("Starting private transfer...")
            transfer_result = self.private_transfer(token_address, amount, recipient_address)
            results["transfer"] = transfer_result

            if not transfer_result.success:
                return results

            logger.info("Transfer completed, waiting before unshield...")
            time.sleep(30)

            logger.info("Starting unshield operation...")
            unshield_result = self.unshield_tokens(token_address, amount, recipient_address)
            results["unshield"] = unshield_result

            results["success"] = unshield_result.success

            return results
        except Exception as e:
            logger.error(f"Complete transfer process failed: {e}")
            return {"success": False, "error": str(e)}


class RailgunConfig:
    def __init__(self):
        self.networks = {
            "ethereum": {
                "name": "ethereum",
                "chain_id": 1,
                "native_token": "0x0000000000000000000000000000000000000000",
                "tokens": {
                    "ETH": "0x0000000000000000000000000000000000000000",
                    "USDC": "0xA0b86a33E6441E8E0a6E8dF8A9f2c7D8E2E1E3B3",
                    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F"
                }
            },
            "polygon": {
                "name": "polygon",
                "chain_id": 137,
                "native_token": "0x0000000000000000000000000000000000000000",
                "tokens": {
                    "MATIC": "0x0000000000000000000000000000000000000000",
                    "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
                    "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
                }
            },
            "bsc": {
                "name": "bsc",
                "chain_id": 56,
                "native_token": "0x0000000000000000000000000000000000000000",
                "tokens": {
                    "BNB": "0x0000000000000000000000000000000000000000",
                    "USDT": "0x55d398326f99059fF775485246999027B3197955",
                    "BUSD": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"
                }
            }
        }

    def get_token_address(self, network: str, symbol: str) -> str:
        if network not in self.networks:
            raise ValueError(f"Unsupported network: {network}")
        if symbol not in self.networks[network]["tokens"]:
            raise ValueError(f"Unsupported token {symbol} on {network}")
        return self.networks[network]["tokens"][symbol]

    def get_network_info(self, network: str) -> Dict[str, Any]:
        if network not in self.networks:
            raise ValueError(f"Unsupported network: {network}")
        return self.networks[network]