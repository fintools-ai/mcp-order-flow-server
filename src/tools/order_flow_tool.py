"""Order flow analysis tool for MCP"""

import logging
from typing import Optional
import time

from src.formatters.state_manager import StateManager
from src.config import get_storage_client

logger = logging.getLogger(__name__)


async def analyze_order_flow(
    ticker: str,
    history: str = "5mins",
    include_patterns: bool = True
) -> str:
    """
    Analyze order flow data for a ticker
    
    Args:
        ticker: Stock ticker symbol
        history: History timeframe (e.g., '5mins', '10mins', '1h')
        include_patterns: Whether to include pattern detection
        
    Returns:
        XML-formatted order flow analysis
    """
    try:
        # Parse history string to seconds
        history_seconds = parse_time_string(history)
        
        # Get storage client (Redis or Data Broker)
        storage_client = get_storage_client()
        
        # Get state manager
        state_manager = StateManager(ticker, storage_client)
        
        # Get formatted data
        logger.info(f"Analyzing order flow for {ticker} with {history_seconds}s history")
        
        # Build response with pattern inclusion preference
        response = state_manager.get_mcp_formatted_data(
            history_seconds=history_seconds,
            include_patterns=include_patterns
        )
        
        return response
        
    except Exception as e:
        logger.exception(f"Error analyzing order flow for {ticker}: {e}")
        return build_error_response(ticker, str(e))


def parse_time_string(time_str: str) -> int:
    """
    Parse time string like '10mins' into seconds
    
    Args:
        time_str: Time string to parse (e.g., '5mins', '1h', '30s')
        
    Returns:
        Number of seconds
    """
    if not time_str:
        return 300  # Default: 5 minutes
        
    time_str = time_str.lower().strip()
    
    # Handle cases with no unit
    if time_str.isdigit():
        return int(time_str)
        
    # Handle various time units
    try:
        # Remove any whitespace
        time_str = time_str.replace(' ', '')
        
        # Seconds
        if time_str.endswith('s') or time_str.endswith('sec') or time_str.endswith('secs'):
            return int(time_str.rstrip('s').rstrip('sec').rstrip('secs'))
            
        # Minutes
        elif time_str.endswith('m') or time_str.endswith('min') or time_str.endswith('mins'):
            minutes = int(time_str.rstrip('m').rstrip('min').rstrip('mins'))
            return minutes * 60
            
        # Hours
        elif time_str.endswith('h') or time_str.endswith('hr') or time_str.endswith('hrs') or time_str.endswith('hour') or time_str.endswith('hours'):
            hours = int(time_str.rstrip('h').rstrip('hr').rstrip('hrs').rstrip('hour').rstrip('hours'))
            return hours * 3600
            
        # If no recognized unit, try to convert directly
        else:
            return int(time_str)
            
    except (ValueError, TypeError):
        # Fallback to default if parsing fails
        logger.warning(f"Could not parse time string: {time_str}. Using default of 5 minutes.")
        return 300


def build_error_response(ticker: str, error_message: str) -> str:
    """Build error response in MCP format"""
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%S')
    
    return f"""<order_flow_data ticker="{ticker}" timestamp="{timestamp}" error="true">
    <error_message>{error_message}</error_message>
    <possible_causes>
        <cause>No data available for this ticker</cause>
        <cause>Storage backend connection issue</cause>
        <cause>Data broker or Redis not running</cause>
    </possible_causes>
    <suggestions>
        <suggestion>Verify the ticker symbol is correct</suggestion>
        <suggestion>Check if the data broker is running</suggestion>
        <suggestion>Ensure storage backend is accessible</suggestion>
    </suggestions>
</order_flow_data>"""
