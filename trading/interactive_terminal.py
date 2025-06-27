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
import sys
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from web3 import Web3
from eth_account import Account


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class InteractiveDEXTerminal:
    def __init__(self):
        self.w3 = None
        self.user_account = None
        self.contracts = {}
        self.token_addresses = {}
        self.token_symbols = []
        self.config = None
        self.connected = False

    def print_header(self, text: str):
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.END}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.END}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.END}\n")

    def print_success(self, text: str):
        print(f"{Colors.GREEN}✅ {text}{Colors.END}")

    def print_error(self, text: str):
        print(f"{Colors.RED}❌ {text}{Colors.END}")

    def print_warning(self, text: str):
        print(f"{Colors.YELLOW}⚠️ {text}{Colors.END}")

    def print_info(self, text: str):
        print(f"{Colors.CYAN}ℹ️ {text}{Colors.END}")

    def load_config(self):
        config_paths = [
            "../config/anvil_final-config.json",
            "../config/anvil_upgradeable-config.json",
            "../config/deployment-config.json",
            "../config/deployed-config.json",
            "./config/deployed-config.json"
        ]

        config_loaded = False
        for config_path in config_paths:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
                self.print_success(f"Config loaded from {config_path}")
                config_loaded = True
                break

        if not config_loaded:
            self.print_error("Config file not found. Run deployment first.")
            self.print_info(f"Expected one of: {config_paths}")
            return False

        self.print_info(f"Loaded config with contracts:")
        contracts = self.config.get('contracts', {})
        if 'proxies' in self.config:
            contracts.update(self.config['proxies'])

        for name, addr in contracts.items():
            self.print_info(f" {name}: {addr}")

        rpc_url = "http://localhost:8545"
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not self.w3.is_connected():
            self.print_error("Cannot connect to blockchain")
            self.print_info("Make sure Hardhat node is running: npx hardhat node")
            return False

        try:
            chain_id = self.w3.eth.chain_id
            block_number = self.w3.eth.block_number
            self.print_success(f"Connected to chain ID: {chain_id}, block: {block_number}")
        except Exception as e:
            self.print_error(f"Network info failed: {str(e)}")

        self.token_addresses = {
            'ETH': '0x0000000000000000000000000000000000000000'
        }

        for symbol, token_config in self.config.get('tokens', {}).items():
            self.token_addresses[symbol] = token_config.get('address', '')

        self.print_info(f"Token addresses:")
        for symbol, addr in self.token_addresses.items():
            if symbol != 'ETH':
                self.print_info(f" {symbol}: {addr}")

        self.token_symbols = list(self.token_addresses.keys())

        try:
            self.load_contracts()
            self.connected = True
            self.print_success("All contracts loaded successfully")
            return True
        except Exception as e:
            self.print_error(f"Failed to load contracts: {str(e)}")
            return False

    def load_contracts(self):
        base_path = "../artifacts/contracts/"
        contracts = self.config.get('contracts', {})
        if 'proxies' in self.config:
            contracts.update(self.config['proxies'])

        router_address = contracts.get('Router', contracts.get('RouterProxy', ''))
        if router_address:
            try:
                with open(f"{base_path}upgradeable/RouterUpgradeable.sol/RouterUpgradeable.json", 'r') as f:
                    router_data = json.load(f)
                router_abi = router_data['abi']
                self.contracts['router'] = self.w3.eth.contract(
                    address=router_address,
                    abi=router_abi
                )
            except Exception as e:
                self.print_warning(f"Failed to load router contract: {e}")

    def get_oracle_prices(self) -> Dict[str, float]:
        prices = {}
        try:
            for symbol, addr in self.token_addresses.items():
                try:
                    raw_price = self.contracts['router'].functions.getPrice(addr).call()
                    prices[symbol] = raw_price / (10 ** 18)
                except Exception as e:
                    fallback_prices = {
                        'ETH': 2500.0, 'CAPY': 1.0, 'AXOL': 1.0,
                        'QUOK': 45000.0, 'PANG': 15.0, 'NARW': 25.0
                    }
                    prices[symbol] = fallback_prices.get(symbol, 1.0)
                    self.print_warning(f"Using fallback {symbol} price: ${prices[symbol]}")
        except Exception as e:
            self.print_error(f"Failed to get prices: {e}")
        return prices

    def add_private_key(self):
        self.print_header("ADD PRIVATE KEY")

        print("Enter your private key (without 0x prefix):")
        print("Or press Enter to use predefined test accounts:")
        print("1 - User1: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
        print("2 - User2: 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC")

        choice = input("Your choice: ").strip()

        if choice == "1":
            private_key = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
        elif choice == "2":
            private_key = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
        elif choice == "":
            self.print_warning("No private key provided")
            return False
        else:
            if not choice.startswith('0x'):
                private_key = '0x' + choice
            else:
                private_key = choice

        try:
            self.user_account = Account.from_key(private_key)
            self.print_success(f"Account loaded: {self.user_account.address}")
            return True
        except Exception as e:
            self.print_error(f"Invalid private key: {str(e)}")
            return False

    def get_user_balances(self) -> Dict[str, Tuple[float, float]]:
        if not self.user_account:
            return {}

        balances = {}
        for symbol in self.token_symbols:
            try:
                if symbol == 'ETH':
                    wallet_balance_wei = self.w3.eth.get_balance(self.user_account.address)
                    wallet_balance = wallet_balance_wei / 10 ** 18

                    try:
                        pool_balance_wei = self.contracts['router'].functions.getBalance(
                            self.user_account.address,
                            '0x0000000000000000000000000000000000000000'
                        ).call()
                        pool_balance = pool_balance_wei / 10 ** 18
                    except:
                        pool_balance = 0

                else:
                    wallet_balance = 0
                    token_addr = self.token_addresses[symbol]

                    try:
                        pool_balance_wei = self.contracts['router'].functions.getBalance(
                            self.user_account.address,
                            token_addr
                        ).call()

                        token_config = self.config.get('tokens', {}).get(symbol, {})
                        decimals = token_config.get('decimals', 18)
                        pool_balance = pool_balance_wei / (10 ** decimals)
                    except:
                        pool_balance = 0

                balances[symbol] = (wallet_balance, pool_balance)

            except Exception as e:
                balances[symbol] = (0.0, 0.0)

        return balances

    def simple_swap(self):
        self.print_header("SIMPLE SWAP")

        balances = self.get_user_balances()
        prices = self.get_oracle_prices()

        print("Available tokens for swap:")
        for i, symbol in enumerate(self.token_symbols, 1):
            pool_balance = balances[symbol][1]
            price = prices.get(symbol, 0)
            print(f"{i}. {symbol} (Pool: {pool_balance:.6f}, Price: ${price:.2f})")

        try:
            from_idx = int(input("Select token to sell (number): ")) - 1
            to_idx = int(input("Select token to buy (number): ")) - 1

            token_from = self.token_symbols[from_idx]
            token_to = self.token_symbols[to_idx]

            if token_from == token_to:
                self.print_error("Cannot swap same token")
                return

            available = balances[token_from][1]
            if available <= 0:
                self.print_error(f"No {token_from} in pool")
                return

            amount = float(input(f"Amount of {token_from} to swap: "))
            if amount <= 0 or amount > available:
                self.print_error("Invalid amount")
                return

            token_from_addr = self.token_addresses[token_from]
            token_to_addr = self.token_addresses[token_to]

            if token_from == 'ETH':
                from_decimals = 18
            else:
                from_decimals = self.config.get('tokens', {}).get(token_from, {}).get('decimals', 18)

            amount_in = int(amount * (10 ** from_decimals))
            min_amount_out = 1

            value = amount_in if token_from == 'ETH' else 0

            tx_hash = self.contracts['router'].functions.swapTokens(
                token_from_addr, token_to_addr, amount_in, min_amount_out
            ).transact({
                'from': self.user_account.address,
                'value': value,
                'gas': 300000
            })

            self.print_success(f"Swap completed: {amount} {token_from} → {token_to}")
            self.print_info(f"Transaction: {tx_hash.hex()}")

        except Exception as e:
            self.print_error(f"Swap failed: {str(e)}")

    def trading_operations(self):
        if not self.user_account:
            self.print_error("Please add your private key first")
            return

        self.print_header("TRADING OPERATIONS")
        print("1. Simple Swap")
        choice = input("Select operation: ").strip()

        if choice == "1":
            self.simple_swap()
        else:
            self.print_error("Invalid choice")

    def run_terminal(self):
        if not self.load_config():
            return

        while True:
            self.print_header("DEX TRADING TERMINAL")
            print("1. Get Oracle Prices")
            print("2. Add Private Key")
            print("3. Get Your Balances")
            print("4. Trading Operations")
            print("5. Exit")

            choice = input("\nSelect option: ").strip()

            try:
                if choice == "1":
                    prices = self.get_oracle_prices()
                    print("\nCurrent Oracle Prices:")
                    for symbol, price in prices.items():
                        print(f" {symbol}: ${price:.2f}")

                elif choice == "2":
                    self.add_private_key()

                elif choice == "3":
                    if not self.user_account:
                        self.print_error("Please add your private key first")
                    else:
                        balances = self.get_user_balances()
                        print("\nYour Balances:")
                        for symbol, (wallet, pool) in balances.items():
                            print(f" {symbol}:")
                            print(f"  Wallet: {wallet:.6f}")
                            print(f"  Pool: {pool:.6f}")

                elif choice == "4":
                    self.trading_operations()

                elif choice == "5":
                    print("Goodbye!")
                    break

                else:
                    self.print_error("Invalid choice")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                self.print_error(f"Error: {str(e)}")

            input("\nPress Enter to continue...")


if __name__ == "__main__":
    terminal = InteractiveDEXTerminal()
    terminal.run_terminal()