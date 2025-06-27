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
import argparse
import sys
from pathlib import Path

from trading_demo import TradingDemo, QuickDemo, MinimalDemo, OrdersOnlyDemo, SecurityDemo
from demo_config import DemoConfigManager


def parse_args():
    parser = argparse.ArgumentParser(description='DEX Trading Demo')

    parser.add_argument(
        '--config',
        type=str,
        default='../config/anvil_final-config.json',
        help='Path to configuration file'
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['full', 'quick', 'minimal', 'orders', 'security', 'debug', 'production'],
        default='full',
        help='Demo mode to run'
    )

    parser.add_argument(
        '--network',
        type=str,
        choices=['localhost', 'testnet', 'mainnet'],
        default='localhost',
        help='Network type for configuration optimization'
    )

    parser.add_argument(
        '--skip-setup',
        action='store_true',
        help='Skip user funds setup phase'
    )
    parser.add_argument(
        '--skip-trading',
        action='store_true',
        help='Skip basic trading phase'
    )
    parser.add_argument(
        '--skip-orders',
        action='store_true',
        help='Skip advanced orders phase'
    )
    parser.add_argument(
        '--skip-management',
        action='store_true',
        help='Skip order management phase'
    )
    parser.add_argument(
        '--skip-emergency',
        action='store_true',
        help='Skip emergency features phase'
    )
    parser.add_argument(
        '--skip-self-exec',
        action='store_true',
        help='Skip self-execution phase'
    )

    parser.add_argument(
        '--enable-diagnostics',
        action='store_true',
        help='Enable comprehensive diagnostics mode'
    )
    parser.add_argument(
        '--enable-safety',
        action='store_true',
        help='Enable maximum safety checks'
    )
    parser.add_argument(
        '--enable-performance',
        action='store_true',
        help='Enable performance monitoring'
    )

    parser.add_argument(
        '--no-ascii',
        action='store_true',
        help='Disable ASCII art output'
    )
    parser.add_argument(
        '--no-detailed-balances',
        action='store_true',
        help='Disable detailed balance display'
    )
    parser.add_argument(
        '--no-price-debug',
        action='store_true',
        help='Disable price debugging output'
    )
    parser.add_argument(
        '--no-transaction-details',
        action='store_true',
        help='Disable transaction details display'
    )
    parser.add_argument(
        '--no-gas-tracking',
        action='store_true',
        help='Disable gas usage tracking'
    )
    parser.add_argument(
        '--no-system-diagnostics',
        action='store_true',
        help='Disable system diagnostics display'
    )

    parser.add_argument(
        '--eth-deposit',
        type=float,
        default=10.0,
        help='Initial ETH deposit amount'
    )
    parser.add_argument(
        '--token-deposit',
        type=float,
        default=1000.0,
        help='Initial token deposit amount'
    )
    parser.add_argument(
        '--swap-amount',
        type=float,
        default=0.5,
        help='Amount for basic swap'
    )
    parser.add_argument(
        '--order-amount',
        type=float,
        default=0.1,
        help='Amount for order creation'
    )

    parser.add_argument(
        '--disable-limit-orders',
        action='store_true',
        help='Disable limit order creation'
    )
    parser.add_argument(
        '--disable-stop-loss',
        action='store_true',
        help='Disable stop-loss order creation'
    )
    parser.add_argument(
        '--disable-modification',
        action='store_true',
        help='Disable order modification demo'
    )
    parser.add_argument(
        '--disable-cancellation',
        action='store_true',
        help='Disable order cancellation demo'
    )

    parser.add_argument(
        '--no-emergency-test',
        action='store_true',
        help='Skip emergency pause testing'
    )

    parser.add_argument(
        '--no-balance-validation',
        action='store_true',
        help='Disable balance validation before operations'
    )
    parser.add_argument(
        '--no-contract-validation',
        action='store_true',
        help='Disable contract state validation'
    )
    parser.add_argument(
        '--no-gas-validation',
        action='store_true',
        help='Disable gas price validation'
    )
    parser.add_argument(
        '--no-liquidity-check',
        action='store_true',
        help='Disable liquidity validation'
    )

    parser.add_argument(
        '--transaction-timeout',
        type=int,
        default=120,
        help='Transaction timeout in seconds'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum transaction retry attempts'
    )
    parser.add_argument(
        '--safety-delay',
        type=float,
        default=1.0,
        help='Delay between operations for safety'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output (WARNING level)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output (DEBUG level)'
    )

    parser.add_argument(
        '--save-config',
        type=str,
        help='Save current configuration to file'
    )
    parser.add_argument(
        '--load-config',
        type=str,
        help='Load configuration from file'
    )
    parser.add_argument(
        '--export-config',
        type=str,
        help='Export configuration to JSON file'
    )
    parser.add_argument(
        '--import-config',
        type=str,
        help='Import configuration from JSON file'
    )

    parser.add_argument(
        '--check-orders',
        action='store_true',
        help='Enable order status checking before operations'
    )
    parser.add_argument(
        '--track-costs',
        action='store_true',
        help='Enable transaction cost tracking'
    )
    parser.add_argument(
        '--validate-before-run',
        action='store_true',
        help='Validate configuration before running demo'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration and show planned actions without execution'
    )

    return parser.parse_args()


