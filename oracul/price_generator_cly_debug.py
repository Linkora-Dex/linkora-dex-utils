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
import time
import asyncio
import logging
import argparse
import sys
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import random
from web3 import Web3
from eth_account import Account


@dataclass
class TokenConfig:
    symbol: str
    address: str
    decimals: int = 18
    initial_price: float = 1.0
    volatility: float = 0.02


@dataclass
class PriceConfig:
    update_interval: int = 50
    display_interval: int = 10
    history_size: int = 100
    volatility_multiplier: float = 1.0
    enable_volatile_events: bool = True
    volatile_event_probability: float = 0.001
    max_price_change: float = 0.5
    min_price: float = 0.01
    base_gas_limit: int = 800000
    max_gas_limit: int = 1500000
    base_gas_price_gwei: int = 20
    max_gas_price_gwei: int = 100
    max_batch_size: int = 6
    retry_attempts: int = 5
    retry_delay_base: float = 1.0


class PriceHistory:
    def __init__(self, max_size: int = 100):
        self.prices: List[Tuple[float, float]] = []
        self.max_size = max_size

    def add(self, price: float, timestamp: float = None):
        if timestamp is None:
            timestamp = time.time()
        self.prices.append((price, timestamp))
        if len(self.prices) > self.max_size:
            self.prices.pop(0)

    def get_stats(self) -> Optional[Dict[str, float]]:
        if len(self.prices) < 2:
            return None

        current = self.prices[-1][0]
        previous = self.prices[-2][0]
        change = ((current - previous) / previous) * 100

        recent_prices = [p[0] for p in self.prices[-24:]]
        return {
            'current': current,
            'change': change,
            'min_24h': min(recent_prices),
            'max_24h': max(recent_prices),
            'count': len(self.prices)
        }


