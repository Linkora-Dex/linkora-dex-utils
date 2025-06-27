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
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path


@dataclass
class DemoPhaseConfig:
    name: str
    enabled: bool = True
    sleep_after: float = 2.0
    continue_on_error: bool = True


@dataclass
class OrderDemoConfig:
    limit_order_enabled: bool = True
    stop_loss_enabled: bool = True
    self_executable_enabled: bool = True
    modification_enabled: bool = True
    cancellation_enabled: bool = True
    eth_amount: float = 0.1
    price_adjustment: float = 1.05
    stop_loss_price_drop: float = 0.9
    slippage_tolerance: float = 0.1


@dataclass
class DiagnosticsConfig:
    enabled: bool = True
    detailed_logging: bool = True
    transaction_analysis: bool = True
    gas_tracking: bool = True
    balance_monitoring: bool = True
    system_state_checks: bool = True
    emergency_pause_detection: bool = True
    liquidity_validation: bool = True
    network_performance_monitoring: bool = True


@dataclass
class SafetyConfig:
    pre_transaction_checks: bool = True
    balance_validation: bool = True
    contract_state_validation: bool = True
    gas_price_validation: bool = True
    emergency_pause_check: bool = True
    liquidity_check: bool = True
    retry_failed_transactions: bool = True
    max_transaction_retries: int = 3
    transaction_timeout: int = 120
    safety_delay_between_operations: float = 1.0