async def main():
    args = parse_args()

    if not Path(args.config).exists():
        print(f"❌ Config file not found: {args.config}")
        print("Run deployment first: npm run full-deploy")
        sys.exit(1)

    try:
        if args.mode == 'quick':
            demo = QuickDemo(args.config)
        elif args.mode == 'minimal':
            demo = MinimalDemo(args.config)
        elif args.mode == 'orders':
            demo = OrdersOnlyDemo(args.config)
        elif args.mode == 'security':
            demo = SecurityDemo(args.config)
        else:
            demo = TradingDemo(args.config)

        if args.import_config:
            demo.demo_config.import_config_json(args.import_config)
            print(f"✅ Imported configuration from {args.import_config}")

        if args.load_config:
            demo.demo_config.load_config(args.load_config)
            print(f"✅ Loaded configuration from {args.load_config}")

        demo.demo_config.configure_for_network(args.network)

        config_updates = {}

        if args.quiet:
            config_updates['log_level'] = 'WARNING'
        elif args.verbose:
            config_updates['log_level'] = 'DEBUG'
        else:
            config_updates['log_level'] = args.log_level

        if args.no_ascii:
            config_updates['ascii_art_enabled'] = False
        if args.no_detailed_balances:
            config_updates['show_detailed_balances'] = False
        if args.no_price_debug:
            config_updates['show_price_debugging'] = False
        if args.no_transaction_details:
            config_updates['show_transaction_details'] = False
        if args.no_gas_tracking:
            config_updates['show_gas_usage'] = False
        if args.no_system_diagnostics:
            config_updates['show_system_diagnostics'] = False

        config_updates['initial_eth_deposit'] = args.eth_deposit
        config_updates['initial_token_deposit'] = args.token_deposit
        config_updates['swap_amount'] = args.swap_amount

        if args.no_emergency_test:
            config_updates['test_emergency_pause'] = False

        if args.check_orders:
            config_updates['check_order_status'] = True
        if args.track_costs:
            config_updates['track_transaction_costs'] = True

        if config_updates:
            demo.demo_config.update_config(**config_updates)

        if args.enable_diagnostics:
            demo.demo_config.enable_diagnostics_mode()
        if args.enable_safety:
            demo.demo_config.enable_safety_mode()
        if args.enable_performance:
            demo.demo_config.enable_performance_mode()

        diagnostics_updates = {}
        if args.no_gas_tracking:
            diagnostics_updates['gas_tracking'] = False
        if diagnostics_updates:
            demo.demo_config.update_diagnostics_config(**diagnostics_updates)

        safety_updates = {}
        if args.no_balance_validation:
            safety_updates['balance_validation'] = False
        if args.no_contract_validation:
            safety_updates['contract_state_validation'] = False
        if args.no_gas_validation:
            safety_updates['gas_price_validation'] = False
        if args.no_liquidity_check:
            safety_updates['liquidity_check'] = False

        safety_updates['transaction_timeout'] = args.transaction_timeout
        safety_updates['max_transaction_retries'] = args.max_retries
        safety_updates['safety_delay_between_operations'] = args.safety_delay

        if safety_updates:
            demo.demo_config.update_safety_config(**safety_updates)

        if args.skip_setup:
            demo.demo_config.disable_phase('setup')
        if args.skip_trading:
            demo.demo_config.disable_phase('basic_trading')
        if args.skip_orders:
            demo.demo_config.disable_phase('advanced_orders')
        if args.skip_management:
            demo.demo_config.disable_phase('order_management')
        if args.skip_emergency:
            demo.demo_config.disable_phase('emergency_features')
        if args.skip_self_exec:
            demo.demo_config.disable_phase('self_execution')

        order_updates = {}
        if args.disable_limit_orders:
            order_updates['limit_order_enabled'] = False
        if args.disable_stop_loss:
            order_updates['stop_loss_enabled'] = False
        if args.disable_modification:
            order_updates['modification_enabled'] = False
        if args.disable_cancellation:
            order_updates['cancellation_enabled'] = False

        order_updates['eth_amount'] = args.order_amount

        for key, value in order_updates.items():
            setattr(demo.demo_config.config.orders, key, value)

        if args.validate_before_run:
            errors = demo.demo_config.validate_demo_config()
            if errors:
                print("❌ Configuration validation failed:")
                for error in errors:
                    print(f"   - {error}")
                sys.exit(1)
            print("✅ Configuration validation passed")

        if args.save_config:
            demo.demo_config.save_config(args.save_config)
            print(f"✅ Saved configuration to {args.save_config}")

        if args.export_config:
            demo.demo_config.export_config_json(args.export_config)
            print(f"✅ Exported configuration to {args.export_config}")

        print("=== DEX Trading Demo ===")
        print(f"Mode: {args.mode}")
        print(f"Network: {args.network}")
        print(f"Config: {args.config}")
        print(f"Chain ID: {demo.w3.eth.chain_id}")

        enabled_phases = [name for name, phase in demo.demo_config.config.phases.items() if phase.enabled]
        print(f"Enabled phases: {', '.join(enabled_phases)}")

        diagnostics_config = demo.demo_config.get_diagnostics_config()
        safety_config = demo.demo_config.get_safety_config()

        print(f"Diagnostics: {'ENABLED' if diagnostics_config['enabled'] else 'DISABLED'}")
        print(f"Safety checks: {'ENABLED' if safety_config['pre_transaction_checks'] else 'DISABLED'}")
        print(f"Transaction timeout: {safety_config['timeout']}s")
        print(f"Max retries: {safety_config['max_retries']}")

        if args.check_orders:
            print("🔍 Order status checking: ENABLED")
        if args.track_costs:
            print("💰 Transaction cost tracking: ENABLED")
        if args.enable_diagnostics:
            print("🔧 Comprehensive diagnostics: ENABLED")
        if args.enable_safety:
            print("🛡️ Maximum safety mode: ENABLED")
        if args.enable_performance:
            print("📊 Performance monitoring: ENABLED")

        if args.dry_run:
            print("\n🧪 DRY RUN MODE - No transactions will be executed")
            print("Configuration validated successfully")
            print("Demo would execute the following phases:")
            for name, phase in demo.demo_config.config.phases.items():
                if phase.enabled:
                    print(f"  ✅ {phase.name}")
                else:
                    print(f"  ⏭️ {phase.name} (skipped)")
            return

        print("\nPress Ctrl+C to stop\n")

        await demo.run_demo()

    except KeyboardInterrupt:
        print("\n🛑 Demo stopped by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        if args.verbose or args.log_level == 'DEBUG':
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())