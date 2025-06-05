"""Redis client for order flow data"""

import json
import time
import logging
import os
from typing import Dict, List, Any, Optional
import redis
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderFlowRedisClient:
    """Redis client for order flow data operations"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
        decode_responses: bool = True
    ):
        """Initialize Redis client with connection parameters"""
        self.host = host or os.getenv('REDIS_HOST', 'localhost')
        self.port = port or int(os.getenv('REDIS_PORT', 6379))
        self.db = db or int(os.getenv('REDIS_DB', 0))
        self.password = password or os.getenv('REDIS_PASSWORD')
        
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=decode_responses,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def get_recent_quotes(self, ticker: str, seconds: int = 300) -> List[Dict[str, Any]]:
        """Get recent quotes for a ticker within specified time window"""
        key = f"orderflow:quotes:{ticker}"
        
        # Calculate time range
        current_time = time.time() * 1000
        start_time = current_time - (seconds * 1000)
        
        try:
            # Get quotes from sorted set
            results = self.redis_client.zrangebyscore(
                key,
                start_time,
                current_time
            )
            
            # Parse JSON quotes
            quotes = []
            for result in results:
                try:
                    quote = json.loads(result)
                    quotes.append(quote)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse quote: {result}")
                    
            return quotes
            
        except Exception as e:
            logger.error(f"Error getting recent quotes for {ticker}: {e}")
            return []

    def get_latest_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get the latest quote for a ticker"""
        key = f"orderflow:latest:{ticker}"
        
        try:
            quote_data = self.redis_client.hgetall(key)
            
            if quote_data:
                # Convert string values back to proper types
                for field in ['bid_price', 'ask_price', 'mid_price', 'spread']:
                    if field in quote_data:
                        quote_data[field] = float(quote_data[field])
                        
                for field in ['bid_size', 'ask_size', 'timestamp']:
                    if field in quote_data:
                        quote_data[field] = int(quote_data[field])
                        
                return quote_data
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest quote for {ticker}: {e}")
            return None

    def get_current_metrics(self, ticker: str, window: str) -> Dict[str, Any]:
        """Get current metrics for a specific time window"""
        key = f"orderflow:metrics:{ticker}:{window}"
        
        try:
            metrics = self.redis_client.hgetall(key)
            
            if not metrics:
                return {}
                
            # Convert string values to appropriate types
            for field in ['bid_price_movement', 'ask_price_movement']:
                if field in metrics:
                    metrics[field] = float(metrics[field])
                    
            for field in ['bid_lift_count', 'bid_drop_count', 'ask_lift_count', 'ask_drop_count',
                         'net_bid_size_change', 'net_ask_size_change', 'large_bids_appeared',
                         'large_asks_appeared', 'avg_bid_size', 'avg_ask_size']:
                if field in metrics:
                    metrics[field] = int(metrics[field])
                    
            # Parse behaviors if present
            if 'behaviors' in metrics:
                try:
                    metrics['behaviors'] = json.loads(metrics['behaviors'])
                except:
                    metrics['behaviors'] = {}
                    
            # Parse last_sweep if present
            if 'last_sweep' in metrics:
                try:
                    metrics['last_sweep'] = json.loads(metrics['last_sweep'])
                except:
                    metrics['last_sweep'] = None
                    
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting metrics for {ticker}:{window}: {e}")
            return {}

    def get_significant_levels(self, ticker: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get significant price levels (support/resistance)"""
        bid_key = f"orderflow:levels:{ticker}:bid"
        ask_key = f"orderflow:levels:{ticker}:ask"
        
        try:
            levels = {'bid': [], 'ask': []}
            
            # Get bid levels
            bid_levels = self.redis_client.zrevrange(bid_key, 0, 10, withscores=True)
            for level_data, score in bid_levels:
                try:
                    level = json.loads(level_data)
                    level['score'] = score
                    levels['bid'].append(level)
                except:
                    pass
                    
            # Get ask levels
            ask_levels = self.redis_client.zrevrange(ask_key, 0, 10, withscores=True)
            for level_data, score in ask_levels:
                try:
                    level = json.loads(level_data)
                    level['score'] = score
                    levels['ask'].append(level)
                except:
                    pass
                    
            return levels
            
        except Exception as e:
            logger.error(f"Error getting significant levels for {ticker}: {e}")
            return {'bid': [], 'ask': []}

    def get_recent_patterns(self, ticker: str, seconds: int = 300) -> List[Dict[str, Any]]:
        """Get recent detected patterns"""
        key = f"orderflow:patterns:{ticker}"
        
        # Calculate time range
        current_time = time.time()
        start_time = current_time - seconds
        
        try:
            # Get patterns from sorted set
            results = self.redis_client.zrangebyscore(
                key,
                start_time,
                current_time
            )
            
            # Parse patterns
            patterns = []
            for result in results:
                try:
                    pattern = json.loads(result)
                    patterns.append(pattern)
                except:
                    pass
                    
            return patterns
            
        except Exception as e:
            logger.error(f"Error getting patterns for {ticker}: {e}")
            return []

    def save_metrics(self, ticker: str, window: str, metrics: Dict[str, Any], ttl: int = 300):
        """Save metrics to Redis"""
        key = f"orderflow:metrics:{ticker}:{window}"
        
        try:
            # Convert complex types to JSON strings
            if 'behaviors' in metrics:
                metrics['behaviors'] = json.dumps(metrics['behaviors'])
            if 'last_sweep' in metrics:
                metrics['last_sweep'] = json.dumps(metrics['last_sweep'])
                
            # Save to Redis
            self.redis_client.hset(key, mapping=metrics)
            self.redis_client.expire(key, ttl)
            
        except Exception as e:
            logger.error(f"Error saving metrics for {ticker}:{window}: {e}")

    def save_pattern(self, ticker: str, pattern: Dict[str, Any], ttl: int = 3600):
        """Save detected pattern"""
        key = f"orderflow:patterns:{ticker}"
        
        try:
            # Add timestamp if not present
            if 'timestamp' not in pattern:
                pattern['timestamp'] = time.time() * 1000  # Use milliseconds
                
            # Save to sorted set (score should be in seconds for TTL)
            score = pattern['timestamp'] / 1000 if pattern['timestamp'] > 1e10 else pattern['timestamp']
            self.redis_client.zadd(
                key,
                {json.dumps(pattern): score}
            )
            
            # Trim old patterns
            cutoff_time = time.time() - ttl
            self.redis_client.zremrangebyscore(key, '-inf', cutoff_time)
            
        except Exception as e:
            logger.error(f"Error saving pattern for {ticker}: {e}")

    def save_significant_level(self, ticker: str, side: str, level_data: Dict[str, Any]):
        """Save significant price level"""
        key = f"orderflow:levels:{ticker}:{side}"
        
        try:
            score = level_data.get('total_size', 0) * level_data.get('appearances', 1)
            
            self.redis_client.zadd(
                key,
                {json.dumps(level_data): score}
            )
            
            # Keep only top 20 levels
            self.redis_client.zremrangebyrank(key, 0, -21)
            
            # Set expiry
            self.redis_client.expire(key, 3600)
            
        except Exception as e:
            logger.error(f"Error saving level for {ticker}:{side}: {e}")

    def ping(self) -> bool:
        """Test Redis connection"""
        try:
            return self.redis_client.ping()
        except:
            return False
            
    def close(self):
        """Close Redis connection"""
        if hasattr(self, 'redis_client'):
            try:
                self.redis_client.close()
            except:
                pass
