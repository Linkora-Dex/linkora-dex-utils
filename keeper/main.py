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

from keeper_service import KeeperService

def parse_args():
    parser = argparse.ArgumentParser(description='DEX Keeper Service')
    parser.add_argument(
        '--config',
        type=str,
        default='../config/anvil_final-config.json',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--private-key',
        type=str,
        help='Private key for keeper account (overrides config)'
    )
    parser.add_argument(
        '--rpc-url',
        type=str,
        help='RPC URL (overrides config)'
    )
    parser.add_argument(
        '--order-interval',
        type=int,
        help='Order check interval in seconds (overrides config)'
    )
    parser.add_argument(
        '--position-interval',
        type=int,
        help='Position check interval in seconds (overrides config)'
    )
    parser.add_argument(
        '--liquidation-threshold',
        type=int,
        help='Liquidation threshold percentage (overrides config)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (overrides config)'
    )
    parser.add_argument(
        '--disable-orders',
        action='store_true',
        help='Disable order execution'
    )
    parser.add_argument(
        '--disable-liquidation',
        action='store_true',
        help='Disable position liquidation'
    )
    parser.add_argument(
        '--disable-diagnostics',
        action='store_true',
        help='Disable diagnostic output'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show keeper status and exit'
    )
    parser.add_argument(
        '--orders',
        action='store_true',
        help='Show all orders and exit'
    )
    parser.add_argument(
        '--positions',
        action='store_true',
        help='Show all positions and exit'
    )
    parser.add_argument(
        '--execute-order',
        type=int,
        help='Manually execute specific order ID'
    )
    parser.add_argument(
        '--liquidate-position',
        type=int,
        help='Manually liquidate specific position ID'
    )

    return parser.parse_args()

async def main():
    args = parse_args()

    if not Path(args.config).exists():
        print(f"❌ Config file not found: {args.config}")
        print("Run deployment first: npm run full-deploy")
        sys.exit(1)

    try:
        keeper = KeeperService(args.config)

        config_overrides = {}
        if args.private_key:
            config_overrides['private_key'] = args.private_key
        if args.rpc_url:
            config_overrides['rpc_url'] = args.rpc_url
        if args.order_interval:
            config_overrides['order_check_interval'] = args.order_interval
        if args.position_interval:
            config_overrides['position_check_interval'] = args.position_interval
        if args.liquidation_threshold:
            config_overrides['liquidation_threshold'] = args.liquidation_threshold
        if args.log_level:
            config_overrides['log_level'] = args.log_level
        if args.disable_orders:
            config_overrides['enable_order_execution'] = False
        if args.disable_liquidation:
            config_overrides['enable_position_liquidation'] = False
        if args.disable_diagnostics:
            config_overrides['enable_diagnostics'] = False

        if config_overrides:
            keeper.update_config(**config_overrides)

        if args.status:
            status = keeper.get_status()
            print("\n🤖 KEEPER STATUS:")
            print(f"Running: {status['running']}")
            print(f"Keeper Address: {status['keeper_address']}")
            print(f"Network ID: {status['network_id']}")
            print(f"Order Check Counter: {status['order_check_counter']}")
            print(f"Position Check Counter: {status['position_check_counter']}")
            print("\n⚙️ CONFIG:")
            for key, value in status['config'].items():
                print(f"{key}: {value}")
            return

        if args.orders:
            orders = keeper.get_all_orders()
            print(f"\n📋 ALL ORDERS ({len(orders)} total):")
            for order in orders:
                status_icon = "✅" if order['executed'] else ("🎯" if order['should_execute'] else "⏳")
                print(f"{status_icon} Order {order['id']}: {order['order_type']} by {order['user'][:10]}...")
                print(f"   Token: {order['token_in'][:10]}... → {order['token_out'][:10]}...")
                print(f"   Amount: {order['amount_in']}, Target: {order['target_price']}")
            return

        if args.positions:
            positions = keeper.get_all_positions()
            print(f"\n📊 ALL POSITIONS ({len(positions)} total):")
            for position in positions:
                status_icon = "⚠️" if position['liquidation_candidate'] else ("🟢" if position['is_open'] else "🔴")
                print(f"{status_icon} Position {position['id']}: {position['position_type']} by {position['user'][:10]}...")
                print(f"   Token: {position['token'][:10]}..., Leverage: {position['leverage']}x")
                print(f"   PnL: {position['pnl_ratio']:.2f}%, Open: {position['is_open']}")
            return

        if args.execute_order:
            print(f"🔧 Manually executing order {args.execute_order}...")
            success = await keeper.manual_execute_order(args.execute_order)
            if success:
                print(f"✅ Order {args.execute_order} executed successfully")
            else:
                print(f"❌ Failed to execute order {args.execute_order}")
            return

        if args.liquidate_position:
            position_info = keeper.get_position_info(args.liquidate_position)
            if not position_info:
                print(f"❌ Position {args.liquidate_position} not found")
                return

            print(f"🔧 Manually liquidating position {args.liquidate_position}...")
            success = await keeper.manual_liquidate_position(args.liquidate_position)
            if success:
                print(f"⚡ Position {args.liquidate_position} liquidated successfully")
            else:
                print(f"❌ Failed to liquidate position {args.liquidate_position}")
            return

        print("=== DEX Keeper Service ===")
        print(f"Config: {args.config}")
        print(f"Network: {keeper.w3.eth.chain_id}")
        print(f"Keeper: {keeper.account.address}")

        if config_overrides:
            print(f"Overrides: {config_overrides}")

        print("\nPress Ctrl+C to stop\n")

        await keeper.start()

    except KeyboardInterrupt:
        print("\n🛑 Keeper stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())