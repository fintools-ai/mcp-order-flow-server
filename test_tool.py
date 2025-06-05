#!/usr/bin/env python3
"""Test script for Order Flow MCP Server"""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tools.order_flow_tool import analyze_order_flow


async def test_order_flow():
    """Test the order flow analysis tool"""
    print("Testing Order Flow MCP Tool")
    print("=" * 50)
    
    # Test tickers
    test_cases = [
        ("SPY", "5mins", True),
        ("QQQ", "1min", True),
        ("IWM", "30s", False),
        ("INVALID", "5mins", True),  # Test error case
    ]
    
    for ticker, history, include_patterns in test_cases:
        print(f"\nTesting {ticker} with {history} history (patterns: {include_patterns})")
        print("-" * 40)
        
        try:
            result = await analyze_order_flow(ticker, history, include_patterns)
            
            # Pretty print first 1000 chars
            if len(result) > 1000:
                print(result[:1000] + "\n... (truncated)")
            else:
                print(result)
                
        except Exception as e:
            print(f"Error: {e}")
            
    print("\n" + "=" * 50)
    print("Test complete!")


async def test_direct_redis():
    """Test direct Redis connection"""
    print("\nTesting Redis Connection")
    print("=" * 50)
    
    try:
        from storage.redis_client import OrderFlowRedisClient
        
        redis_client = OrderFlowRedisClient()
        
        # Test ping
        if redis_client.ping():
            print("✓ Redis connection successful")
        else:
            print("✗ Redis connection failed")
            return
            
        # List available tickers
        keys = []
        cursor = 0
        
        while True:
            cursor, batch = redis_client.redis_client.scan(
                cursor, 
                match="orderflow:quotes:*",
                count=100
            )
            keys.extend(batch)
            
            if cursor == 0:
                break
                
        if keys:
            print(f"\n✓ Found {len(keys)} tickers with data:")
            for key in sorted(keys)[:10]:
                ticker = key.split(':')[2]
                latest = redis_client.get_latest_quote(ticker)
                if latest:
                    print(f"  - {ticker}: bid={latest.get('bid_price', 0):.2f} ask={latest.get('ask_price', 0):.2f}")
                else:
                    print(f"  - {ticker}: (no latest quote)")
                    
            if len(keys) > 10:
                print(f"  ... and {len(keys) - 10} more")
        else:
            print("\n✗ No order flow data found in Redis")
            print("  Make sure the data broker is running")
            
    except Exception as e:
        print(f"✗ Redis test failed: {e}")


def main():
    """Main test function"""
    print("MCP Order Flow Server - Test Suite")
    print("=" * 50)
    
    # Run tests
    asyncio.run(test_direct_redis())
    print("\n")
    asyncio.run(test_order_flow())


if __name__ == "__main__":
    main()
