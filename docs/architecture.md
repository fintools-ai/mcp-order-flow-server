# Order Flow MCP Server - Architecture Overview

## System Design

The MCP Order Flow Server is designed as a real-time analysis system that processes market microstructure data to help LLM agents make informed options trading decisions.

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server (FastMCP)                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   MCP Tool Interface                    │ │
│  │              analyze_order_flow_tool()                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                              │                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  Background Processor                   │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │   Metrics   │  │  Patterns   │  │  Behaviors  │   │ │
│  │  │ Calculator  │  │  Detector   │  │  Analyzer   │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  └────────────────────────────────────────────────────────┘ │
│                              │                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    Redis Storage                        │ │
│  │  • Quotes (orderflow:quotes:{ticker})                  │ │
│  │  • Metrics (orderflow:metrics:{ticker}:{window})      │ │
│  │  • Patterns (orderflow:patterns:{ticker})             │ │
│  │  • Levels (orderflow:levels:{ticker}:{side})          │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Quote Ingestion**: The data broker (separate service) publishes quotes to Redis
2. **Processing Loop**: Background processor runs every second
3. **Analysis**: Calculates metrics, detects patterns, analyzes behaviors
4. **Storage**: Results stored in Redis with appropriate TTLs
5. **API Response**: MCP tool queries Redis and formats response

## Key Design Decisions

### 1. Separation of Concerns
- **Data Collection**: Handled by separate data broker (private repo)
- **Analysis**: This server focuses purely on analysis
- **Storage**: Redis acts as the decoupling layer

### 2. Time Windows
- **10 seconds**: Immediate momentum and behaviors
- **60 seconds**: Short-term patterns and trends
- **5 minutes**: Context and significant levels

### 3. Pattern Detection
- **Absorption**: Large orders absorbing flow at price levels
- **Stacking**: Building walls of orders
- **Momentum Shift**: Directional pressure changes
- **Iceberg**: Hidden liquidity detection

### 4. No Recommendations
The server provides pure data analysis without trading recommendations. The LLM agent interprets the data to make decisions.

## Performance Considerations

### Processing Efficiency
- Each ticker processed in <100ms
- Metrics cached in Redis to avoid recalculation
- Patterns detected incrementally

### Scalability
- Horizontal scaling possible (multiple instances)
- Redis handles concurrent reads/writes
- Each ticker processed independently

### Memory Management
- Quotes expire after 1 hour (configurable)
- Only significant patterns stored long-term
- Price levels cleaned up regularly

## Redis Schema

### Quote Storage
```
Key: orderflow:quotes:{ticker}
Type: Sorted Set
Score: Timestamp
Value: JSON quote data
TTL: 3600 seconds
```

### Metrics Storage
```
Key: orderflow:metrics:{ticker}:{window}
Type: Hash
Fields: Various metrics
TTL: 60-600 seconds depending on window
```

### Pattern Storage
```
Key: orderflow:patterns:{ticker}
Type: Sorted Set
Score: Timestamp
Value: JSON pattern data
TTL: 3600 seconds
```

### Price Level Storage
```
Key: orderflow:levels:{ticker}:{bid|ask}
Type: Sorted Set
Score: Significance (size * appearances)
Value: JSON level data
TTL: 3600 seconds
```

## Configuration

Environment variables control behavior:
- `REDIS_HOST`: Redis server host
- `REDIS_PORT`: Redis server port
- `LOG_LEVEL`: Logging verbosity
- `PROCESSOR_INTERVAL`: Processing frequency (seconds)

## Error Handling

- **Redis Connection**: Graceful degradation if Redis unavailable
- **Processing Errors**: Isolated per ticker, logged but don't crash
- **Pattern Detection**: Best effort, missing patterns logged
- **API Errors**: Clear error responses with troubleshooting hints
