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
import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path


@dataclass
class KeeperConfig:
    rpc_url: str = "http://localhost:8545"
    private_key: str = ""
    keeper_address: str = ""
    order_check_interval: int = 5
    position_check_interval: int = 8
    oracle_check_interval: int = 10
    liquidation_threshold: int = -90
    max_gas_price: int = 50000000000
    gas_limit: int = 500000
    transaction_timeout: int = 120
    log_level: str = "INFO"
    enable_diagnostics: bool = True
    diagnostics_interval: int = 30
    contracts: Dict[str, str] = field(default_factory=dict)
    tokens: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    retry_attempts: int = 3
    retry_delay: int = 2
    retry_multiplier: float = 1.5
    max_retry_delay: int = 30
    max_orders_per_batch: int = 10
    enable_order_execution: bool = True
    enable_position_liquidation: bool = True
    enable_oracle_monitoring: bool = True
    enable_emergency_checks: bool = True
    safety_checks_enabled: bool = True
    balance_validation_enabled: bool = True
    liquidity_validation_enabled: bool = True
    gas_estimation_buffer: float = 1.2
    min_gas_price: int = 1000000000
    nonce_management: str = "auto"
    transaction_receipt_timeout: int = 180


class ConfigManager:
    def __init__(self, config_path: str = "../config/anvil_final-config.json"):
        self.config_path = Path(config_path)
        self.config = KeeperConfig()
        self._load_env_file()
        self._load_config()

    def _load_env_file(self):
        env_path = self.config_path.parent.parent / ".env"
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            print(f"✅ Loaded environment variables from {env_path}")

    def _load_config(self):
        config_paths = [
            self.config_path.parent / "anvil_final-config.json",
            self.config_path.parent / "anvil_upgradeable-config.json",
            self.config_path,
            self.config_path.parent / "deployment-config.json",
            self.config_path.parent / "deployed-config.json"
        ]

        loaded_config = None
        for config_path in config_paths:
            if config_path.exists():
                print(f"📋 Loading config: {config_path}")
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                break

        if not loaded_config:
            raise FileNotFoundError(f"No config file found in: {config_paths}")

        self.config.contracts = loaded_config.get('contracts', {})
        if 'proxies' in loaded_config:
            self.config.contracts.update(loaded_config['proxies'])
        self.config.tokens = loaded_config.get('tokens', {})
        accounts = loaded_config.get('accounts', {})
        if 'keeper' in accounts:
            self.config.keeper_address = accounts['keeper']
        self._load_keeper_credentials()
        self._apply_network_specific_settings()

    def _load_keeper_credentials(self):
        keeper_config_path = self.config_path.parent / "keeper-config.json"
        if keeper_config_path.exists():
            try:
                with open(keeper_config_path, 'r') as f:
                    keeper_data = json.load(f)
                self.config.private_key = keeper_data.get('private_key', '')
                self.config.rpc_url = keeper_data.get('rpc_url', self.config.rpc_url)
                self.config.max_gas_price = keeper_data.get('max_gas_price', self.config.max_gas_price)
                self.config.gas_limit = keeper_data.get('gas_limit', self.config.gas_limit)
                self.config.transaction_timeout = keeper_data.get('transaction_timeout', self.config.transaction_timeout)
                print(f"✅ Loaded keeper credentials from {keeper_config_path}")
            except Exception as e:
                print(f"⚠️ Warning: Could not load keeper config: {e}")

        if not self.config.private_key:
            anvil_key = os.getenv('ANVIL_KEEPER_PRIVATE_KEY')
            if anvil_key:
                if not anvil_key.startswith('0x'):
                    anvil_key = '0x' + anvil_key
                self.config.private_key = anvil_key
                print("✅ Loaded private key from ANVIL_KEEPER_PRIVATE_KEY")

        if not self.config.private_key:
            env_key = os.getenv('KEEPER_PRIVATE_KEY')
            if env_key:
                if not env_key.startswith('0x'):
                    env_key = '0x' + env_key
                self.config.private_key = env_key
                print("✅ Loaded private key from KEEPER_PRIVATE_KEY")

        if not self.config.rpc_url or self.config.rpc_url == "http://localhost:8545":
            env_rpc = os.getenv('RPC_URL')
            if env_rpc:
                self.config.rpc_url = env_rpc
                print(f"✅ Loaded RPC URL from environment variable: {env_rpc}")

    def _apply_network_specific_settings(self):
        """Применение настроек в зависимости от сети"""
        rpc_url = self.config.rpc_url.lower()

        if 'localhost' in rpc_url or '127.0.0.1' in rpc_url:
            self.config.max_gas_price = 50000000000
            self.config.gas_limit = 500000
            self.config.transaction_timeout = 60
            self.config.retry_attempts = 2
            self.config.enable_diagnostics = True
            print("🔧 Applied localhost network settings")
        elif 'mainnet' in rpc_url or 'ethereum' in rpc_url:
            self.config.max_gas_price = 100000000000
            self.config.gas_limit = 300000
            self.config.transaction_timeout = 300
            self.config.retry_attempts = 5
            self.config.enable_diagnostics = False
            print("🔧 Applied mainnet network settings")
        elif 'sepolia' in rpc_url or 'goerli' in rpc_url:
            self.config.max_gas_price = 30000000000
            self.config.gas_limit = 400000
            self.config.transaction_timeout = 180
            self.config.retry_attempts = 3
            self.config.enable_diagnostics = True
            print("🔧 Applied testnet network settings")

    def get_retry_config(self) -> Dict[str, Any]:
        """Получение конфигурации retry логики"""
        return {
            'max_attempts': self.config.retry_attempts,
            'base_delay': self.config.retry_delay,
            'multiplier': self.config.retry_multiplier,
            'max_delay': self.config.max_retry_delay,
            'timeout': self.config.transaction_timeout
        }

    def get_gas_config(self) -> Dict[str, Any]:
        """Получение конфигурации gas параметров"""
        return {
            'max_gas_price': self.config.max_gas_price,
            'min_gas_price': self.config.min_gas_price,
            'gas_limit': self.config.gas_limit,
            'estimation_buffer': self.config.gas_estimation_buffer
        }

    def get_safety_config(self) -> Dict[str, bool]:
        """Получение конфигурации безопасности"""
        return {
            'emergency_checks': self.config.enable_emergency_checks,
            'safety_checks': self.config.safety_checks_enabled,
            'balance_validation': self.config.balance_validation_enabled,
            'liquidity_validation': self.config.liquidity_validation_enabled
        }

    def update_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def get_contract_address(self, contract_name: str) -> str:
        address = self.config.contracts.get(contract_name, "")
        if not address and contract_name == 'Router':
            address = self.config.contracts.get('RouterProxy', "")
        return address

    def get_token_config(self, symbol: str) -> Dict[str, Any]:
        return self.config.tokens.get(symbol, {})

    def validate_config(self) -> List[str]:
        errors = []

        if not self.config.private_key:
            errors.append("Private key not set")

        router_address = self.get_contract_address('Router')
        if not router_address:
            errors.append("Contract Router address not found")

        if self.config.order_check_interval < 1:
            errors.append("Order check interval must be >= 1")

        if self.config.liquidation_threshold >= 0:
            errors.append("Liquidation threshold must be negative")

        if self.config.max_gas_price < self.config.min_gas_price:
            errors.append("Max gas price must be >= min gas price")

        if self.config.gas_limit < 21000:
            errors.append("Gas limit too low")

        if self.config.transaction_timeout < 30:
            errors.append("Transaction timeout too low")

        if self.config.retry_attempts < 1:
            errors.append("Retry attempts must be >= 1")

        if self.config.retry_delay < 1:
            errors.append("Retry delay must be >= 1")

        return errors

    def is_valid(self) -> bool:
        """Проверка корректности конфигурации"""
        return len(self.validate_config()) == 0

    def get_network_info(self) -> Dict[str, Any]:
        """Получение информации о сети"""
        return {
            'rpc_url': self.config.rpc_url,
            'max_gas_price': self.config.max_gas_price,
            'gas_limit': self.config.gas_limit,
            'timeout': self.config.transaction_timeout,
            'retry_attempts': self.config.retry_attempts
        }

    def save_config(self, path: str):
        """Сохранение конфигурации в файл"""
        config_dict = {
            'rpc_url': self.config.rpc_url,
            'max_gas_price': self.config.max_gas_price,
            'gas_limit': self.config.gas_limit,
            'transaction_timeout': self.config.transaction_timeout,
            'retry_attempts': self.config.retry_attempts,
            'retry_delay': self.config.retry_delay,
            'enable_diagnostics': self.config.enable_diagnostics,
            'safety_checks_enabled': self.config.safety_checks_enabled
        }

        with open(path, 'w') as f:
            json.dump(config_dict, f, indent=2)

    def load_config_from_file(self, path: str):
        """Загрузка конфигурации из файла"""
        if Path(path).exists():
            with open(path, 'r') as f:
                config_data = json.load(f)

            for key, value in config_data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)