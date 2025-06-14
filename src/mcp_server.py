"""MCP Order Flow Server - Main entry point"""

from fastmcp import FastMCP
import os
import sys
import logging
from typing import Optional

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Import tool implementation
from src.tools.order_flow_tool import analyze_order_flow

# Create MCP server instance
mcp = FastMCP("mcp-order-flow-server")


@mcp.tool()
async def analyze_order_flow_tool(
    ticker: str,
    history: str = "5mins",
    include_patterns: bool = True
) -> str:
    """
    Analyzes order flow data for options trading decisions.
    
    This tool provides real-time analysis of order book dynamics including:
    - Bid/ask momentum and size changes
    - Pattern detection (absorption, stacking, sweeps)
    - Support/resistance levels from order flow
    - Market behavior indicators
    
    Args:
        ticker: Stock ticker symbol (e.g., SPY, QQQ)
        history: Time window for analysis (e.g., "5mins", "10mins", "30s")
        include_patterns: Whether to include pattern detection in response
        
    Returns:
        XML-formatted analysis optimized for LLM decision making
    """
    try:
        result = await analyze_order_flow(ticker, history, include_patterns)
        return result
    except Exception as e:
        logger.error(f"Error analyzing order flow for {ticker}: {e}")
        return f"""<order_flow_data ticker="{ticker}" error="true">
    <error_message>{str(e)}</error_message>
    <suggestion>Please verify the ticker and try again</suggestion>
</order_flow_data>"""


def main():
    """Main entry point"""
    # Log startup info
    logger.info("MCP Order Flow Server starting up")
    
    data_source = os.getenv('DATA_SOURCE', 'grpc')
    logger.info(f"Data source: {data_source}")
    
    if data_source == 'grpc':
        logger.info(f"gRPC URL: {os.getenv('DATA_BROKER_GRPC_URL', 'localhost:9090')}")
    elif data_source == 'data_broker':
        logger.info(f"HTTP URL: {os.getenv('DATA_BROKER_URL', 'http://localhost:8080')}")
    else:
        logger.info(f"Redis: {os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}")
    
    logger.info("Server startup complete")
    
    # Run the server
    mcp.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)