@dataclass
class TradingDemoConfig:
    config_path: str = "../config/anvil_final-config.json"
    phases: Dict[str, DemoPhaseConfig] = field(default_factory=lambda: {
        "setup": DemoPhaseConfig("User Funds Setup"),
        "basic_trading": DemoPhaseConfig("Basic Trading & Security"),
        "advanced_orders": DemoPhaseConfig("Advanced Order Types"),
        "order_management": DemoPhaseConfig("Order Management"),
        "emergency_features": DemoPhaseConfig("Emergency & Security"),
        "self_execution": DemoPhaseConfig("Self-Execution Demo")
    })
    initial_eth_deposit: float = 10.0
    initial_token_deposit: float = 1000.0
    mint_if_insufficient: bool = True
    swap_amount: float = 0.5
    retry_with_smaller_amount: bool = True
    smaller_amount: float = 0.1
    increased_slippage: float = 0.2
    orders: OrderDemoConfig = field(default_factory=OrderDemoConfig)
    diagnostics: DiagnosticsConfig = field(default_factory=DiagnosticsConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    show_detailed_balances: bool = True
    show_price_debugging: bool = True
    show_security_features: bool = True
    show_transaction_details: bool = True
    show_gas_usage: bool = True
    show_system_diagnostics: bool = True
    ascii_art_enabled: bool = True
    test_emergency_pause: bool = True
    emergency_test_amount: float = 0.01
    verbose: bool = True
    log_level: str = "INFO"
    enable_performance_metrics: bool = True
    track_transaction_costs: bool = True


class DemoConfigManager:
    def __init__(self, config_path: str = None):
        self.config = TradingDemoConfig()
        if config_path:
            self.config.config_path = config_path
        self._load_deployed_config()

    def _load_deployed_config(self):
        config_paths = [
            Path(self.config.config_path),
            Path(self.config.config_path).parent / "anvil_final-config.json",
            Path(self.config.config_path).parent / "anvil_upgradeable-config.json",
            Path(self.config.config_path).parent / "deployment-config.json",
            Path(self.config.config_path).parent / "deployed-config.json"
        ]

        loaded = False
        for config_path in config_paths:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.deployed_config = json.load(f)
                    loaded = True
                    break

        if not loaded:
            raise FileNotFoundError(f"No config file found in: {config_paths}")

    def update_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def update_diagnostics_config(self, **kwargs):
        """Обновление конфигурации диагностики"""
        for key, value in kwargs.items():
            if hasattr(self.config.diagnostics, key):
                setattr(self.config.diagnostics, key, value)

    def update_safety_config(self, **kwargs):
        """Обновление конфигурации безопасности"""
        for key, value in kwargs.items():
            if hasattr(self.config.safety, key):
                setattr(self.config.safety, key, value)

    def enable_phase(self, phase_name: str, enabled: bool = True):
        if phase_name in self.config.phases:
            self.config.phases[phase_name].enabled = enabled

    def disable_phase(self, phase_name: str):
        self.enable_phase(phase_name, False)

    def set_phase_sleep(self, phase_name: str, sleep_time: float):
        if phase_name in self.config.phases:
            self.config.phases[phase_name].sleep_after = sleep_time

    def enable_diagnostics_mode(self):
        """Включение полной диагностики"""
        self.config.diagnostics.enabled = True
        self.config.diagnostics.detailed_logging = True
        self.config.diagnostics.transaction_analysis = True
        self.config.diagnostics.gas_tracking = True
        self.config.diagnostics.balance_monitoring = True
        self.config.diagnostics.system_state_checks = True
        self.config.show_detailed_balances = True
        self.config.show_transaction_details = True
        self.config.show_gas_usage = True
        self.config.show_system_diagnostics = True
        self.config.log_level = "DEBUG"

    def enable_safety_mode(self):
        """Включение максимальной безопасности"""
        self.config.safety.pre_transaction_checks = True
        self.config.safety.balance_validation = True
        self.config.safety.contract_state_validation = True
        self.config.safety.gas_price_validation = True
        self.config.safety.emergency_pause_check = True
        self.config.safety.liquidity_check = True
        self.config.safety.retry_failed_transactions = True
        self.config.safety.safety_delay_between_operations = 2.0

    def enable_performance_mode(self):
        """Включение отслеживания производительности"""
        self.config.enable_performance_metrics = True
        self.config.track_transaction_costs = True
        self.config.diagnostics.gas_tracking = True
        self.config.diagnostics.network_performance_monitoring = True

    def get_contract_address(self, contract_name: str) -> str:
        contracts = self.deployed_config.get('contracts', {})
        if 'proxies' in self.deployed_config:
            contracts.update(self.deployed_config['proxies'])
        return contracts.get(contract_name, "")

    def get_token_config(self, symbol: str) -> Dict[str, Any]:
        return self.deployed_config.get('tokens', {}).get(symbol, {})

    def get_all_tokens(self) -> Dict[str, Dict[str, Any]]:
        return self.deployed_config.get('tokens', {})

    def get_accounts(self) -> Dict[str, str]:
        return self.deployed_config.get('accounts', {})

    def get_features(self) -> Dict[str, bool]:
        return self.deployed_config.get('features', {})

    def get_diagnostics_config(self) -> Dict[str, Any]:
        """Получение настроек диагностики"""
        return {
            'enabled': self.config.diagnostics.enabled,
            'detailed_logging': self.config.diagnostics.detailed_logging,
            'transaction_analysis': self.config.diagnostics.transaction_analysis,
            'gas_tracking': self.config.diagnostics.gas_tracking,
            'balance_monitoring': self.config.diagnostics.balance_monitoring,
            'system_state_checks': self.config.diagnostics.system_state_checks,
            'emergency_pause_detection': self.config.diagnostics.emergency_pause_detection,
            'liquidity_validation': self.config.diagnostics.liquidity_validation
        }

    def get_safety_config(self) -> Dict[str, Any]:
        """Получение настроек безопасности"""
        return {
            'pre_transaction_checks': self.config.safety.pre_transaction_checks,
            'balance_validation': self.config.safety.balance_validation,
            'contract_state_validation': self.config.safety.contract_state_validation,
            'gas_price_validation': self.config.safety.gas_price_validation,
            'emergency_pause_check': self.config.safety.emergency_pause_check,
            'liquidity_check': self.config.safety.liquidity_check,
            'retry_failed_transactions': self.config.safety.retry_failed_transactions,
            'max_retries': self.config.safety.max_transaction_retries,
            'timeout': self.config.safety.transaction_timeout
        }

    def quick_setup(self, mode: str = "full"):
        if mode == "minimal":
            self.disable_phase("emergency_features")
            self.disable_phase("self_execution")
            self.config.orders.modification_enabled = False
            self.config.orders.cancellation_enabled = False
            self.config.ascii_art_enabled = False
            self.config.diagnostics.enabled = False
        elif mode == "orders_only":
            self.disable_phase("basic_trading")
            self.disable_phase("emergency_features")
            self.disable_phase("self_execution")
        elif mode == "security_focus":
            self.disable_phase("basic_trading")
            self.disable_phase("order_management")
            self.config.test_emergency_pause = True
            self.enable_safety_mode()
        elif mode == "fast":
            for phase in self.config.phases.values():
                phase.sleep_after = 0.5
            self.config.ascii_art_enabled = False
            self.config.show_detailed_balances = False
            self.config.safety.safety_delay_between_operations = 0.2
        elif mode == "debug":
            self.enable_diagnostics_mode()
            self.enable_safety_mode()
            self.config.log_level = "DEBUG"
        elif mode == "production":
            self.config.diagnostics.enabled = False
            self.config.show_detailed_balances = False
            self.config.ascii_art_enabled = False
            self.config.log_level = "WARNING"
            self.enable_safety_mode()

    def configure_for_network(self, network_type: str):
        """Настройка конфигурации для типа сети"""
        if network_type == "localhost":
            self.config.safety.transaction_timeout = 60
            self.config.safety.max_transaction_retries = 2
            self.enable_diagnostics_mode()
        elif network_type == "testnet":
            self.config.safety.transaction_timeout = 180
            self.config.safety.max_transaction_retries = 3
            self.config.diagnostics.enabled = True
        elif network_type == "mainnet":
            self.config.safety.transaction_timeout = 300
            self.config.safety.max_transaction_retries = 5
            self.enable_safety_mode()
            self.config.diagnostics.enabled = False

    def validate_demo_config(self) -> List[str]:
        """Валидация конфигурации демо"""
        errors = []

        if self.config.initial_eth_deposit <= 0:
            errors.append("Initial ETH deposit must be > 0")

        if self.config.initial_token_deposit <= 0:
            errors.append("Initial token deposit must be > 0")

        if self.config.swap_amount <= 0:
            errors.append("Swap amount must be > 0")

        if self.config.orders.eth_amount <= 0:
            errors.append("Order ETH amount must be > 0")

        if self.config.safety.max_transaction_retries < 1:
            errors.append("Max transaction retries must be >= 1")

        if self.config.safety.transaction_timeout < 30:
            errors.append("Transaction timeout must be >= 30 seconds")

        enabled_phases = [name for name, phase in self.config.phases.items() if phase.enabled]
        if not enabled_phases:
            errors.append("At least one phase must be enabled")

        return errors

    def save_config(self, path: str):
        import pickle
        with open(path, 'wb') as f:
            pickle.dump(self.config, f)

    def load_config(self, path: str):
        import pickle
        with open(path, 'rb') as f:
            self.config = pickle.load(f)

    def export_config_json(self, path: str):
        """Экспорт конфигурации в JSON"""
        config_dict = {
            'phases': {name: {'enabled': phase.enabled, 'sleep_after': phase.sleep_after}
                       for name, phase in self.config.phases.items()},
            'diagnostics': self.get_diagnostics_config(),
            'safety': self.get_safety_config(),
            'orders': {
                'limit_order_enabled': self.config.orders.limit_order_enabled,
                'stop_loss_enabled': self.config.orders.stop_loss_enabled,
                'modification_enabled': self.config.orders.modification_enabled,
                'eth_amount': self.config.orders.eth_amount
            },
            'general': {
                'log_level': self.config.log_level,
                'verbose': self.config.verbose,
                'ascii_art_enabled': self.config.ascii_art_enabled
            }
        }

        with open(path, 'w') as f:
            json.dump(config_dict, f, indent=2)

    def import_config_json(self, path: str):
        """Импорт конфигурации из JSON"""
        if Path(path).exists():
            with open(path, 'r') as f:
                config_data = json.load(f)

            if 'phases' in config_data:
                for phase_name, phase_config in config_data['phases'].items():
                    if phase_name in self.config.phases:
                        self.config.phases[phase_name].enabled = phase_config.get('enabled', True)
                        self.config.phases[phase_name].sleep_after = phase_config.get('sleep_after', 2.0)

            if 'diagnostics' in config_data:
                self.update_diagnostics_config(**config_data['diagnostics'])

            if 'safety' in config_data:
                self.update_safety_config(**config_data['safety'])

            if 'general' in config_data:
                self.update_config(**config_data['general'])