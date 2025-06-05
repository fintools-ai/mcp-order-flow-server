#!/bin/bash

# Development helper script for MCP Order Flow Server
# Ensures Redis is available and starts the server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}MCP Order Flow Server - Development Mode${NC}"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "src/mcp_server.py" ]; then
    echo -e "${RED}Error: Must run from the mcp-order-flow-server directory${NC}"
    exit 1
fi

# Check Redis connection
echo -e "\n${YELLOW}Checking Redis connection...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running${NC}"
    
    # Check if there's data flowing
    echo -e "\n${YELLOW}Checking for order flow data...${NC}"
    KEYS=$(redis-cli keys "orderflow:quotes:*" | wc -l)
    if [ "$KEYS" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $KEYS ticker(s) with quote data${NC}"
        
        # Show sample tickers
        echo -e "\nAvailable tickers:"
        redis-cli keys "orderflow:quotes:*" | sed 's/orderflow:quotes:/  - /' | head -10
        
        if [ "$KEYS" -gt 10 ]; then
            echo "  ... and $((KEYS - 10)) more"
        fi
    else
        echo -e "${YELLOW}⚠ No order flow data found in Redis${NC}"
        echo ""
        echo "Make sure the data broker is running:"
        echo "  cd ../mcp-trading-data-broker"
        echo "  ./dev_start.sh"
        echo ""
    fi
else
    echo -e "${RED}✗ Redis is not running${NC}"
    echo ""
    echo "Please start Redis first:"
    echo "  On macOS: brew services start redis"
    echo "  On Linux: sudo systemctl start redis"
    echo "  Or: redis-server --daemonize yes"
    echo ""
    exit 1
fi

# Check Python virtual environment
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo -e "\n${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Install/update dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Export environment variables
export REDIS_HOST=${REDIS_HOST:-localhost}
export REDIS_PORT=${REDIS_PORT:-6379}
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export PROCESSOR_INTERVAL=${PROCESSOR_INTERVAL:-1}

echo -e "\n${GREEN}Configuration:${NC}"
echo "  REDIS_HOST=$REDIS_HOST"
echo "  REDIS_PORT=$REDIS_PORT"
echo "  LOG_LEVEL=$LOG_LEVEL"
echo "  PROCESSOR_INTERVAL=${PROCESSOR_INTERVAL}s"

# Start the server
echo -e "\n${GREEN}Starting MCP Order Flow Server...${NC}"
echo "===================================="
echo ""

# Trap to handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Shutting down...${NC}"; exit' INT TERM

# Run the server
python -m src.mcp_server
