#!/bin/bash

# Development helper script for MCP Order Flow Server

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

# Check for data source configuration
DATA_SOURCE=${DATA_SOURCE:-grpc}
echo -e "\n${YELLOW}Data source: ${DATA_SOURCE}${NC}"

if [ "$DATA_SOURCE" = "grpc" ]; then
    DATA_BROKER_URL=${DATA_BROKER_GRPC_URL:-localhost:9090}
    echo -e "${YELLOW}Checking gRPC broker at ${DATA_BROKER_URL}...${NC}"
    
    # Simple connectivity check for gRPC
    if nc -z ${DATA_BROKER_URL%:*} ${DATA_BROKER_URL#*:} 2>/dev/null; then
        echo -e "${GREEN}✓ gRPC broker is reachable${NC}"
    else
        echo -e "${YELLOW}⚠ gRPC broker not reachable at ${DATA_BROKER_URL}${NC}"
        echo "  Make sure the data broker is running"
    fi
    
elif [ "$DATA_SOURCE" = "redis" ]; then
    # Check Redis connection
    echo -e "${YELLOW}Checking Redis connection...${NC}"
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis is running${NC}"
        
        # Check if there's data
        KEYS=$(redis-cli keys "orderflow:quotes:*" | wc -l)
        if [ "$KEYS" -gt 0 ]; then
            echo -e "${GREEN}✓ Found $KEYS ticker(s) with data${NC}"
        else
            echo -e "${YELLOW}⚠ No order flow data found in Redis${NC}"
        fi
    else
        echo -e "${RED}✗ Redis is not running${NC}"
        echo "  Please start Redis first"
        exit 1
    fi
fi

# Generate protobuf files if needed
if [ "$DATA_SOURCE" = "grpc" ] && [ ! -f "src/proto/orderflow_pb2.py" ]; then
    echo -e "\n${YELLOW}Generating protobuf files...${NC}"
    ./generate_proto.sh
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
export DATA_SOURCE=${DATA_SOURCE}
export DATA_BROKER_GRPC_URL=${DATA_BROKER_GRPC_URL:-localhost:9090}
export LOG_LEVEL=${LOG_LEVEL:-INFO}

echo -e "\n${GREEN}Configuration:${NC}"
echo "  DATA_SOURCE=${DATA_SOURCE}"
if [ "$DATA_SOURCE" = "grpc" ]; then
    echo "  DATA_BROKER_GRPC_URL=${DATA_BROKER_GRPC_URL}"
else
    echo "  REDIS_HOST=${REDIS_HOST:-localhost}"
    echo "  REDIS_PORT=${REDIS_PORT:-6379}"
fi
echo "  LOG_LEVEL=${LOG_LEVEL}"

# Start the server
echo -e "\n${GREEN}Starting MCP Order Flow Server...${NC}"
echo "===================================="
echo ""

# Trap to handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Shutting down...${NC}"; exit' INT TERM

# Run the server
python -m src.mcp_server
