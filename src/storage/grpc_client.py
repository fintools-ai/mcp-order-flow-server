"""High-performance gRPC client for MCP Trading Data Broker"""

import os
import logging
import time
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import grpc
from grpc import aio as grpc_aio

# Import generated protobuf files
from ..proto import orderflow_pb2, orderflow_pb2_grpc

logger = logging.getLogger(__name__)


class GRPCDataBrokerClient:
    """High-performance gRPC client for data broker"""
    
    def __init__(
        self,
        server_url: Optional[str] = None,
        max_message_size: int = 10 * 1024 * 1024,  # 10MB
        keepalive_time: int = 30,
        keepalive_timeout: int = 5,
        max_workers: int = 10
    ):
        """Initialize gRPC client with performance optimizations"""
        self.server_url = server_url or os.getenv('DATA_BROKER_GRPC_URL', 'localhost:9090')
        self.channel = None
        self.client = None
        
        # Performance options
        self.channel_options = [
            ('grpc.keepalive_time_ms', keepalive_time * 1000),
            ('grpc.keepalive_timeout_ms', keepalive_timeout * 1000),
            ('grpc.keepalive_permit_without_calls', True),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.min_time_between_pings_ms', 10000),
            ('grpc.http2.min_ping_interval_without_data_ms', 300000),
            ('grpc.max_receive_message_length', max_message_size),
            ('grpc.max_send_message_length', max_message_size),
            ('grpc.max_concurrent_streams', 1000),
            # Enable compression
            ('grpc.default_compression_algorithm', grpc.Compression.Gzip),
            ('grpc.default_compression_level', grpc.CompressionLevel.Medium),
        ]
        
        logger.info(f"GRPCDataBrokerClient initialized for {self.server_url}")
    
    async def _ensure_connection(self):
        """Ensure gRPC connection is established"""
        if self.channel is None:
            self.channel = grpc_aio.insecure_channel(
                self.server_url,
                options=self.channel_options
            )
            self.client = orderflow_pb2_grpc.OrderFlowServiceStub(self.channel)
            
            # Test connection with a health check
            try:
                await self._health_check()
            except Exception as e:
                logger.error(f"Failed to connect to gRPC server: {e}")
                raise
    
    async def _health_check(self):
        """Simple health check by trying to get recent quotes for a common ticker"""
        try:
            request = orderflow_pb2.GetRecentQuotesRequest(
                ticker="SPY",
                seconds=10
            )
            response = await self.client.GetRecentQuotes(request, timeout=5)
            logger.debug(f"Health check successful, got {len(response.quotes)} quotes")
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                # No data available is acceptable for health check
                logger.debug("Health check: No data available but connection is working")
            else:
                raise
    
    async def get_recent_quotes(self, ticker: str, seconds: int = 300) -> List[Dict[str, Any]]:
        """Get recent quotes using gRPC"""
        await self._ensure_connection()
        
        try:
            request = orderflow_pb2.GetRecentQuotesRequest(
                ticker=ticker,
                seconds=seconds
            )
            
            response = await self.client.GetRecentQuotes(request)
            
            # Convert protobuf response to dict format
            quotes = []
            for proto_quote in response.quotes:
                quote = {
                    'ticker': proto_quote.ticker,
                    'timestamp': int(proto_quote.timestamp.seconds * 1000 + proto_quote.timestamp.nanos // 1000000),
                    'bid_price': proto_quote.bid_price,
                    'bid_size': proto_quote.bid_size,
                    'ask_price': proto_quote.ask_price,
                    'ask_size': proto_quote.ask_size,
                    'mid_price': proto_quote.mid_price,
                    'spread': proto_quote.spread,
                }
                quotes.append(quote)
            
            logger.debug(f"Retrieved {len(quotes)} quotes for {ticker}")
            return quotes
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting quotes for {ticker}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting quotes for {ticker}: {e}")
            return []
    
    async def get_current_metrics(self, ticker: str, window: str) -> Dict[str, Any]:
        """Get current metrics using gRPC"""
        await self._ensure_connection()
        
        try:
            request = orderflow_pb2.GetCurrentMetricsRequest(
                ticker=ticker,
                window=window
            )
            
            response = await self.client.GetCurrentMetrics(request)
            
            # Convert protobuf to dict
            metrics = {
                'ticker': response.ticker,
                'timestamp': int(response.timestamp.seconds),
                'window': response.window,
                'behaviors': dict(response.behaviors),
            }
            
            # Add momentum metrics
            if response.HasField('momentum'):
                metrics.update({
                    'bid_price_movement': response.momentum.bid_price_movement,
                    'ask_price_movement': response.momentum.ask_price_movement,
                    'bid_lift_count': response.momentum.bid_lift_count,
                    'bid_drop_count': response.momentum.bid_drop_count,
                    'ask_lift_count': response.momentum.ask_lift_count,
                    'ask_drop_count': response.momentum.ask_drop_count,
                    'net_bid_size_change': response.momentum.net_bid_size_change,
                    'net_ask_size_change': response.momentum.net_ask_size_change,
                })
            
            # Add size dynamics
            if response.HasField('size_dynamics'):
                metrics.update({
                    'large_bids_appeared': response.size_dynamics.large_bids_appeared,
                    'large_asks_appeared': response.size_dynamics.large_asks_appeared,
                    'avg_bid_size': response.size_dynamics.avg_bid_size,
                    'avg_ask_size': response.size_dynamics.avg_ask_size,
                    'bid_size_acceleration': response.size_dynamics.bid_size_acceleration,
                    'ask_size_acceleration': response.size_dynamics.ask_size_acceleration,
                })
            
            logger.debug(f"Retrieved metrics for {ticker}:{window}")
            return metrics
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting metrics for {ticker}:{window}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting metrics for {ticker}:{window}: {e}")
            return {}
    
    async def get_recent_patterns(self, ticker: str, seconds: int = 300) -> List[Dict[str, Any]]:
        """Get recent patterns using gRPC"""
        await self._ensure_connection()
        
        try:
            request = orderflow_pb2.GetRecentPatternsRequest(
                ticker=ticker,
                seconds=seconds
            )
            
            response = await self.client.GetRecentPatterns(request)
            
            patterns = []
            for proto_pattern in response.patterns:
                pattern = {
                    'type': proto_pattern.type,
                    'timestamp': int(proto_pattern.timestamp.seconds * 1000 + proto_pattern.timestamp.nanos // 1000000),
                    'subtype': proto_pattern.subtype,
                    'strength': proto_pattern.strength,
                    'direction': proto_pattern.direction,
                    'price': proto_pattern.price,
                    'price_level': proto_pattern.price_level,
                    'price_range': proto_pattern.price_range,
                    'size': proto_pattern.size,
                    'volume': proto_pattern.volume,
                    'duration_seconds': proto_pattern.duration_seconds,
                    'institutional_percentage': proto_pattern.institutional_percentage,
                    'spread_tightening': proto_pattern.spread_tightening,
                    'price_movement': proto_pattern.price_movement,
                    'description': proto_pattern.description,
                }
                patterns.append(pattern)
            
            logger.debug(f"Retrieved {len(patterns)} patterns for {ticker}")
            return patterns
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting patterns for {ticker}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting patterns for {ticker}: {e}")
            return []
    
    async def get_significant_levels(self, ticker: str, min_appearances: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Get significant levels using gRPC"""
        await self._ensure_connection()
        
        try:
            request = orderflow_pb2.GetSignificantLevelsRequest(
                ticker=ticker,
                min_appearances=min_appearances
            )
            
            response = await self.client.GetSignificantLevels(request)
            
            levels = {'bid': [], 'ask': []}
            
            for proto_level in response.bid_levels:
                level = {
                    'price': proto_level.price,
                    'appearances': proto_level.appearances,
                    'total_size': proto_level.total_size,
                    'last_seen': int(proto_level.last_seen.seconds),
                    'score': proto_level.score,
                }
                levels['bid'].append(level)
            
            for proto_level in response.ask_levels:
                level = {
                    'price': proto_level.price,
                    'appearances': proto_level.appearances,
                    'total_size': proto_level.total_size,
                    'last_seen': int(proto_level.last_seen.seconds),
                    'score': proto_level.score,
                }
                levels['ask'].append(level)
            
            logger.debug(f"Retrieved {len(levels['bid'])} bid and {len(levels['ask'])} ask levels for {ticker}")
            return levels
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting levels for {ticker}: {e}")
            return {'bid': [], 'ask': []}
        except Exception as e:
            logger.error(f"Unexpected error getting levels for {ticker}: {e}")
            return {'bid': [], 'ask': []}
    
    async def get_order_flow_snapshot(
        self, 
        ticker: str, 
        quote_seconds: int = 300,
        pattern_seconds: int = 300,
        metric_windows: List[str] = None,
        include_levels: bool = True
    ) -> Dict[str, Any]:
        """Get complete order flow snapshot - most efficient method"""
        await self._ensure_connection()
        
        try:
            request = orderflow_pb2.GetOrderFlowSnapshotRequest(
                ticker=ticker,
                quote_seconds=quote_seconds,
                pattern_seconds=pattern_seconds,
                metric_windows=metric_windows or ['10s', '1min', '5min'],
                include_levels=include_levels
            )
            
            response = await self.client.GetOrderFlowSnapshot(request)
            
            # Convert to dict format
            snapshot = {
                'ticker': response.ticker,
                'snapshot_time': response.snapshot_time.seconds,
                'quotes': [],
                'metrics': {},
                'patterns': [],
                'latest_quote': None,
            }
            
            # Process quotes
            for proto_quote in response.recent_quotes:
                quote = {
                    'ticker': proto_quote.ticker,
                    'timestamp': int(proto_quote.timestamp.seconds * 1000 + proto_quote.timestamp.nanos // 1000000),
                    'bid_price': proto_quote.bid_price,
                    'bid_size': proto_quote.bid_size,
                    'ask_price': proto_quote.ask_price,
                    'ask_size': proto_quote.ask_size,
                    'mid_price': proto_quote.mid_price,
                    'spread': proto_quote.spread,
                }
                snapshot['quotes'].append(quote)
            
            # Process latest quote
            if response.HasField('latest_quote'):
                snapshot['latest_quote'] = {
                    'ticker': response.latest_quote.ticker,
                    'timestamp': int(response.latest_quote.timestamp.seconds * 1000 + response.latest_quote.timestamp.nanos // 1000000),
                    'bid_price': response.latest_quote.bid_price,
                    'bid_size': response.latest_quote.bid_size,
                    'ask_price': response.latest_quote.ask_price,
                    'ask_size': response.latest_quote.ask_size,
                    'mid_price': response.latest_quote.mid_price,
                    'spread': response.latest_quote.spread,
                }
            
            # Process metrics
            for window, proto_metrics in response.metrics.items():
                metrics = {
                    'ticker': proto_metrics.ticker,
                    'window': proto_metrics.window,
                    'behaviors': dict(proto_metrics.behaviors),
                }
                
                if proto_metrics.HasField('momentum'):
                    metrics.update({
                        'bid_price_movement': proto_metrics.momentum.bid_price_movement,
                        'ask_price_movement': proto_metrics.momentum.ask_price_movement,
                        'bid_lift_count': proto_metrics.momentum.bid_lift_count,
                        'bid_drop_count': proto_metrics.momentum.bid_drop_count,
                        'ask_lift_count': proto_metrics.momentum.ask_lift_count,
                        'ask_drop_count': proto_metrics.momentum.ask_drop_count,
                        'net_bid_size_change': proto_metrics.momentum.net_bid_size_change,
                        'net_ask_size_change': proto_metrics.momentum.net_ask_size_change,
                    })
                
                if proto_metrics.HasField('size_dynamics'):
                    metrics.update({
                        'large_bids_appeared': proto_metrics.size_dynamics.large_bids_appeared,
                        'large_asks_appeared': proto_metrics.size_dynamics.large_asks_appeared,
                        'avg_bid_size': proto_metrics.size_dynamics.avg_bid_size,
                        'avg_ask_size': proto_metrics.size_dynamics.avg_ask_size,
                        'bid_size_acceleration': proto_metrics.size_dynamics.bid_size_acceleration,
                        'ask_size_acceleration': proto_metrics.size_dynamics.ask_size_acceleration,
                    })
                
                snapshot['metrics'][window] = metrics
            
            # Process patterns
            for proto_pattern in response.patterns:
                pattern = {
                    'type': proto_pattern.type,
                    'timestamp': int(proto_pattern.timestamp.seconds * 1000 + proto_pattern.timestamp.nanos // 1000000),
                    'subtype': proto_pattern.subtype,
                    'strength': proto_pattern.strength,
                    'direction': proto_pattern.direction,
                    'price': proto_pattern.price,
                    'description': proto_pattern.description,
                }
                snapshot['patterns'].append(pattern)
            
            # Process levels
            if response.HasField('levels'):
                levels = {'bid': [], 'ask': []}
                
                for proto_level in response.levels.bid_levels:
                    levels['bid'].append({
                        'price': proto_level.price,
                        'appearances': proto_level.appearances,
                        'total_size': proto_level.total_size,
                        'score': proto_level.score,
                    })
                
                for proto_level in response.levels.ask_levels:
                    levels['ask'].append({
                        'price': proto_level.price,
                        'appearances': proto_level.appearances,
                        'total_size': proto_level.total_size,
                        'score': proto_level.score,
                    })
                
                snapshot['levels'] = levels
            
            logger.debug(f"Retrieved complete snapshot for {ticker}")
            return snapshot
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting snapshot for {ticker}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting snapshot for {ticker}: {e}")
            return {}
    
    async def ping(self) -> bool:
        """Test gRPC connection"""
        try:
            await self._ensure_connection()
            await self._health_check()
            return True
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return False
    
    async def close(self):
        """Close gRPC connection"""
        if self.channel:
            await self.channel.close()
            self.channel = None
            self.client = None


# Compatibility wrapper for existing interface
class OrderFlowRedisClient(GRPCDataBrokerClient):
    """gRPC-based client that maintains Redis client interface"""
    
    def __init__(self, *args, **kwargs):
        # Extract gRPC-specific options
        server_url = kwargs.get('server_url') or os.getenv('DATA_BROKER_GRPC_URL', 'localhost:9090')
        
        super().__init__(server_url=server_url)
        
        # Create event loop for sync methods
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
    
    def _run_async(self, coro):
        """Run async coroutine in sync context"""
        try:
            if self.loop.is_running():
                # If loop is already running, we can't use run_until_complete
                # This is a limitation - in a real async environment, this should be avoided
                logger.warning("Event loop already running - async operation may not complete properly")
                return asyncio.create_task(coro)
            else:
                return self.loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"Error running async gRPC method: {e}")
            raise
    
    # Sync wrappers for compatibility
    def get_recent_quotes(self, ticker: str, seconds: int = 300) -> List[Dict[str, Any]]:
        return self._run_async(super().get_recent_quotes(ticker, seconds))
    
    def get_latest_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        # Use the snapshot method for efficiency
        snapshot = self._run_async(super().get_order_flow_snapshot(ticker, quote_seconds=10))
        return snapshot.get('latest_quote')
    
    def get_current_metrics(self, ticker: str, window: str) -> Dict[str, Any]:
        return self._run_async(super().get_current_metrics(ticker, window))
    
    def get_significant_levels(self, ticker: str) -> Dict[str, List[Dict[str, Any]]]:
        return self._run_async(super().get_significant_levels(ticker, 5))
    
    def get_recent_patterns(self, ticker: str, seconds: int = 300) -> List[Dict[str, Any]]:
        return self._run_async(super().get_recent_patterns(ticker, seconds))
    
    def ping(self) -> bool:
        return self._run_async(super().ping())
    
    def close(self):
        self._run_async(super().close())
    
    # Write operations not supported via gRPC client (read-only)
    def save_metrics(self, *args, **kwargs):
        logger.warning("Write operations not supported via gRPC client")
        
    def save_pattern(self, *args, **kwargs):
        logger.warning("Write operations not supported via gRPC client")
        
    def save_significant_level(self, *args, **kwargs):
        logger.warning("Write operations not supported via gRPC client")