"""MCP Order Flow Server - Main entry point"""

from fastmcp import FastMCP
import os
import sys
import logging
import asyncio
from typing import Optional

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Import tool implementation
from src.tools.order_flow_tool import analyze_order_flow
from src.background.processor_service import ProcessorService

# Create MCP server instance
mcp = FastMCP("mcp-order-flow-server")

# Global processor service
processor_service = None


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


async def start_background_processor():
    """Start the background processor service"""
    global processor_service
    
    try:
        # Create processor service
        processor_service = ProcessorService()
        
        # Start in background
        logger.info("Starting background processor service")
        await processor_service.start()
        
    except Exception as e:
        logger.error(f"Failed to start background processor: {e}")
        # Don't crash the server if processor fails
        # The tool will still work but with stale data


async def stop_background_processor():
    """Stop the background processor service"""
    global processor_service
    
    if processor_service:
        logger.info("Stopping background processor service")
        await processor_service.stop()
        processor_service = None


# Server lifecycle hooks
@mcp.startup()
async def on_startup():
    """Called when the MCP server starts"""
    logger.info("MCP Order Flow Server starting up")
    
    # Start background processor
    asyncio.create_task(start_background_processor())
    
    logger.info("Server startup complete")


@mcp.shutdown()
async def on_shutdown():
    """Called when the MCP server shuts down"""
    logger.info("MCP Order Flow Server shutting down")
    
    # Stop background processor
    await stop_background_processor()
    
    logger.info("Server shutdown complete")


def main():
    """Main entry point"""
    logger.info(f"Starting MCP Order Flow Server")
    logger.info(f"Redis: {os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}")
    
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
