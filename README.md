# MCP Order Flow Server

A high-performance Model Context Protocol (MCP) server that provides real-time order flow analysis for algorithmic trading applications. This server connects to market data brokers via gRPC to deliver institutional-grade market microstructure insights.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![gRPC](https://img.shields.io/badge/gRPC-enabled-green.svg)](https://grpc.io/)
[![MCP](https://img.shields.io/badge/MCP-compatible-orange.svg)](https://modelcontextprotocol.io/)

## Features

- **Real-time Order Flow Analysis**: Live market microstructure data processing
- **High-Performance gRPC Integration**: Sub-millisecond latency data retrieval
- **Institutional Pattern Detection**: Absorption, stacking, and sweep patterns
- **Support/Resistance Levels**: Algorithmically derived key price levels
- **Market Momentum Metrics**: Bid/ask dynamics and size acceleration
- **MCP Protocol Compliance**: Seamless integration with AI agents and LLMs

## Quick Start

### Prerequisites

- Python 3.10 or higher
- A compatible market data broker (gRPC endpoint)
- Basic understanding of market microstructure concepts

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mcp-order-flow-server
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Generate protobuf files** (if using gRPC data source):
   ```bash
   ./generate_proto.sh
   ```

4. **Configure environment** (optional):
   ```bash
   export DATA_BROKER_GRPC_URL=localhost:9090
   export LOG_LEVEL=INFO
   ```

5. **Start the server**:
   ```bash
   python src/mcp_server.py
   ```

## Usage

### MCP Tool: `analyze_order_flow_tool`

The server exposes a single MCP tool for order flow analysis:

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ticker` | string | **required** | Stock/ETF ticker symbol (e.g., "SPY", "QQQ") |
| `history` | string | `"5mins"` | Analysis time window (e.g., "30s", "10mins", "1h") |
| `include_patterns` | boolean | `true` | Include pattern detection in response |

#### Example Request

```json
{
  "method": "tools/call",
  "params": {
    "name": "analyze_order_flow_tool",
    "arguments": {
      "ticker": "SPY",
      "history": "5mins",
      "include_patterns": true
    }
  }
}
```

#### Example Response

```xml
<order_flow_data ticker="SPY" timestamp="2024-01-15T10:30:00" current_price="485.24">
    <data_summary>
        <quote_count>1847</quote_count>
        <history_window>300s</history_window>
        <pattern_count>3</pattern_count>
    </data_summary>
    
    <current_quote>
        <bid_price>485.230</bid_price>
        <ask_price>485.250</ask_price>
        <bid_size>1800</bid_size>
        <ask_size>1200</ask_size>
        <spread>0.020</spread>
    </current_quote>
    
    <metrics window="10s">
        <momentum>
            <bid_movement>0.050</bid_movement>
            <ask_movement>0.045</ask_movement>
            <bid_lifts>3</bid_lifts>
            <ask_lifts>2</ask_lifts>
        </momentum>
        <size_dynamics>
            <avg_bid_size>1650</avg_bid_size>
            <avg_ask_size>1250</avg_ask_size>
            <large_bids>1</large_bids>
            <large_asks>0</large_asks>
        </size_dynamics>
        <behaviors>
            <bid_stacking>YES</bid_stacking>
            <momentum_building>YES</momentum_building>
        </behaviors>
    </metrics>
    
    <significant_levels>
        <bid_levels>
            <level price="485.20" appearances="15" total_size="45000" />
            <level price="485.15" appearances="12" total_size="38000" />
        </bid_levels>
        <ask_levels>
            <level price="485.30" appearances="12" total_size="38000" />
            <level price="485.35" appearances="9" total_size="28000" />
        </ask_levels>
    </significant_levels>
    
    <detected_patterns>
        <pattern type="absorption">
            <subtype>bullish</subtype>
            <strength>strong</strength>
            <description>Strong bid absorption at 485.20</description>
        </pattern>
    </detected_patterns>
</order_flow_data>
```

## Configuration

### Environment Variables

```bash
# Data source configuration
DATA_SOURCE=grpc                    # Use 'grpc' (recommended) or 'redis'
DATA_BROKER_GRPC_URL=localhost:9090 # gRPC endpoint for market data

# Redis fallback (if DATA_SOURCE=redis)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Logging
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR
```

### Data Sources

| Source | Latency | Throughput | Use Case |
|--------|---------|------------|----------|
| **gRPC** | 0.1-0.5ms | 2000+ req/s | Production (Recommended) |
| **Redis** | 0.5-2ms | 500+ req/s | Development/Fallback |

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│   MCP Client    │───▶│  MCP Server      │───▶│  Market Data      │
│  (AI Agent)     │    │  (This Repo)     │    │  Broker (gRPC)    │
└─────────────────┘    └──────────────────┘    └───────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Order Flow      │
                       │  Analysis Engine │
                       └──────────────────┘
```

### Key Components

- **MCP Server**: FastMCP-based server handling tool requests
- **gRPC Client**: High-performance data retrieval from market broker
- **State Manager**: XML response formatting and data aggregation
- **Pattern Detector**: Real-time institutional pattern recognition

## Development

### Project Structure

```
mcp-order-flow-server/
├── src/
│   ├── mcp_server.py           # Main MCP server entry point
│   ├── config.py               # Configuration management
│   ├── proto/                  # Generated protobuf files
│   ├── storage/
│   │   ├── grpc_client.py     # gRPC data client
│   │   └── redis_client.py    # Redis fallback client
│   ├── formatters/
│   │   └── state_manager.py   # XML response formatting
│   └── tools/
│       └── order_flow_tool.py # MCP tool implementation
├── generate_proto.sh           # Protobuf generation script
├── test_tool.py               # Development testing
└── requirements.txt           # Python dependencies
```

### Testing

```bash
# Run development tests
python test_tool.py

# Test specific ticker
python -c "
import asyncio
from src.tools.order_flow_tool import analyze_order_flow
result = asyncio.run(analyze_order_flow('SPY', '1min', True))
print(result)
"
```

### Regenerating Protobuf Files

If the market data broker's protobuf definitions change:

```bash
./generate_proto.sh
```

## Performance

### Benchmarks

- **Analysis Latency**: < 1ms per request (gRPC mode)
- **Concurrent Requests**: 2000+ simultaneous analyses
- **Memory Usage**: ~50MB base + 1KB per active ticker
- **CPU Usage**: < 5% on modern hardware

### Optimization Tips

1. **Use gRPC mode** for production deployments
2. **Reduce history window** for faster responses
3. **Disable patterns** if not needed (`include_patterns=false`)
4. **Batch requests** when analyzing multiple tickers

## Error Handling

The server provides detailed error responses for common issues:

```xml
<order_flow_data ticker="INVALID" error="true">
    <error_message>No data available for ticker</error_message>
    <possible_causes>
        <cause>Invalid ticker symbol</cause>
        <cause>Market data broker not running</cause>
        <cause>Network connectivity issues</cause>
    </possible_causes>
    <suggestions>
        <suggestion>Verify ticker symbol is correct</suggestion>
        <suggestion>Check market data broker status</suggestion>
        <suggestion>Ensure network connectivity</suggestion>
    </suggestions>
</order_flow_data>
```