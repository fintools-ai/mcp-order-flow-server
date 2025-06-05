# Order Flow MCP Server - API Examples

## MCP Tool Usage

### Basic Order Flow Analysis

Request:
```python
result = await analyze_order_flow_tool(
    ticker="SPY",
    history="5mins",
    include_patterns=True
)
```

Response:
```xml
<order_flow_data ticker="SPY" timestamp="2025-01-15T10:30:45" current_price="450.27" history_window="300s">
  
  <current_quote>
    <bid price="450.25" size="5000" />
    <ask price="450.30" size="2000" />
    <bid_ask_ratio>2.5</bid_ask_ratio>
    <spread value="0.0500" basis_points="1.1" />
  </current_quote>
  
  <momentum>
    <last_10s>
      <bid_price_change>0.0800</bid_price_change>
      <ask_price_change>0.0700</ask_price_change>
      <bid_size_change>3500</bid_size_change>
      <ask_size_change>-1200</ask_size_change>
    </last_10s>
    <last_60s>
      <bid_price_change>0.1500</bid_price_change>
      <ask_price_change>0.1400</ask_price_change>
      <bid_lifts>39</bid_lifts>
      <bid_drops>21</bid_drops>
      <ask_lifts>18</ask_lifts>
      <ask_drops>35</ask_drops>
    </last_60s>
    <last_5min>
      <bid_price_change>0.3200</bid_price_change>
      <ask_price_change>0.3100</ask_price_change>
      <bid_lifts>142</bid_lifts>
      <bid_drops>98</bid_drops>
    </last_5min>
  </momentum>
  
  <size_metrics>
    <large_orders>
      <bids_over_10k>8</bids_over_10k>
      <asks_over_10k>3</asks_over_10k>
    </large_orders>
    <average_sizes>
      <bid_avg>4200</bid_avg>
      <ask_avg>2800</ask_avg>
    </average_sizes>
    <acceleration>
      <bid>INCREASING</bid>
      <ask>STABLE</ask>
    </acceleration>
  </size_metrics>
  
  <behaviors>
    <bid_stacking>YES</bid_stacking>
    <ask_pulling>NO</ask_pulling>
    <spread_tightening>NO</spread_tightening>
    <momentum_building>YES</momentum_building>
  </behaviors>
  
  <price_levels>
    <bid_level price="450.20" size="85000" appearances="12" distance_pct="0.02" />
    <bid_level price="450.15" size="62000" appearances="8" distance_pct="0.04" />
    <ask_level price="450.35" size="45000" appearances="8" distance_pct="0.02" />
    <ask_level price="450.40" size="38000" appearances="6" distance_pct="0.04" />
    <sweep price="450.22" size="18000" direction="lift" seconds_ago="45" />
  </price_levels>
  
  <velocity>
    <quotes_per_second>12.5</quotes_per_second>
    <price_velocity>0.002500</price_velocity>
    <size_turnover>183</size_turnover>
  </velocity>
  
  <detected_patterns count="3" window="300s">
    <pattern>
      <type>absorption</type>
      <side>bid</side>
      <strength>strong</strength>
      <price_level>450.20</price_level>
      <volume>85000</volume>
      <description>Bid absorption at 450.20 with avg size 12000</description>
      <detected_seconds_ago>120</detected_seconds_ago>
    </pattern>
    <pattern>
      <type>momentum_shift</type>
      <direction>bullish</direction>
      <strength>moderate</strength>
      <description>Bullish momentum: 39 lifts vs 21 drops</description>
      <detected_seconds_ago>60</detected_seconds_ago>
    </pattern>
    <pattern>
      <type>stacking</type>
      <side>bid</side>
      <levels>5</levels>
      <total_size>42000</total_size>
      <description>Bid stacking detected with 42000 total size</description>
      <detected_seconds_ago>15</detected_seconds_ago>
    </pattern>
  </detected_patterns>
  
</order_flow_data>
```

