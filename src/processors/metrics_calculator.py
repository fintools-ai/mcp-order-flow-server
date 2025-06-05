"""Metrics calculator for order flow analysis"""

import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculates various metrics from quote data"""
    
    def calculate_momentum_metrics(self, quotes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate momentum-related metrics"""
        if not quotes:
            return {}
            
        metrics = {}
        
        # Get first and last quotes
        first_quote = quotes[0]
        last_quote = quotes[-1]
        
        # Price movements
        metrics['bid_price_movement'] = last_quote.get('bid_price', 0) - first_quote.get('bid_price', 0)
        metrics['ask_price_movement'] = last_quote.get('ask_price', 0) - first_quote.get('ask_price', 0)
        
        # Count lifts and drops
        bid_lifts = 0
        bid_drops = 0
        ask_lifts = 0
        ask_drops = 0
        
        for i in range(1, len(quotes)):
            prev = quotes[i-1]
            curr = quotes[i]
            
            # Bid movements
            if curr.get('bid_price', 0) > prev.get('bid_price', 0):
                bid_lifts += 1
            elif curr.get('bid_price', 0) < prev.get('bid_price', 0):
                bid_drops += 1
                
            # Ask movements
            if curr.get('ask_price', 0) > prev.get('ask_price', 0):
                ask_lifts += 1
            elif curr.get('ask_price', 0) < prev.get('ask_price', 0):
                ask_drops += 1
                
        metrics['bid_lift_count'] = bid_lifts
        metrics['bid_drop_count'] = bid_drops
        metrics['ask_lift_count'] = ask_lifts
        metrics['ask_drop_count'] = ask_drops
        
        # Net size changes
        metrics['net_bid_size_change'] = last_quote.get('bid_size', 0) - first_quote.get('bid_size', 0)
        metrics['net_ask_size_change'] = last_quote.get('ask_size', 0) - first_quote.get('ask_size', 0)
        
        return metrics
        
    def calculate_size_dynamics(self, quotes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate size-related dynamics"""
        if not quotes:
            return {}
            
        metrics = {}
        
        # Large order tracking
        large_bids = 0
        large_asks = 0
        bid_sizes = []
        ask_sizes = []
        
        for quote in quotes:
            bid_size = quote.get('bid_size', 0)
            ask_size = quote.get('ask_size', 0)
            
            bid_sizes.append(bid_size)
            ask_sizes.append(ask_size)
            
            if bid_size > 10000:
                large_bids += 1
            if ask_size > 10000:
                large_asks += 1
                
        metrics['large_bids_appeared'] = large_bids
        metrics['large_asks_appeared'] = large_asks
        
        # Average sizes
        metrics['avg_bid_size'] = int(sum(bid_sizes) / len(bid_sizes)) if bid_sizes else 0
        metrics['avg_ask_size'] = int(sum(ask_sizes) / len(ask_sizes)) if ask_sizes else 0
        
        # Size acceleration (compare first half vs second half)
        if len(quotes) > 10:
            mid = len(quotes) // 2
            
            first_half_bid_avg = sum(bid_sizes[:mid]) / mid
            second_half_bid_avg = sum(bid_sizes[mid:]) / (len(bid_sizes) - mid)
            
            first_half_ask_avg = sum(ask_sizes[:mid]) / mid
            second_half_ask_avg = sum(ask_sizes[mid:]) / (len(ask_sizes) - mid)
            
            # Determine acceleration
            bid_ratio = second_half_bid_avg / first_half_bid_avg if first_half_bid_avg > 0 else 1
            ask_ratio = second_half_ask_avg / first_half_ask_avg if first_half_ask_avg > 0 else 1
            
            if bid_ratio > 1.2:
                metrics['bid_size_acceleration'] = 'INCREASING'
            elif bid_ratio < 0.8:
                metrics['bid_size_acceleration'] = 'DECREASING'
            else:
                metrics['bid_size_acceleration'] = 'STABLE'
                
            if ask_ratio > 1.2:
                metrics['ask_size_acceleration'] = 'INCREASING'
            elif ask_ratio < 0.8:
                metrics['ask_size_acceleration'] = 'DECREASING'
            else:
                metrics['ask_size_acceleration'] = 'STABLE'
        else:
            metrics['bid_size_acceleration'] = 'STABLE'
            metrics['ask_size_acceleration'] = 'STABLE'
            
        return metrics
        
    def detect_sweep(self, quotes: List[Dict[str, Any]], threshold: int = 15000) -> Optional[Dict[str, Any]]:
        """Detect sweep activity (sudden large size changes)"""
        if len(quotes) < 2:
            return None
            
        # Look for sudden size changes
        for i in range(1, len(quotes)):
            prev = quotes[i-1]
            curr = quotes[i]
            
            # Check bid sweep
            bid_change = abs(curr.get('bid_size', 0) - prev.get('bid_size', 0))
            if bid_change > threshold:
                return {
                    'type': 'sweep',
                    'side': 'bid',
                    'price': curr.get('bid_price', 0),
                    'size': bid_change,
                    'direction': 'lift' if curr.get('bid_price', 0) > prev.get('bid_price', 0) else 'hit',
                    'timestamp': curr.get('timestamp', 0)
                }
                
            # Check ask sweep
            ask_change = abs(curr.get('ask_size', 0) - prev.get('ask_size', 0))
            if ask_change > threshold:
                return {
                    'type': 'sweep',
                    'side': 'ask',
                    'price': curr.get('ask_price', 0),
                    'size': ask_change,
                    'direction': 'lift' if curr.get('ask_price', 0) > prev.get('ask_price', 0) else 'hit',
                    'timestamp': curr.get('timestamp', 0)
                }
                
        return None
        
    def calculate_spread_metrics(self, quotes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate spread-related metrics"""
        if not quotes:
            return {}
            
        spreads = []
        
        for quote in quotes:
            bid = quote.get('bid_price', 0)
            ask = quote.get('ask_price', 0)
            
            if bid > 0 and ask > 0:
                spread = ask - bid
                spreads.append(spread)
                
        if not spreads:
            return {}
            
        metrics = {
            'avg_spread': sum(spreads) / len(spreads),
            'min_spread': min(spreads),
            'max_spread': max(spreads),
            'spread_volatility': max(spreads) - min(spreads)
        }
        
        # Check if spread is tightening
        if len(spreads) > 5:
            recent_avg = sum(spreads[-5:]) / 5
            older_avg = sum(spreads[:-5]) / (len(spreads) - 5)
            
            if recent_avg < older_avg * 0.8:
                metrics['spread_trend'] = 'TIGHTENING'
            elif recent_avg > older_avg * 1.2:
                metrics['spread_trend'] = 'WIDENING'
            else:
                metrics['spread_trend'] = 'STABLE'
        else:
            metrics['spread_trend'] = 'STABLE'
            
        return metrics
