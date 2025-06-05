"""Background processor service that runs continuously"""

import asyncio
import logging
import time
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..storage.redis_client import OrderFlowRedisClient
from ..processors.order_flow_processor import OrderFlowProcessor

logger = logging.getLogger(__name__)


class ProcessorService:
    """Background service that processes order flow data continuously"""
    
    def __init__(self):
        """Initialize processor service"""
        self.running = False
        self.processors = {}
        self.redis_client = None
        self.process_interval = int(os.getenv('PROCESSOR_INTERVAL', 1))  # seconds
        self._task = None
        
    async def start(self):
        """Start the processor service"""
        if self.running:
            logger.warning("Processor service already running")
            return
            
        logger.info("Starting processor service")
        self.running = True
        
        # Initialize Redis client
        try:
            self.redis_client = OrderFlowRedisClient()
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Processor service will not run without Redis")
            self.running = False
            return
            
        # Start processing loop
        self._task = asyncio.create_task(self._process_loop())
        logger.info("Processor service started")
        
    async def stop(self):
        """Stop the processor service"""
        logger.info("Stopping processor service")
        self.running = False
        
        # Cancel processing task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
        # Stop all processors
        for ticker, processor in self.processors.items():
            try:
                processor.stop()
            except Exception as e:
                logger.error(f"Error stopping processor for {ticker}: {e}")
                
        # Close Redis connection
        if self.redis_client:
            self.redis_client.close()
            
        logger.info("Processor service stopped")
        
    async def _process_loop(self):
        """Main processing loop"""
        logger.info(f"Processing loop started (interval: {self.process_interval}s)")
        
        while self.running:
            try:
                # Get active tickers from Redis
                active_tickers = await self._get_active_tickers()
                
                # Process each ticker
                for ticker in active_tickers:
                    try:
                        await self._process_ticker(ticker)
                    except Exception as e:
                        logger.error(f"Error processing {ticker}: {e}")
                        
                # Sleep before next iteration
                await asyncio.sleep(self.process_interval)
                
            except asyncio.CancelledError:
                logger.info("Processing loop cancelled")
                break
            except Exception as e:
                logger.exception(f"Error in processing loop: {e}")
                await asyncio.sleep(self.process_interval)
                
    async def _get_active_tickers(self) -> List[str]:
        """Get list of active tickers from Redis"""
        try:
            # Get all quote keys
            keys = []
            cursor = 0
            
            while True:
                cursor, batch = self.redis_client.redis_client.scan(
                    cursor, 
                    match="orderflow:quotes:*",
                    count=100
                )
                keys.extend(batch)
                
                if cursor == 0:
                    break
                    
            # Extract tickers from keys
            tickers = []
            for key in keys:
                parts = key.split(':')
                if len(parts) >= 3:
                    ticker = parts[2]
                    if ticker not in tickers:
                        tickers.append(ticker)
                        
            return tickers
            
        except Exception as e:
            logger.error(f"Error getting active tickers: {e}")
            return []
            
    async def _process_ticker(self, ticker: str):
        """Process a single ticker"""
        # Get or create processor
        if ticker not in self.processors:
            logger.info(f"Creating processor for {ticker}")
            self.processors[ticker] = OrderFlowProcessor(ticker, self.redis_client)
            
        processor = self.processors[ticker]
        
        # Run processing
        try:
            # This is synchronous but fast (< 100ms typically)
            processor.process()
            
        except Exception as e:
            logger.error(f"Error in processor for {ticker}: {e}")
            
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        status = {
            'running': self.running,
            'process_interval': self.process_interval,
            'active_tickers': list(self.processors.keys()),
            'redis_connected': self.redis_client.ping() if self.redis_client else False
        }
        
        # Add processor stats
        processor_stats = {}
        for ticker, processor in self.processors.items():
            processor_stats[ticker] = processor.get_stats()
            
        status['processors'] = processor_stats
        
        return status