### Quick Momentum Check

Request:
```python
result = await analyze_order_flow_tool(
    ticker="QQQ",
    history="30s",
    include_patterns=False  # Skip pattern detection for speed
)
```

Response (simplified):
```xml
<order_flow_data ticker="QQQ" timestamp="2025-01-15T10:31:00" current_price="380.15" history_window="30s">
  
  <current_quote>
    <bid price="380.14" size="3200" />
    <ask price="380.16" size="3100" />
    <bid_ask_ratio>1.03</bid_ask_ratio>
    <spread value="0.0200" basis_points="0.5" />
  </current_quote>
  
  <momentum>
    <last_10s>
      <bid_price_change>-0.0200</bid_price_change>
      <ask_price_change>-0.0200</ask_price_change>
      <bid_size_change>-500</bid_size_change>
      <ask_size_change>200</ask_size_change>
    </last_10s>
    <!-- Limited to 30s history, no 60s data -->
  </momentum>
  
  <behaviors>
    <bid_stacking>NO</bid_stacking>
    <ask_pulling>NO</ask_pulling>
    <spread_tightening>YES</spread_tightening>
    <momentum_building>NO</momentum_building>
  </behaviors>
  
</order_flow_data>
```

### Error Response

Request:
```python
result = await analyze_order_flow_tool(
    ticker="INVALID",
    history="5mins"
)
```

Response:
```xml
<order_flow_data ticker="INVALID" timestamp="2025-01-15T10:31:15" error="true">
  <error_message>No recent quote data available</error_message>
  <possible_causes>
    <cause>No data available for this ticker</cause>
    <cause>Redis connection issue</cause>
    <cause>Data broker not running</cause>
  </possible_causes>
  <suggestions>
    <suggestion>Verify the ticker symbol is correct</suggestion>
    <suggestion>Check if the data broker is running</suggestion>
    <suggestion>Ensure Redis is accessible</suggestion>
  </suggestions>
</order_flow_data>
```

## Interpretation Guide

### Bullish Signals
- `bid_ask_ratio` > 2.0
- `bid_lifts` > `bid_drops` * 1.5
- `bid_stacking` = YES
- `bid_size_acceleration` = INCREASING
- Large bid levels close to current price

### Bearish Signals
- `bid_ask_ratio` < 0.5
- `bid_drops` > `bid_lifts` * 1.5
- `ask_stacking` = YES
- `ask_size_acceleration` = INCREASING
- Large ask levels close to current price

### Momentum Building
- `momentum_building` = YES
- High `price_velocity`
- Increasing `size_turnover`
- Multiple patterns detected

### Support/Resistance
- `bid_level` entries show support levels
- `ask_level` entries show resistance levels
- `distance_pct` shows how far from current price
- Higher `appearances` = stronger level

## Use Cases

### 1. 0DTE Options Entry
Check 30s-1min data for immediate momentum:
```python
# Quick momentum check
data = await analyze_order_flow_tool("SPY", "1min", False)
# Look for momentum_building and directional bias
```

### 2. Swing Trade Setup
Analyze 5-10min data for patterns:
```python
# Deeper analysis with patterns
data = await analyze_order_flow_tool("SPY", "10mins", True)
# Look for absorption patterns and significant levels
```

### 3. Scalping Opportunities
Monitor very short timeframes:
```python
# Ultra-short term
data = await analyze_order_flow_tool("SPY", "30s", False)
# Focus on behaviors and immediate momentum
```

## Integration Examples

### With Claude Desktop
```json
{
  "mcpServers": {
    "order-flow": {
      "command": "uvx",
      "args": ["mcp-order-flow-server"]
    }
  }
}
```

### Python Client
```python
import asyncio
from mcp import Client

async def main():
    async with Client("order-flow") as client:
        result = await client.call_tool(
            "analyze_order_flow_tool",
            ticker="SPY",
            history="5mins"
        )
        print(result)

asyncio.run(main())
```