class PriceGenerator:

    def __init__(self, config_path: str = "../config/anvil_final-config.json"):
        self.config_path = Path(config_path)
        self.price_config = PriceConfig()
        self.tokens: Dict[str, TokenConfig] = {}
        self.price_history: Dict[str, PriceHistory] = {}
        self.current_prices: Dict[str, float] = {}
        self.is_running = False
        self.quiet = False
        self.system_operational = True

        self.w3: Optional[Web3] = None
        self.router = None
        self.access_control = None
        self.keeper_account = None

        self.failed_attempts = 0
        self.current_batch_size = 6
        self.adaptive_gas_multiplier = 1.0

        self.logger = self._setup_logging()
        self._load_env_file()
        self._load_config()

    def get_smart_gas_limit(self, tokens_count: int, attempt: int = 0) -> int:
        if tokens_count == 1:
            base_gas = 800000
        elif tokens_count <= 3:
            base_gas = 2500000
        else:
            base_gas = 1500000 + (tokens_count * 700000)

        retry_multiplier = 1.0 + (attempt * 0.2)
        failure_multiplier = 1.0 + (self.failed_attempts * 0.1)

        gas_limit = int(base_gas * retry_multiplier * failure_multiplier)
        return min(gas_limit, 8000000)

    def _setup_logging(self, level: str = "INFO") -> logging.Logger:
        log_level = getattr(logging, level.upper())
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def set_quiet(self, quiet: bool):
        self.quiet = quiet
        if quiet:
            self.logger.setLevel(logging.WARNING)

    def _load_env_file(self):
        env_path = self.config_path.parent.parent / ".env"
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            if not self.quiet:
                self.logger.info(f"Loaded environment variables from {env_path}")
        else:
            if not self.quiet:
                self.logger.warning(f"Environment file not found: {env_path}")

    def _load_config(self):
        config_paths = [
            self.config_path,
            self.config_path.parent / "anvil_final-config.json",
            self.config_path.parent / "anvil_upgradeable-config.json",
            self.config_path.parent / "deployment-config.json"
        ]

        loaded_config = None
        for config_path in config_paths:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    if not self.quiet:
                        self.logger.info(f"Loaded config: {config_path}")
                break

        if not loaded_config:
            raise FileNotFoundError(f"No config file found in: {config_paths}")

        contracts = loaded_config.get('contracts', {})
        if 'proxies' in loaded_config:
            contracts.update(loaded_config['proxies'])

        self.contract_addresses = contracts

        if not self.contract_addresses:
            raise ValueError("No contracts found in configuration")

        initial_prices = loaded_config.get('initialPrices', {})
        if not initial_prices:
            initial_prices = {
                'ETH': '2500',
                'CAPY': '1',
                'AXOL': '1',
                'QUOK': '45000',
                'PANG': '15',
                'NARW': '25'
            }

        self.tokens['ETH'] = TokenConfig('ETH', Web3.to_checksum_address('0x' + '0' * 40), 18, 2500.0, 0.01)

        tokens_config = loaded_config.get('tokens', {})
        for symbol, token_data in tokens_config.items():
            initial_price = float(initial_prices.get(symbol, "1.0"))
            self.tokens[symbol] = TokenConfig(
                symbol=symbol,
                address=Web3.to_checksum_address(token_data['address']),
                decimals=token_data['decimals'],
                initial_price=initial_price,
                volatility=self._calculate_volatility(initial_price)
            )

        for symbol, token in self.tokens.items():
            self.current_prices[symbol] = token.initial_price
            self.price_history[symbol] = PriceHistory(self.price_config.history_size)

    def _calculate_volatility(self, base_price: float) -> float:
        if base_price >= 10000:
            return 0.04
        elif base_price >= 10:
            return 0.05
        elif base_price <= 2:
            return 0.001
        return 0.03

    def configure(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.price_config, key):
                setattr(self.price_config, key, value)
                if not self.quiet:
                    self.logger.info(f"Config updated: {key} = {value}")

    async def initialize(self, rpc_url: str = "http://localhost:8545", private_key: str = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {rpc_url}")

        if private_key:
            if not private_key.startswith('0x'):
                private_key = '0x' + private_key
            self.keeper_account = Account.from_key(private_key)
        else:
            env_key = os.getenv('ANVIL_KEEPER_PRIVATE_KEY')
            if not env_key:
                raise ValueError("ANVIL_KEEPER_PRIVATE_KEY environment variable not set")

            if not env_key.startswith('0x'):
                env_key = '0x' + env_key
            self.keeper_account = Account.from_key(env_key)

            if not self.quiet:
                self.logger.info(f"Using keeper from ANVIL_KEEPER_PRIVATE_KEY: {self.keeper_account.address}")

        router_abi = self._load_abi('../artifacts/contracts/upgradeable/RouterUpgradeable.sol/RouterUpgradeable.json')
        access_abi = self._load_abi('../artifacts/contracts/access/AccessControl.sol/AccessControlContract.json')

        router_address = self.contract_addresses.get('Router') or self.contract_addresses.get('RouterProxy')
        access_address = self.contract_addresses.get('AccessControl')

        if not router_address:
            raise ValueError("Router contract address not found")
        if not access_address:
            raise ValueError("AccessControl contract address not found")

        self.router = self.w3.eth.contract(
            address=Web3.to_checksum_address(router_address),
            abi=router_abi
        )

        self.access_control = self.w3.eth.contract(
            address=Web3.to_checksum_address(access_address),
            abi=access_abi
        )

        try:
            keeper_role = self.access_control.functions.KEEPER_ROLE().call()
            has_keeper_role = self.access_control.functions.hasRole(keeper_role, self.keeper_account.address).call()

            if not self.quiet:
                self.logger.info(f"KEEPER_ROLE: {keeper_role.hex()}")
                self.logger.info(f"Keeper address: {self.keeper_account.address}")
                self.logger.info(f"Has KEEPER_ROLE: {has_keeper_role}")

            if not has_keeper_role:
                self.logger.error(f"❌ Keeper {self.keeper_account.address} does not have KEEPER_ROLE!")
                self.logger.error("Run: node admin-setup.js")
                raise PermissionError("Keeper lacks required KEEPER_ROLE")

            oracle_address = self.router.functions.oracle().call()
            if not self.quiet:
                self.logger.info(f"Router oracle address: {oracle_address}")

            is_paused = self.access_control.functions.emergencyStop().call()
            if not self.quiet:
                self.logger.info(f"System paused: {is_paused}")

            if is_paused:
                self.logger.warning("🚨 System is currently paused!")

            oracle_abi = self._load_abi('../artifacts/contracts/upgradeable/OracleUpgradeable.sol/OracleUpgradeable.json')
            oracle_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(oracle_address),
                abi=oracle_abi
            )

            if not self.quiet:
                self.logger.info("✅ Oracle contract accessible")

        except Exception as e:
            self.logger.error(f"Permission check failed: {e}")
            self.logger.warning("Continuing despite permission check failure...")

        if not self.quiet:
            self.logger.info(f"Initialized with keeper: {self.keeper_account.address}")
            self.logger.info(f"Router: {self.router.address}")
            self.logger.info(f"Tokens: {list(self.tokens.keys())}")
            self.logger.info("✅ Basic initialization completed")

    def _load_abi(self, path: str) -> List:
        try:
            with open(path, 'r') as f:
                return json.load(f)['abi']
        except FileNotFoundError:
            self.logger.error(f"ABI file not found: {path}")
            sys.exit(1)

    async def is_system_operational(self) -> bool:
        try:
            is_operational = not self.access_control.functions.emergencyStop().call()
            self.system_operational = is_operational
            return is_operational
        except Exception as e:
            if not self.quiet:
                self.logger.error(f"Error checking system status: {e}")
            return False

    async def wait_for_system_unpause(self):
        if not self.quiet:
            self.logger.warning("🔴 System paused - waiting for unpause...")
        while not await self.is_system_operational():
            await asyncio.sleep(3)
        if not self.quiet:
            self.logger.info("🟢 System operational - resuming...")

    def generate_price(self, symbol: str) -> float:
        token = self.tokens[symbol]
        current = self.current_prices[symbol]

        volatility = token.volatility * self.price_config.volatility_multiplier

        if (self.price_config.enable_volatile_events and
                random.random() < self.price_config.volatile_event_probability):
            volatility *= random.uniform(2, 5)
            if not self.quiet:
                self.logger.info(f"🚨 Volatile event for {symbol}")

        change = (random.random() - 0.5) * 2 * volatility
        change = max(-self.price_config.max_price_change,
                     min(self.price_config.max_price_change, change))

        new_price = current * (1 + change)
        return max(new_price, self.price_config.min_price)

    async def get_dynamic_gas_price(self) -> int:
        try:
            latest_gas_price = self.w3.eth.gas_price
            network_gas_price_gwei = Web3.from_wei(latest_gas_price, 'gwei')

            adjusted_gas_price = max(
                self.price_config.base_gas_price_gwei,
                min(network_gas_price_gwei * 1.2, self.price_config.max_gas_price_gwei)
            )

            final_gas_price = int(adjusted_gas_price * self.adaptive_gas_multiplier)

            self.logger.debug(f"Gas price: network={network_gas_price_gwei:.1f}, adjusted={adjusted_gas_price:.1f}, final={final_gas_price}")

            return Web3.to_wei(final_gas_price, 'gwei')

        except Exception as e:
            self.logger.debug(f"Failed to get dynamic gas price: {e}")
            return Web3.to_wei(self.price_config.base_gas_price_gwei, 'gwei')

    def get_adaptive_gas_limit(self, num_tokens: int) -> int:
        base_gas_per_token = self.price_config.base_gas_limit // 6
        gas_limit = base_gas_per_token * num_tokens
        gas_limit = int(gas_limit * self.adaptive_gas_multiplier)

        return min(gas_limit, self.price_config.max_gas_limit)

    def adjust_batch_size_on_failure(self):
        self.failed_attempts += 1

        if self.failed_attempts >= 2:
            self.current_batch_size = max(2, self.current_batch_size - 1)
            self.adaptive_gas_multiplier = min(2.0, self.adaptive_gas_multiplier * 1.2)
            self.logger.warning(f"Reducing batch size to {self.current_batch_size}, gas multiplier to {self.adaptive_gas_multiplier:.2f}")

        if self.failed_attempts >= 4:
            self.current_batch_size = 1
            self.adaptive_gas_multiplier = 2.0
            self.logger.warning("Fallback to individual updates")

    def reset_adaptive_params_on_success(self):
        if self.failed_attempts > 0:
            self.failed_attempts = max(0, self.failed_attempts - 1)

        if self.failed_attempts == 0:
            if self.current_batch_size < self.price_config.max_batch_size:
                self.current_batch_size = min(self.price_config.max_batch_size, self.current_batch_size + 1)

            self.adaptive_gas_multiplier = max(1.0, self.adaptive_gas_multiplier * 0.95)

    async def update_prices_with_retry(self, tokens: List[str], prices: List[int], updates: Dict[str, float]) -> bool:
        self.logger.info(f"Attempting update: keeper={self.keeper_account.address}")

        try:
            balance = self.w3.eth.get_balance(self.keeper_account.address)
            self.logger.info(f"Keeper balance: {Web3.from_wei(balance, 'ether')} ETH")

            nonce = self.w3.eth.get_transaction_count(self.keeper_account.address)
            self.logger.info(f"Keeper nonce: {nonce}")

            network_gas = self.w3.eth.gas_price
            self.logger.info(f"Network gas price: {Web3.from_wei(network_gas, 'gwei')} gwei")

        except Exception as e:
            self.logger.error(f"Pre-flight check failed: {e}")
            return False

        for attempt in range(self.price_config.retry_attempts):
            try:
                gas_price = await self.get_dynamic_gas_price()
                gas_limit = self.get_smart_gas_limit(len(tokens), attempt)
                nonce = self.w3.eth.get_transaction_count(self.keeper_account.address)

                self.logger.debug(f"Attempt {attempt + 1}: tokens={len(tokens)}, gas_limit={gas_limit}, gas_price={Web3.from_wei(gas_price, 'gwei'):.1f} gwei")

                if len(tokens) == 1:
                    tx_function = self.router.functions.updateOraclePrice(tokens[0], prices[0])
                else:
                    tx_function = self.router.functions.batchUpdateOraclePrices(tokens, prices)

                try:
                    if len(tokens) == 1:
                        self.logger.info(f"Testing updateOraclePrice call for {tokens[0]}")
                        result = tx_function.call({'from': self.keeper_account.address})
                        self.logger.info(f"Call successful, result: {result}")
                    else:
                        self.logger.info(f"Testing batchUpdateOraclePrices call for {len(tokens)} tokens")
                        result = tx_function.call({'from': self.keeper_account.address})
                        self.logger.info(f"Call successful, result: {result}")
                except Exception as call_error:
                    self.logger.error(f"Contract call failed: {call_error}")
                    self.logger.error(f"Call error type: {type(call_error).__name__}")
                    self.logger.error(f"Call error details: {str(call_error)}")
                    return False

                tx_data = tx_function.build_transaction({
                    'from': self.keeper_account.address,
                    'gas': gas_limit,
                    'gasPrice': gas_price,
                    'nonce': nonce
                })

                self.logger.info(f"Transaction data built: gas={gas_limit}, gasPrice={Web3.from_wei(gas_price, 'gwei'):.1f} gwei")

                signed_tx = self.keeper_account.sign_transaction(tx_data)
                self.logger.info(f"Transaction signed, hash: {signed_tx.hash.hex()}")

                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                self.logger.info(f"Transaction sent, waiting for receipt...")

                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

                if receipt.status == 1:
                    self.reset_adaptive_params_on_success()
                    if not self.quiet:
                        method = "individual" if len(tokens) == 1 else "batch"
                        self.logger.info(f"✅ {method} update successful: {len(tokens)} tokens, gas used: {receipt.gasUsed}")
                    return True
                else:
                    self.logger.error(f"Transaction failed with status: {receipt.status}")

            except Exception as e:
                retry_delay = self.price_config.retry_delay_base * (2 ** attempt)
                error_msg = str(e)

                self.logger.error(f"Attempt {attempt + 1} failed: {type(e).__name__}")
                self.logger.error(f"Full error message: {error_msg}")

                if hasattr(e, 'response'):
                    self.logger.error(f"Error response: {e.response}")
                if hasattr(e, 'code'):
                    self.logger.error(f"Error code: {e.code}")
                if hasattr(e, 'message'):
                    self.logger.error(f"Error message detail: {e.message}")

                import traceback
                self.logger.error(f"Full traceback:\n{traceback.format_exc()}")

                if "out of gas" in error_msg.lower():
                    self.adaptive_gas_multiplier = min(2.0, self.adaptive_gas_multiplier * 1.3)
                    self.logger.warning(f"Gas insufficient, increasing multiplier to {self.adaptive_gas_multiplier:.2f}")
                elif "price change too large" in error_msg.lower():
                    self.logger.warning("Circuit breaker triggered")
                    return False
                elif "execution reverted" in error_msg.lower():
                    self.logger.error("Contract execution reverted - checking permissions and contract state")
                    return False

                if attempt < self.price_config.retry_attempts - 1:
                    self.logger.debug(f"Retrying in {retry_delay:.1f}s...")
                    await asyncio.sleep(retry_delay)

        return False

    async def update_prices(self):
        if not await self.is_system_operational():
            await self.wait_for_system_unpause()
            return

        tokens = []
        prices = []
        updates = {}

        for symbol, token in self.tokens.items():
            new_price = self.generate_price(symbol)
            self.current_prices[symbol] = new_price
            self.price_history[symbol].add(new_price)
            updates[symbol] = new_price

            tokens.append(token.address)
            prices.append(Web3.to_wei(new_price, 'ether'))

        token_batches = []
        price_batches = []
        update_batches = []

        for i in range(0, len(tokens), self.current_batch_size):
            end_idx = min(i + self.current_batch_size, len(tokens))
            token_batch = tokens[i:end_idx]
            price_batch = prices[i:end_idx]
            update_batch = {k: v for j, (k, v) in enumerate(updates.items()) if i <= j < end_idx}

            token_batches.append(token_batch)
            price_batches.append(price_batch)
            update_batches.append(update_batch)

        all_success = True

        for token_batch, price_batch, update_batch in zip(token_batches, price_batches, update_batches):
            success = await self.update_prices_with_retry(token_batch, price_batch, update_batch)
            if not success:
                all_success = False
                self.adjust_batch_size_on_failure()

                if len(token_batch) > 1:
                    self.logger.info(f"Falling back to individual updates for batch: {list(update_batch.keys())}")
                    for token_addr, price, (symbol, new_price) in zip(token_batch, price_batch, update_batch.items()):
                        individual_success = await self.update_prices_with_retry([token_addr], [price], {symbol: new_price})
                        if individual_success and not self.quiet:
                            self.logger.info(f"✅ {symbol}: ${new_price:.6f} (individual)")

        if all_success:
            self.reset_adaptive_params_on_success()

    async def display_prices(self):
        if self.quiet:
            return

        status = "🟢 OPERATIONAL" if self.system_operational else "🔴 PAUSED"

        print("\033[2J\033[H")
        print("=" * 80)
        print(f" LIVE PRICE FEED via Router [{status}]")
        print("=" * 80)
        print("Symbol".ljust(10) + "Price".ljust(15) + "Change%".ljust(12) + "24h Low".ljust(12) + "24h High")
        print("-" * 80)

        for symbol in self.tokens.keys():
            stats = self.price_history[symbol].get_stats()
            if stats:
                change_str = f"+{stats['change']:.2f}%" if stats['change'] >= 0 else f"{stats['change']:.2f}%"
                print(
                    symbol.ljust(10) +
                    f"${stats['current']:.6f}".ljust(15) +
                    change_str.ljust(12) +
                    f"${stats['min_24h']:.6f}".ljust(12) +
                    f"${stats['max_24h']:.6f}"
                )

        print("-" * 80)
        adaptive_info = f"Batch: {self.current_batch_size}, Gas: {self.adaptive_gas_multiplier:.1f}x, Fails: {self.failed_attempts}"
        print(f"Last update: {time.strftime('%H:%M:%S')} | {adaptive_info}")
        if status == "🔴 PAUSED":
            print("🚨 Run 'npm run unpause' to resume")
        print("Press Ctrl+C to stop")

    async def generate_volatile_event(self, symbol: str, multiplier: float = 2.0):
        if symbol not in self.tokens:
            return

        if not self.quiet:
            self.logger.info(f"🚨 Generating volatile event for {symbol}")

        current = self.current_prices[symbol]
        direction = 1 if random.random() > 0.5 else -1
        shock_price = current * (1 + direction * 0.1 * multiplier)

        self.current_prices[symbol] = shock_price

        try:
            token_addr = self.tokens[symbol].address
            price_wei = Web3.to_wei(shock_price, 'ether')

            success = await self.update_prices_with_retry([token_addr], [price_wei], {symbol: shock_price})

            if success and not self.quiet:
                action = "surged" if direction > 0 else "crashed"
                self.logger.info(f"💥 {symbol} {action} to ${shock_price:.6f}")
            elif not success:
                self.logger.error(f"Volatile event failed for {symbol}")

        except Exception as e:
            self.logger.error(f"Volatile event error for {symbol}: {str(e)}")

    async def start(self):
        if self.is_running:
            return

        self.is_running = True
        if not self.quiet:
            self.logger.info("🚀 Starting Python price generator with smart retry logic...")

        async def update_loop():
            while self.is_running:
                await self.update_prices()
                await asyncio.sleep(self.price_config.update_interval)

        async def display_loop():
            while self.is_running:
                await self.display_prices()
                await asyncio.sleep(self.price_config.display_interval)

        async def event_loop():
            await asyncio.sleep(30)
            while self.is_running:
                if self.price_config.enable_volatile_events:
                    symbol = random.choice(list(self.tokens.keys()))
                    await self.generate_volatile_event(symbol)
                await asyncio.sleep(60)

        try:
            if self.quiet:
                await update_loop()
            else:
                await asyncio.gather(update_loop(), display_loop(), event_loop())
        except KeyboardInterrupt:
            if not self.quiet:
                self.logger.info("🛑 Stopping price generator...")
        finally:
            self.is_running = False

    def stop(self):
        self.is_running = False


