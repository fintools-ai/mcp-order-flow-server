#!/bin/bash

# Generate Python protobuf files from the trading data broker
# This script should be run from the mcp-order-flow-server directory

set -e

echo "Generating Python protobuf files..."

# Check if proto source exists
PROTO_SOURCE="../mcp-trading-data-broker/api/proto/orderflow.proto"
if [ ! -f "$PROTO_SOURCE" ]; then
    echo "Error: Cannot find orderflow.proto at $PROTO_SOURCE"
    echo "Make sure mcp-trading-data-broker is in the parent directory"
    exit 1
fi

# Create proto directory if it doesn't exist
mkdir -p src/proto

# Generate Python files
python -m grpc_tools.protoc \
    --python_out=src/proto \
    --grpc_python_out=src/proto \
    --proto_path=../mcp-trading-data-broker/api/proto \
    ../mcp-trading-data-broker/api/proto/orderflow.proto

# Create __init__.py if it doesn't exist
if [ ! -f "src/proto/__init__.py" ]; then
    echo "# Generated protobuf files" > src/proto/__init__.py
fi

# Fix import in generated gRPC file
sed -i '' 's/import orderflow_pb2/from . import orderflow_pb2/' src/proto/orderflow_pb2_grpc.py

echo " Protobuf files generated successfully!"
echo "Generated files:"
echo "  - src/proto/orderflow_pb2.py"
echo "  - src/proto/orderflow_pb2_grpc.py"
echo "  - src/proto/__init__.py"