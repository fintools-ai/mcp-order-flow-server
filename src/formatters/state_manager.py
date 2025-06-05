"""State manager for order flow data - formats data for MCP responses"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..storage.redis_client import OrderFlowRedisClient

logger = logging.getLogger(__name__)


class StateManager:
    """Manages state for order flow analysis - provides data only, no recommendations"""
    
    def __init__(self, ticker: str, redis_client: Optional[OrderFlowRedisClient] = None):
        """Initialize state manager"""
        self.ticker = ticker
        self.redis_client = redis_client or OrderFlowRedisClient()
        
    def get_current_state(self, history_seconds: int = 600) -> Dict[str, Any]:
        """Get current state data with specified history"""
        # Get recent quotes for the full history period
        quotes = self.redis_client.get_recent_quotes(self.ticker, seconds=history_seconds)
        if not quotes:
            return {
                'ticker': self.ticker,
                'timestamp': time.time(),
                'error': 'No recent quote data available'
            }
            
        # Get latest quote
        latest_quote = self.redis_client.get_latest_quote(self.ticker) or (quotes[-1] if quotes else {})
        
        # Get current metrics (snapshots)
        metrics_10s = self.redis_client.get_current_metrics(self.ticker, "10s")
        metrics_1min = self.redis_client.get_current_metrics(self.ticker, "1min")
        metrics_5min = self.redis_client.get_current_metrics(self.ticker, "5min")
        
        # Get significant levels
        levels = self.redis_client.get_significant_levels(self.ticker)
        
        # Get patterns for the FULL history period
        patterns = self.redis_client.get_recent_patterns(self.ticker, seconds=history_seconds)
        
        # Calculate current price (mid-point)
        current_price = 0
        if latest_quote:
            bid = latest_quote.get('bid_price', 0)
            ask = latest_quote.get('ask_price', 0)
            if bid > 0 and ask > 0:
                current_price = (bid + ask) / 2
                
        # Build state
        state = {
            'ticker': self.ticker,
            'timestamp': time.time(),
            'current_price': current_price,
            'latest_quote': latest_quote,
            'metrics_10s': metrics_10s,
            'metrics_1min': metrics_1min,
            'metrics_5min': metrics_5min,
            'significant_levels': levels,
            'recent_patterns': patterns,
            'quote_count': len(quotes),
            'history_seconds': history_seconds
        }
        
        return state
        
    def get_mcp_formatted_data(self, history_seconds: int = 600, include_patterns: bool = True) -> str:
        """Get MCP-formatted data - pure data only, no recommendations"""
        # Get current state with specified history
        state = self.get_current_state(history_seconds)
        
        if 'error' in state:
            return self._format_error_response(state['error'])
            
        # Format data-only response
        return self._format_data_only_mcp(state, include_patterns)
        
    def _format_data_only_mcp(self, state: Dict[str, Any], include_patterns: bool = True) -> str:
        """Format pure data for LLM to analyze"""
        timestamp = datetime.fromtimestamp(state['timestamp']).isoformat()
        latest_quote = state.get('latest_quote', {})
        metrics_10s = state.get('metrics_10s', {})
        metrics_1min = state.get('metrics_1min', {})
        metrics_5min = state.get('metrics_5min', {})
        levels = state.get('significant_levels', {})
        current_price = state.get('current_price', 0)
        history_seconds = state.get('history_seconds', 600)
        
        # Calculate basic metrics
        bid_size = int(latest_quote.get('bid_size', 0))
        ask_size = int(latest_quote.get('ask_size', 0))
        bid_ask_ratio = round(bid_size / ask_size, 2) if ask_size > 0 else 0
        
        # Calculate spread
        bid_price = float(latest_quote.get('bid_price', 0))
        ask_price = float(latest_quote.get('ask_price', 0))
        spread = ask_price - bid_price if bid_price > 0 and ask_price > 0 else 0
        spread_bps = (spread / current_price * 10000) if current_price > 0 else 0
        
        # Start building MCP response
        mcp = f'<order_flow_data ticker="{self.ticker}" timestamp="{timestamp}" current_price="{current_price:.2f}" history_window="{history_seconds}s">\n'
        
        # Current Quote
        mcp += f'  <current_quote>\n'
        mcp += f'    <bid price="{bid_price:.2f}" size="{bid_size}" />\n'
        mcp += f'    <ask price="{ask_price:.2f}" size="{ask_size}" />\n'
        mcp += f'    <bid_ask_ratio>{bid_ask_ratio}</bid_ask_ratio>\n'
        mcp += f'    <spread value="{spread:.4f}" basis_points="{spread_bps:.1f}" />\n'
        mcp += f'  </current_quote>\n'
        
        # Momentum Data
        mcp += f'  <momentum>\n'
        mcp += f'    <last_10s>\n'
        mcp += f'      <bid_price_change>{metrics_10s.get("bid_price_movement", 0):.4f}</bid_price_change>\n'
        mcp += f'      <ask_price_change>{metrics_10s.get("ask_price_movement", 0):.4f}</ask_price_change>\n'
        mcp += f'      <bid_size_change>{metrics_10s.get("net_bid_size_change", 0)}</bid_size_change>\n'
        mcp += f'      <ask_size_change>{metrics_10s.get("net_ask_size_change", 0)}</ask_size_change>\n'
        mcp += f'    </last_10s>\n'
        mcp += f'    <last_60s>\n'
        mcp += f'      <bid_price_change>{metrics_1min.get("bid_price_movement", 0):.4f}</bid_price_change>\n'
        mcp += f'      <ask_price_change>{metrics_1min.get("ask_price_movement", 0):.4f}</ask_price_change>\n'
        mcp += f'      <bid_lifts>{metrics_1min.get("bid_lift_count", 0)}</bid_lifts>\n'
        mcp += f'      <bid_drops>{metrics_1min.get("bid_drop_count", 0)}</bid_drops>\n'
        mcp += f'      <ask_lifts>{metrics_1min.get("ask_lift_count", 0)}</ask_lifts>\n'
        mcp += f'      <ask_drops>{metrics_1min.get("ask_drop_count", 0)}</ask_drops>\n'
        mcp += f'    </last_60s>\n'
        
        # Add 5min metrics if available
        if metrics_5min:
            mcp += f'    <last_5min>\n'
            mcp += f'      <bid_price_change>{metrics_5min.get("bid_price_movement", 0):.4f}</bid_price_change>\n'
            mcp += f'      <ask_price_change>{metrics_5min.get("ask_price_movement", 0):.4f}</ask_price_change>\n'
            mcp += f'      <bid_lifts>{metrics_5min.get("bid_lift_count", 0)}</bid_lifts>\n'
            mcp += f'      <bid_drops>{metrics_5min.get("bid_drop_count", 0)}</bid_drops>\n'
            mcp += f'    </last_5min>\n'
            
        mcp += f'  </momentum>\n'
        
        # Size Metrics
        mcp += f'  <size_metrics>\n'
        mcp += f'    <large_orders>\n'
        mcp += f'      <bids_over_10k>{metrics_1min.get("large_bids_appeared", 0)}</bids_over_10k>\n'
        mcp += f'      <asks_over_10k>{metrics_1min.get("large_asks_appeared", 0)}</asks_over_10k>\n'
        mcp += f'    </large_orders>\n'
        mcp += f'    <average_sizes>\n'
        mcp += f'      <bid_avg>{metrics_1min.get("avg_bid_size", 0)}</bid_avg>\n'
        mcp += f'      <ask_avg>{metrics_1min.get("avg_ask_size", 0)}</ask_avg>\n'
        mcp += f'    </average_sizes>\n'
        mcp += f'    <acceleration>\n'
        mcp += f'      <bid>{metrics_1min.get("bid_size_acceleration", "STABLE")}</bid>\n'
        mcp += f'      <ask>{metrics_1min.get("ask_size_acceleration", "STABLE")}</ask>\n'
        mcp += f'    </acceleration>\n'
        mcp += f'  </size_metrics>\n'
        
        # Market Behaviors
        behaviors = metrics_10s.get('behaviors', {})
        mcp += f'  <behaviors>\n'
        mcp += f'    <bid_stacking>{behaviors.get("bid_stacking", "NO")}</bid_stacking>\n'
        mcp += f'    <ask_pulling>{behaviors.get("ask_pulling", "NO")}</ask_pulling>\n'
        mcp += f'    <spread_tightening>{behaviors.get("spread_tightening", "NO")}</spread_tightening>\n'
        mcp += f'    <momentum_building>{behaviors.get("momentum_building", "NO")}</momentum_building>\n'
        mcp += f'  </behaviors>\n'
        
        # Price Levels
        mcp += f'  <price_levels>\n'
        
        # Find nearest support and resistance
        if levels.get('bid'):
            for level in levels['bid'][:3]:  # Top 3 bid levels
                if level.get('price', 0) < current_price:
                    distance = ((current_price - level['price']) / current_price) * 100 if current_price > 0 else 0
                    mcp += f'    <bid_level price="{level["price"]:.2f}" size="{level.get("total_size", 0)}" appearances="{level.get("appearances", 0)}" distance_pct="{distance:.2f}" />\n'
                    
        if levels.get('ask'):
            for level in levels['ask'][:3]:  # Top 3 ask levels
                if level.get('price', 0) > current_price:
                    distance = ((level['price'] - current_price) / current_price) * 100 if current_price > 0 else 0
                    mcp += f'    <ask_level price="{level["price"]:.2f}" size="{level.get("total_size", 0)}" appearances="{level.get("appearances", 0)}" distance_pct="{distance:.2f}" />\n'
                    
        # Add recent sweep if any
        last_sweep = metrics_1min.get('last_sweep')
        if last_sweep and isinstance(last_sweep, dict):
            timestamp = last_sweep.get('timestamp', 0)
            # Convert to seconds if timestamp is in milliseconds
            if timestamp > 1e10:  # Likely milliseconds
                seconds_ago = int(time.time() - timestamp / 1000)
            else:
                seconds_ago = int(time.time() - timestamp)
                
            if seconds_ago < 300:  # Only show sweeps from last 5 minutes
                mcp += f'    <sweep price="{last_sweep.get("price", 0):.2f}" size="{last_sweep.get("size", 0)}" direction="{last_sweep.get("direction", "")}" seconds_ago="{seconds_ago}" />\n'
                
        mcp += f'  </price_levels>\n'
        
        # Flow Velocity
        mcp += f'  <velocity>\n'
        mcp += f'    <quotes_per_second>{round(state.get("quote_count", 0) / max(history_seconds, 1), 1)}</quotes_per_second>\n'
        
        price_velocity = abs(metrics_1min.get('bid_price_movement', 0)) / 60 if metrics_1min.get('bid_price_movement') else 0
        mcp += f'    <price_velocity>{price_velocity:.6f}</price_velocity>\n'
        
        size_turnover = (abs(metrics_1min.get('net_bid_size_change', 0)) + abs(metrics_1min.get('net_ask_size_change', 0))) / 60
        mcp += f'    <size_turnover>{round(size_turnover)}</size_turnover>\n'
        mcp += f'  </velocity>\n'
        
        # Recent Patterns (if requested)
        if include_patterns:
            patterns = state.get('recent_patterns', [])
            if patterns:
                mcp += f'  <detected_patterns count="{len(patterns)}" window="{history_seconds}s">\n'
                
                # Show last 10 patterns or all if less
                display_patterns = patterns[-10:] if len(patterns) > 10 else patterns
                
                for pattern in display_patterns:
                    if not isinstance(pattern, dict):
                        continue
                        
                    timestamp = pattern.get('timestamp', 0)
                    # Convert to seconds properly
                    if timestamp > 1e10:  # Likely milliseconds
                        seconds_ago = int(time.time() - timestamp / 1000)
                    else:
                        seconds_ago = int(time.time() - timestamp)
                        
                    if seconds_ago > history_seconds:
                        continue  # Skip patterns outside our window
                        
                    mcp += f'    <pattern>\n'
                    mcp += f'      <type>{pattern.get("type", "unknown")}</type>\n'
                    
                    # Add pattern-specific details
                    if pattern.get('type') == 'absorption':
                        mcp += f'      <side>{pattern.get("side", "")}</side>\n'
                        mcp += f'      <strength>{pattern.get("strength", "")}</strength>\n'
                        mcp += f'      <price_level>{pattern.get("price_level", 0):.2f}</price_level>\n'
                        mcp += f'      <volume>{pattern.get("volume", 0)}</volume>\n'
                        
                    elif pattern.get('type') == 'stacking':
                        mcp += f'      <side>{pattern.get("side", "")}</side>\n'
                        mcp += f'      <levels>{pattern.get("levels", 0)}</levels>\n'
                        mcp += f'      <total_size>{pattern.get("total_size", 0)}</total_size>\n'
                        
                    elif pattern.get('type') == 'sweep':
                        mcp += f'      <direction>{pattern.get("direction", "")}</direction>\n'
                        mcp += f'      <price>{pattern.get("price", 0):.2f}</price>\n'
                        mcp += f'      <size>{pattern.get("size", 0)}</size>\n'
                        
                    elif pattern.get('type') == 'momentum_shift':
                        mcp += f'      <direction>{pattern.get("direction", "")}</direction>\n'
                        mcp += f'      <strength>{pattern.get("strength", "")}</strength>\n'
                        
                    # Common fields
                    if pattern.get('description'):
                        mcp += f'      <description>{pattern.get("description", "")}</description>\n'
                    mcp += f'      <detected_seconds_ago>{seconds_ago}</detected_seconds_ago>\n'
                    mcp += f'    </pattern>\n'
                    
                mcp += f'  </detected_patterns>\n'
                
        mcp += f'</order_flow_data>'
        
        return mcp
        
    def _format_error_response(self, error_message: str) -> str:
        """Format error response"""
        timestamp = datetime.now().isoformat()
        
        mcp = f'<order_flow_data ticker="{self.ticker}" timestamp="{timestamp}" error="true">\n'
        mcp += f'  <error_message>{error_message}</error_message>\n'
        mcp += f'</order_flow_data>'
        
        return mcp