def parse_args():
    parser = argparse.ArgumentParser(description='Python Price Generator for DEX')

    parser.add_argument('--config', type=str, default='../config/anvil_final-config.json',
                        help='Path to config file')
    parser.add_argument('--rpc-url', type=str, default='http://localhost:8545',
                        help='RPC endpoint URL')
    parser.add_argument('--private-key', type=str,
                        help='Keeper private key (overrides config)')
    parser.add_argument('--update-interval', type=int, default=5,
                        help='Price update interval in seconds')
    parser.add_argument('--volatility', type=float, default=1.0,
                        help='Volatility multiplier (1.0 = normal)')
    parser.add_argument('--no-events', action='store_true',
                        help='Disable volatile events')
    parser.add_argument('--event-probability', type=float, default=0.001,
                        help='Volatile event probability per cycle')
    parser.add_argument('--max-change', type=float, default=0.5,
                        help='Maximum price change per update')
    parser.add_argument('--history-size', type=int, default=100,
                        help='Price history size for stats')
    parser.add_argument('--quiet', action='store_true',
                        help='Minimal output mode')
    parser.add_argument('--verbose', action='store_true',
                        help='Verbose logging')
    parser.add_argument('--debug', action='store_true',
                        help='Debug logging with full error details')
    parser.add_argument('--mode', choices=['conservative', 'aggressive', 'test'],
                        help='Predefined configuration mode')

    return parser.parse_args()


