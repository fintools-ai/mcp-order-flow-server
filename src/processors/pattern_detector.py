"""Pattern detector for order flow analysis"""

import logging
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class PatternDetector:
    """Detects patterns in order flow data"""
    
    def detect_patterns(self, quotes: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect all patterns in the quote data"""
        patterns = []
        
        # Detect absorption
        absorption = self._detect_absorption(quotes)
        if absorption:
            patterns.append(absorption)
            
        # Detect stacking
        stacking = self._detect_stacking(quotes)
        if stacking:
            patterns.append(stacking)
            
        # Detect momentum shift
        momentum_shift = self._detect_momentum_shift(quotes, metrics)
        if momentum_shift:
            patterns.append(momentum_shift)
            
        # Detect iceberg orders
        iceberg = self._detect_iceberg(quotes)
        if iceberg:
            patterns.append(iceberg)
            
        return patterns
        
    def _detect_absorption(self, quotes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Detect absorption pattern (large orders absorbing flow)"""
        if len(quotes) < 10:
            return None
            
        # Look for stable price with high volume
        for i in range(10, len(quotes)):
            window = quotes[i-10:i]
            
            # Get price range
            bid_prices = [q.get('bid_price', 0) for q in window]
            ask_prices = [q.get('ask_price', 0) for q in window]
            
            bid_range = max(bid_prices) - min(bid_prices) if bid_prices else 0
            ask_range = max(ask_prices) - min(ask_prices) if ask_prices else 0
            
            # Check if price is stable (small range)
            if bid_range < 0.02 and ask_range < 0.02:
                # Check for large sizes
                bid_sizes = [q.get('bid_size', 0) for q in window]
                ask_sizes = [q.get('ask_size', 0) for q in window]
                
                avg_bid_size = sum(bid_sizes) / len(bid_sizes) if bid_sizes else 0
                avg_ask_size = sum(ask_sizes) / len(ask_sizes) if ask_sizes else 0
                
                # Detect bid absorption
                if avg_bid_size > 8000 and max(bid_sizes) > 15000:
                    return {
                        'type': 'absorption',
                        'side': 'bid',
                        'price_level': sum(bid_prices) / len(bid_prices),
                        'avg_size': avg_bid_size,
                        'max_size': max(bid_sizes),
                        'strength': 'strong' if avg_bid_size > 12000 else 'moderate',
                        'timestamp': time.time() * 1000,  # Convert to milliseconds
                        'description': f'Bid absorption at {bid_prices[-1]:.2f} with avg size {avg_bid_size}'
                    }
                    
                # Detect ask absorption
                if avg_ask_size > 8000 and max(ask_sizes) > 15000:
                    return {
                        'type': 'absorption',
                        'side': 'ask',
                        'price_level': sum(ask_prices) / len(ask_prices),
                        'avg_size': avg_ask_size,
                        'max_size': max(ask_sizes),
                        'strength': 'strong' if avg_ask_size > 12000 else 'moderate',
                        'timestamp': time.time() * 1000,  # Convert to milliseconds
                        'description': f'Ask absorption at {ask_prices[-1]:.2f} with avg size {avg_ask_size}'
                    }
                    
        return None
        
    def _detect_stacking(self, quotes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Detect stacking pattern (building walls)"""
        if len(quotes) < 5:
            return None
            
        # Look at recent quotes
        recent = quotes[-5:]
        
        # Check bid stacking
        bid_sizes = [q.get('bid_size', 0) for q in recent]
        if all(size > 5000 for size in bid_sizes) and bid_sizes[-1] > bid_sizes[0] * 1.5:
            return {
                'type': 'stacking',
                'side': 'bid',
                'levels': len([s for s in bid_sizes if s > 5000]),
                'total_size': sum(bid_sizes),
                'growth_rate': bid_sizes[-1] / bid_sizes[0] if bid_sizes[0] > 0 else 0,
                'timestamp': time.time() * 1000,  # Convert to milliseconds
                'description': f'Bid stacking detected with {sum(bid_sizes)} total size'
            }
            
        # Check ask stacking
        ask_sizes = [q.get('ask_size', 0) for q in recent]
        if all(size > 5000 for size in ask_sizes) and ask_sizes[-1] > ask_sizes[0] * 1.5:
            return {
                'type': 'stacking',
                'side': 'ask',
                'levels': len([s for s in ask_sizes if s > 5000]),
                'total_size': sum(ask_sizes),
                'growth_rate': ask_sizes[-1] / ask_sizes[0] if ask_sizes[0] > 0 else 0,
                'timestamp': time.time() * 1000,  # Convert to milliseconds
                'description': f'Ask stacking detected with {sum(ask_sizes)} total size'
            }
            
        return None
        
    def _detect_momentum_shift(self, quotes: List[Dict[str, Any]], metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect momentum shift pattern"""
        if not metrics:
            return None
            
        # Check lift/drop imbalance
        bid_lifts = metrics.get('bid_lift_count', 0)
        bid_drops = metrics.get('bid_drop_count', 0)
        
        total_moves = bid_lifts + bid_drops
        if total_moves < 10:
            return None
            
        # Strong bullish momentum
        if bid_lifts > bid_drops * 2:
            return {
                'type': 'momentum_shift',
                'direction': 'bullish',
                'strength': 'strong' if bid_lifts > bid_drops * 3 else 'moderate',
                'lift_ratio': bid_lifts / bid_drops if bid_drops > 0 else bid_lifts,
                'timestamp': time.time() * 1000,  # Convert to milliseconds
                'description': f'Bullish momentum: {bid_lifts} lifts vs {bid_drops} drops'
            }
            
        # Strong bearish momentum
        if bid_drops > bid_lifts * 2:
            return {
                'type': 'momentum_shift',
                'direction': 'bearish',
                'strength': 'strong' if bid_drops > bid_lifts * 3 else 'moderate',
                'drop_ratio': bid_drops / bid_lifts if bid_lifts > 0 else bid_drops,
                'timestamp': time.time() * 1000,  # Convert to milliseconds
                'description': f'Bearish momentum: {bid_drops} drops vs {bid_lifts} lifts'
            }
            
        return None
        
    def _detect_iceberg(self, quotes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Detect iceberg order pattern (hidden liquidity)"""
        if len(quotes) < 10:
            return None
            
        # Look for consistent refills at same price level
        price_counts = {}
        
        for quote in quotes[-20:]:  # Look at last 20 quotes
            bid_price = quote.get('bid_price', 0)
            bid_size = quote.get('bid_size', 0)
            
            if bid_size > 5000:  # Only track significant sizes
                if bid_price not in price_counts:
                    price_counts[bid_price] = {'count': 0, 'sizes': []}
                    
                price_counts[bid_price]['count'] += 1
                price_counts[bid_price]['sizes'].append(bid_size)
                
        # Check for iceberg pattern
        for price, data in price_counts.items():
            if data['count'] >= 5:  # Same price appeared 5+ times
                avg_size = sum(data['sizes']) / len(data['sizes'])
                if avg_size > 7000:
                    return {
                        'type': 'iceberg',
                        'side': 'bid',
                        'price': price,
                        'refill_count': data['count'],
                        'avg_size': avg_size,
                        'total_volume': sum(data['sizes']),
                        'timestamp': time.time() * 1000,  # Convert to milliseconds
                        'description': f'Iceberg order detected at {price:.2f} with {data["count"]} refills'
                    }
                    
        return None
