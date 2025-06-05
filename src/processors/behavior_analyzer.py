"""Behavior analyzer for order flow data"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class BehaviorAnalyzer:
    """Analyzes market behaviors from order flow data"""
    
    def analyze_behaviors(self, quotes: List[Dict[str, Any]], metrics: Dict[str, Any]) -> Dict[str, str]:
        """Analyze behaviors and return YES/NO flags"""
        behaviors = {}
        
        # Analyze bid stacking
        behaviors['bid_stacking'] = self._check_bid_stacking(quotes)
        
        # Analyze ask pulling
        behaviors['ask_pulling'] = self._check_ask_pulling(quotes)
        
        # Analyze spread tightening
        behaviors['spread_tightening'] = self._check_spread_tightening(quotes)
        
        # Analyze momentum building
        behaviors['momentum_building'] = self._check_momentum_building(quotes, metrics)
        
        # Analyze aggressive buying/selling
        behaviors['aggressive_buying'] = self._check_aggressive_buying(quotes, metrics)
        behaviors['aggressive_selling'] = self._check_aggressive_selling(quotes, metrics)
        
        return behaviors
        
    def _check_bid_stacking(self, quotes: List[Dict[str, Any]]) -> str:
        """Check if bids are stacking (building up)"""
        if len(quotes) < 5:
            return "NO"
            
        # Look at last 5 quotes
        recent = quotes[-5:]
        bid_sizes = [q.get('bid_size', 0) for q in recent]
        
        # Check if sizes are increasing
        increasing = all(bid_sizes[i] <= bid_sizes[i+1] for i in range(len(bid_sizes)-1))
        
        # Check if all sizes are significant
        all_significant = all(size > 3000 for size in bid_sizes)
        
        # Check if last size is much larger than first
        if bid_sizes[0] > 0:
            growth = bid_sizes[-1] / bid_sizes[0]
        else:
            growth = 0
            
        if increasing and all_significant and growth > 1.3:
            return "YES"
            
        return "NO"
        
    def _check_ask_pulling(self, quotes: List[Dict[str, Any]]) -> str:
        """Check if asks are being pulled (reducing)"""
        if len(quotes) < 5:
            return "NO"
            
        # Look at last 5 quotes
        recent = quotes[-5:]
        ask_sizes = [q.get('ask_size', 0) for q in recent]
        
        # Check if sizes are decreasing
        decreasing = all(ask_sizes[i] >= ask_sizes[i+1] for i in range(len(ask_sizes)-1))
        
        # Check if reduction is significant
        if ask_sizes[0] > 0:
            reduction = 1 - (ask_sizes[-1] / ask_sizes[0])
        else:
            reduction = 0
            
        if decreasing and reduction > 0.3:
            return "YES"
            
        return "NO"
        
    def _check_spread_tightening(self, quotes: List[Dict[str, Any]]) -> str:
        """Check if spread is tightening"""
        if len(quotes) < 5:
            return "NO"
            
        spreads = []
        
        for quote in quotes:
            bid = quote.get('bid_price', 0)
            ask = quote.get('ask_price', 0)
            
            if bid > 0 and ask > 0:
                spread = ask - bid
                spreads.append(spread)
                
        if len(spreads) < 3:
            return "NO"
            
        # Compare recent vs older spreads
        recent_avg = sum(spreads[-3:]) / 3
        older_avg = sum(spreads[:-3]) / (len(spreads) - 3) if len(spreads) > 3 else spreads[0]
        
        if older_avg > 0 and recent_avg < older_avg * 0.8:
            return "YES"
            
        return "NO"
        
    def _check_momentum_building(self, quotes: List[Dict[str, Any]], metrics: Dict[str, Any]) -> str:
        """Check if momentum is building"""
        # Check price movement
        bid_movement = abs(metrics.get('bid_price_movement', 0))
        
        # Check lift/drop imbalance
        bid_lifts = metrics.get('bid_lift_count', 0)
        bid_drops = metrics.get('bid_drop_count', 0)
        ask_lifts = metrics.get('ask_lift_count', 0)
        ask_drops = metrics.get('ask_drop_count', 0)
        
        # Bullish momentum
        if bid_lifts > bid_drops * 1.5 and bid_movement > 0.02:
            return "YES"
            
        # Bearish momentum
        if bid_drops > bid_lifts * 1.5 and bid_movement > 0.02:
            return "YES"
            
        # Check size dynamics
        bid_accel = metrics.get('bid_size_acceleration', 'STABLE')
        ask_accel = metrics.get('ask_size_acceleration', 'STABLE')
        
        if bid_accel == 'INCREASING' or ask_accel == 'DECREASING':
            return "YES"
            
        return "NO"
        
    def _check_aggressive_buying(self, quotes: List[Dict[str, Any]], metrics: Dict[str, Any]) -> str:
        """Check for aggressive buying behavior"""
        # Multiple indicators of aggressive buying
        indicators = 0
        
        # 1. Ask lifts dominate
        if metrics.get('ask_lift_count', 0) > metrics.get('ask_drop_count', 0) * 2:
            indicators += 1
            
        # 2. Large bid sizes appearing
        if metrics.get('large_bids_appeared', 0) > 3:
            indicators += 1
            
        # 3. Bid size increasing
        if metrics.get('bid_size_acceleration') == 'INCREASING':
            indicators += 1
            
        # 4. Price lifting
        if metrics.get('bid_price_movement', 0) > 0.05:
            indicators += 1
            
        return "YES" if indicators >= 2 else "NO"
        
    def _check_aggressive_selling(self, quotes: List[Dict[str, Any]], metrics: Dict[str, Any]) -> str:
        """Check for aggressive selling behavior"""
        # Multiple indicators of aggressive selling
        indicators = 0
        
        # 1. Bid drops dominate
        if metrics.get('bid_drop_count', 0) > metrics.get('bid_lift_count', 0) * 2:
            indicators += 1
            
        # 2. Large ask sizes appearing
        if metrics.get('large_asks_appeared', 0) > 3:
            indicators += 1
            
        # 3. Ask size increasing
        if metrics.get('ask_size_acceleration') == 'INCREASING':
            indicators += 1
            
        # 4. Price dropping
        if metrics.get('bid_price_movement', 0) < -0.05:
            indicators += 1
            
        return "YES" if indicators >= 2 else "NO"