def setup_mode_config(generator: PriceGenerator, mode: str):
    if mode == 'conservative':
        generator.configure(
            update_interval=10,
            volatility_multiplier=0.5,
            enable_volatile_events=False,
            max_price_change=0.1
        )
    elif mode == 'aggressive':
        generator.configure(
            update_interval=2,
            volatility_multiplier=3.0,
            enable_volatile_events=True,
            volatile_event_probability=0.01,
            max_price_change=1.0
        )
    elif mode == 'test':
        generator.configure(
            update_interval=1,
            volatility_multiplier=5.0,
            enable_volatile_events=True,
            volatile_event_probability=0.05,
            max_price_change=2.0
        )


async def main():
    args = parse_args()

    try:
        generator = PriceGenerator(args.config)

        if args.quiet:
            generator.set_quiet(True)
        elif args.verbose or args.debug:
            level = 'DEBUG' if args.debug else 'INFO'
            generator._setup_logging(level)

        if args.mode:
            setup_mode_config(generator, args.mode)
            if not args.quiet:
                print(f"🎯 Using {args.mode} mode configuration")

        generator.configure(
            update_interval=args.update_interval,
            volatility_multiplier=args.volatility,
            enable_volatile_events=not args.no_events,
            volatile_event_probability=args.event_probability,
            max_price_change=args.max_change,
            history_size=args.history_size
        )

        if not args.quiet:
            print("🚀 Python Price Generator for DEX (Smart Retry)")
            print(f"Config: {args.config}")
            print(f"RPC: {args.rpc_url}")
            print(f"Update interval: {args.update_interval}s")
            print(f"Volatility: {args.volatility}x")
            print(f"Volatile events: {'disabled' if args.no_events else 'enabled'}")
            if args.mode:
                print(f"Mode: {args.mode}")
            print("Features: Dynamic Gas + Smart Retry + Adaptive Batching")
            print()

        await generator.initialize(args.rpc_url, args.private_key)
        await generator.start()

    except FileNotFoundError as e:
        print(f"❌ Config error: {e}")
        print("Run deployment first: npm run full-deploy")
        sys.exit(1)
    except ConnectionError as e:
        print(f"❌ Network error: {e}")
        print("Make sure Hardhat node is running: npx hardhat node")
        sys.exit(1)
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n🛑 Price generator stopped")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose or args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())