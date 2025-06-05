"""Order flow processor - analyzes quotes and detects patterns"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from ..storage.redis_client import OrderFlowRedisClient
from .metrics_calculator import MetricsCalculator
from .pattern_detector import PatternDetector
from .behavior_analyzer import BehaviorAnalyzer

logger = logging.getLogger(__name__)


class OrderFlowProcessor:
    """Processes order flow data for a single ticker"""
    
    def __init__(self, ticker: str, redis_client: OrderFlowRedisClient):
        """Initialize processor"""
        self.ticker = ticker
        self.redis_client = redis_client
        
        # Components
        self.metrics_calculator = MetricsCalculator()
        self.pattern_detector = PatternDetector()
        self.behavior_analyzer = BehaviorAnalyzer()
        
        # State
        self.last_process_time = 0
        self.stats = {
            'process_count': 0,
            'errors': 0,
            'patterns_detected': 0,
            'last_process_time': None
        }
        
        # Price level tracking
        self.price_levels = {
            'bid': {},  # price -> {count, total_size, last_seen}
            'ask': {}   # price -> {count, total_size, last_seen}
        }
        
    def process(self):
        """Main processing method - called every second"""
        start_time = time.time()
        
        try:
            # Get quotes for different time windows
            quotes_10s = self.redis_client.get_recent_quotes(self.ticker, seconds=10)
            quotes_60s = self.redis_client.get_recent_quotes(self.ticker, seconds=60)
            quotes_300s = self.redis_client.get_recent_quotes(self.ticker, seconds=300)
            
            if not quotes_10s:
                logger.debug(f"No quotes for {self.ticker} in last 10s")
                return
                
            # Calculate metrics for each window
            metrics_10s = self._calculate_window_metrics(quotes_10s, "10s")
            metrics_60s = self._calculate_window_metrics(quotes_60s, "1min") if quotes_60s else {}
            metrics_300s = self._calculate_window_metrics(quotes_300s, "5min") if len(quotes_300s) > 100 else {}
            
            # Detect patterns in 60s window
            if quotes_60s:
                patterns = self.pattern_detector.detect_patterns(quotes_60s, metrics_60s)
                for pattern in patterns:
                    self.redis_client.save_pattern(self.ticker, pattern)
                    self.stats['patterns_detected'] += 1
                    
            # Analyze behaviors in 10s window
            behaviors = self.behavior_analyzer.analyze_behaviors(quotes_10s, metrics_10s)
            metrics_10s['behaviors'] = behaviors
            
            # Update price levels
            self._update_price_levels(quotes_10s)
            
            # Save metrics to Redis
            self.redis_client.save_metrics(self.ticker, "10s", metrics_10s, ttl=60)
            self.redis_client.save_metrics(self.ticker, "1min", metrics_60s, ttl=300)
            if metrics_300s:
                self.redis_client.save_metrics(self.ticker, "5min", metrics_300s, ttl=600)
                
            # Update stats
            self.stats['process_count'] += 1
            self.stats['last_process_time'] = datetime.now()
            
            # Log processing time if slow
            process_time = time.time() - start_time
            if process_time > 0.1:  # Log if takes more than 100ms
                logger.warning(f"Slow processing for {self.ticker}: {process_time:.3f}s")
                
        except Exception as e:
            logger.exception(f"Error processing {self.ticker}: {e}")
            self.stats['errors'] += 1
            
    def _calculate_window_metrics(self, quotes: List[Dict[str, Any]], window_name: str) -> Dict[str, Any]:
        """Calculate metrics for a time window"""
        if not quotes:
            return {}
            
        # Calculate basic metrics
        metrics = self.metrics_calculator.calculate_momentum_metrics(quotes)
        
        # Add size dynamics
        size_dynamics = self.metrics_calculator.calculate_size_dynamics(quotes)
        metrics.update(size_dynamics)
        
        # Detect sweeps
        sweep = self.metrics_calculator.detect_sweep(quotes)
        if sweep:
            metrics['last_sweep'] = sweep
            
        return metrics
        
    def _update_price_levels(self, quotes: List[Dict[str, Any]]):
        """Update significant price levels"""
        current_time = time.time()
        
        for quote in quotes:
            bid_price = quote.get('bid_price', 0)
            bid_size = quote.get('bid_size', 0)
            ask_price = quote.get('ask_price', 0)
            ask_size = quote.get('ask_size', 0)
            
            # Track bid levels
            if bid_price > 0 and bid_size > 5000:  # Only track significant sizes
                if bid_price not in self.price_levels['bid']:
                    self.price_levels['bid'][bid_price] = {
                        'count': 0,
                        'total_size': 0,
                        'last_seen': 0
                    }
                    
                level = self.price_levels['bid'][bid_price]
                level['count'] += 1
                level['total_size'] += bid_size
                level['last_seen'] = current_time
                
            # Track ask levels
            if ask_price > 0 and ask_size > 5000:
                if ask_price not in self.price_levels['ask']:
                    self.price_levels['ask'][ask_price] = {
                        'count': 0,
                        'total_size': 0,
                        'last_seen': 0
                    }
                    
                level = self.price_levels['ask'][ask_price]
                level['count'] += 1
                level['total_size'] += ask_size
                level['last_seen'] = current_time
                
        # Clean old levels and save significant ones
        self._clean_and_save_levels(current_time)
        
    def _clean_and_save_levels(self, current_time: float):
        """Clean old price levels and save significant ones"""
        # Clean levels not seen in last 5 minutes
        for side in ['bid', 'ask']:
            levels_to_remove = []
            
            for price, level_data in self.price_levels[side].items():
                if current_time - level_data['last_seen'] > 300:
                    levels_to_remove.append(price)
                elif level_data['count'] >= 3:  # Appeared at least 3 times
                    # Save significant level
                    self.redis_client.save_significant_level(
                        self.ticker,
                        side,
                        {
                            'price': price,
                            'appearances': level_data['count'],
                            'total_size': level_data['total_size'],
                            'avg_size': level_data['total_size'] / level_data['count'],
                            'last_seen': level_data['last_seen']
                        }
                    )
                    
            # Remove old levels
            for price in levels_to_remove:
                del self.price_levels[side][price]
                
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        return self.stats.copy()
        
    def stop(self):
        """Stop the processor"""
        logger.info(f"Stopping processor for {self.ticker}")
        # Any cleanup if needed
