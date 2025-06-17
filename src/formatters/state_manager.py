"""State manager for order flow data - formats data for MCP responses"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StateManager:
    """Manages state for order flow analysis - optimized for gRPC snapshot calls"""
    
    def __init__(self, ticker: str, storage_client):
        """Initialize state manager"""
        self.ticker = ticker
        self.storage_client = storage_client
        
    def get_current_state(self, history_seconds: int = 600) -> Dict[str, Any]:
        """Get current state data using efficient snapshot method"""
        
        # Use gRPC snapshot if available for maximum efficiency
        if hasattr(self.storage_client, 'get_order_flow_snapshot'):
            try:
                snapshot = self.storage_client.get_order_flow_snapshot(
                    ticker=self.ticker,
                    quote_seconds=history_seconds,
                    pattern_seconds=history_seconds,
                    metric_windows=['10s', '1min', '5min'],
                    include_levels=True
                )
                
                if snapshot:
                    return self._process_snapshot(snapshot, history_seconds)
                    
            except Exception as e:
                logger.warning(f"Snapshot method failed, falling back to individual calls: {e}")
        
        # Fallback to individual calls for non-gRPC clients
        return self._get_state_individual_calls(history_seconds)
    
    def _process_snapshot(self, snapshot: Dict[str, Any], history_seconds: int) -> Dict[str, Any]:
        """Process gRPC snapshot data"""
        quotes = snapshot.get('quotes', [])
        if not quotes:
            return {
                'ticker': self.ticker,
                'timestamp': time.time(),
                'error': 'No recent quote data available'
            }
        
        latest_quote = snapshot.get('latest_quote') or (quotes[-1] if quotes else {})
        metrics = snapshot.get('metrics', {})
        patterns = snapshot.get('patterns', [])
        levels = snapshot.get('levels', {'bid': [], 'ask': []})
        
        # Calculate current price with proper validation
        current_price = 0
        if latest_quote:
            bid = latest_quote.get('bid_price', 0)
            ask = latest_quote.get('ask_price', 0)
            
            # Validate bid < ask relationship
            if bid and ask and bid < ask:
                current_price = (bid + ask) / 2
            elif bid and not ask:
                current_price = bid  # Use bid if ask is missing
            elif ask and not bid:
                current_price = ask  # Use ask if bid is missing
            # If bid >= ask or both are invalid, current_price remains 0
        
        # Build comprehensive state
        state = {
            'ticker': self.ticker,
            'timestamp': time.time(),
            'current_price': current_price,
            'latest_quote': latest_quote,
            'quote_count': len(quotes),
            'history_seconds': history_seconds,
            'metrics': {
                '10s': metrics.get('10s', {}),
                '1min': metrics.get('1min', {}),
                '5min': metrics.get('5min', {})
            },
            'significant_levels': levels,
            'patterns': patterns
        }
        
        return state
    
    def _get_state_individual_calls(self, history_seconds: int) -> Dict[str, Any]:
        """Fallback method using individual storage calls"""
        try:
            # Get recent quotes
            quotes = self.storage_client.get_recent_quotes(self.ticker, seconds=history_seconds)
            if not quotes:
                return {
                    'ticker': self.ticker,
                    'timestamp': time.time(),
                    'error': 'No recent quote data available'
                }
                
            # Get latest quote
            latest_quote = self.storage_client.get_latest_quote(self.ticker) or (quotes[-1] if quotes else {})
            
            # Get current metrics
            metrics_10s = self.storage_client.get_current_metrics(self.ticker, "10s")
            metrics_1min = self.storage_client.get_current_metrics(self.ticker, "1min")
            metrics_5min = self.storage_client.get_current_metrics(self.ticker, "5min")
            
            # Get significant levels
            levels = self.storage_client.get_significant_levels(self.ticker)
            
            # Get patterns
            patterns = self.storage_client.get_recent_patterns(self.ticker, seconds=history_seconds)
            
            # Calculate current price
            current_price = 0
            if latest_quote:
                bid = latest_quote.get('bid_price', 0)
                ask = latest_quote.get('ask_price', 0)
                if bid and ask:
                    current_price = (bid + ask) / 2
            
            # Build state
            state = {
                'ticker': self.ticker,
                'timestamp': time.time(),
                'current_price': current_price,
                'latest_quote': latest_quote,
                'quote_count': len(quotes),
                'history_seconds': history_seconds,
                'metrics': {
                    '10s': metrics_10s,
                    '1min': metrics_1min,
                    '5min': metrics_5min
                },
                'significant_levels': levels,
                'patterns': patterns
            }
            
            return state
            
        except Exception as e:
            logger.exception(f"Error getting state for {self.ticker}: {e}")
            return {
                'ticker': self.ticker,
                'timestamp': time.time(),
                'error': f'Failed to retrieve data: {str(e)}'
            }
    
    def get_mcp_formatted_data(self, history_seconds: int = 300, include_patterns: bool = True) -> str:
        """Get MCP-formatted XML response for order flow analysis"""
        
        # Get current state using efficient method
        state = self.get_current_state(history_seconds)
        
        # Handle errors
        if 'error' in state:
            return self._build_error_response(state['error'])
        
        # Build MCP XML response
        return self._build_mcp_response(state, include_patterns)
    
    def _build_mcp_response(self, state: Dict[str, Any], include_patterns: bool) -> str:
        """Build MCP XML response from state data"""
        ticker = state['ticker']
        timestamp = datetime.fromtimestamp(state['timestamp']).strftime('%Y-%m-%dT%H:%M:%S')
        current_price = state.get('current_price', 0)
        latest_quote = state.get('latest_quote', {})
        
        # Start XML response
        xml_parts = [
            f'<order_flow_data ticker="{ticker}" timestamp="{timestamp}" current_price="{current_price:.2f}">',
            f'    <data_summary>',
            f'        <quote_count>{state.get("quote_count", 0)}</quote_count>',
            f'        <history_window>{state.get("history_seconds", 0)}s</history_window>',
            f'        <pattern_count>{len(state.get("patterns", []))}</pattern_count>',
            f'    </data_summary>'
        ]
        
        # Add current quote information
        if latest_quote:
            xml_parts.extend([
                f'    <current_quote>',
                f'        <bid_price>{latest_quote.get("bid_price", 0):.3f}</bid_price>',
                f'        <ask_price>{latest_quote.get("ask_price", 0):.3f}</ask_price>',
                f'        <bid_size>{latest_quote.get("bid_size", 0)}</bid_size>',
                f'        <ask_size>{latest_quote.get("ask_size", 0)}</ask_size>',
                f'        <spread>{latest_quote.get("spread", 0):.3f}</spread>',
                f'    </current_quote>'
            ])
        
        # Add metrics for different time windows
        metrics = state.get('metrics', {})
        for window, window_metrics in metrics.items():
            if window_metrics:
                xml_parts.extend([
                    f'    <metrics window="{window}">',
                    self._format_metrics_xml(window_metrics),
                    f'    </metrics>'
                ])
        
        # Add significant levels
        levels = state.get('significant_levels', {'bid': [], 'ask': []})
        if levels['bid'] or levels['ask']:
            xml_parts.append('    <significant_levels>')
            
            # Bid levels
            if levels['bid']:
                xml_parts.append('        <bid_levels>')
                for level in levels['bid'][:5]:  # Top 5 levels
                    xml_parts.append(
                        f'            <level price="{level.get("price", 0):.2f}" '
                        f'appearances="{level.get("appearances", 0)}" '
                        f'total_size="{level.get("total_size", 0)}" />'
                    )
                xml_parts.append('        </bid_levels>')
            
            # Ask levels
            if levels['ask']:
                xml_parts.append('        <ask_levels>')
                for level in levels['ask'][:5]:  # Top 5 levels
                    xml_parts.append(
                        f'            <level price="{level.get("price", 0):.2f}" '
                        f'appearances="{level.get("appearances", 0)}" '
                        f'total_size="{level.get("total_size", 0)}" />'
                    )
                xml_parts.append('        </ask_levels>')
            
            xml_parts.append('    </significant_levels>')
        
        # Add patterns if requested
        if include_patterns:
            patterns = state.get('patterns', [])
            if patterns:
                xml_parts.append('    <detected_patterns>')
                for pattern in patterns[-10:]:  # Last 10 patterns
                    xml_parts.extend([
                        f'        <pattern type="{pattern.get("type", "unknown")}">',
                        f'            <subtype>{pattern.get("subtype", "")}</subtype>',
                        f'            <strength>{pattern.get("strength", "")}</strength>',
                        f'            <description>{pattern.get("description", "")}</description>',
                        f'        </pattern>'
                    ])
                xml_parts.append('    </detected_patterns>')
        
        xml_parts.append('</order_flow_data>')
        
        return '\n'.join(xml_parts)
    
    def _format_metrics_xml(self, metrics: Dict[str, Any]) -> str:
        """Format metrics as XML"""
        xml_parts = []
        
        # Momentum metrics
        if any(k in metrics for k in ['bid_price_movement', 'ask_price_movement']):
            xml_parts.extend([
                '        <momentum>',
                f'            <bid_movement>{metrics.get("bid_price_movement", 0):.3f}</bid_movement>',
                f'            <ask_movement>{metrics.get("ask_price_movement", 0):.3f}</ask_movement>',
                f'            <bid_lifts>{metrics.get("bid_lift_count", 0)}</bid_lifts>',
                f'            <ask_lifts>{metrics.get("ask_lift_count", 0)}</ask_lifts>',
                '        </momentum>'
            ])
        
        # Size dynamics
        if any(k in metrics for k in ['avg_bid_size', 'avg_ask_size']):
            xml_parts.extend([
                '        <size_dynamics>',
                f'            <avg_bid_size>{metrics.get("avg_bid_size", 0)}</avg_bid_size>',
                f'            <avg_ask_size>{metrics.get("avg_ask_size", 0)}</avg_ask_size>',
                f'            <large_bids>{metrics.get("large_bids_appeared", 0)}</large_bids>',
                f'            <large_asks>{metrics.get("large_asks_appeared", 0)}</large_asks>',
                '        </size_dynamics>'
            ])
        
        # Behaviors
        behaviors = metrics.get('behaviors', {})
        if behaviors:
            xml_parts.append('        <behaviors>')
            for behavior, value in behaviors.items():
                xml_parts.append(f'            <{behavior}>{value}</{behavior}>')
            xml_parts.append('        </behaviors>')
        
        return '\n'.join(xml_parts)
    
    def _build_error_response(self, error_message: str) -> str:
        """Build error response XML"""
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        
        return f"""<order_flow_data ticker="{self.ticker}" timestamp="{timestamp}" error="true">
    <error_message>{error_message}</error_message>
    <possible_causes>
        <cause>No data available for this ticker</cause>
        <cause>Data broker connection issue</cause>
        <cause>Storage backend not accessible</cause>
    </possible_causes>
    <suggestions>
        <suggestion>Verify the ticker symbol is correct</suggestion>
        <suggestion>Check if the data broker is running</suggestion>
        <suggestion>Ensure storage backend is accessible</suggestion>
    </suggestions>
</order_flow_data>"""