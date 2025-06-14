"""Configuration for MCP Order Flow Server"""

import os
from typing import Optional

# Data source configuration
DATA_SOURCE = os.getenv('DATA_SOURCE', 'grpc')  # 'redis' or 'grpc'

# gRPC Data Broker configuration
DATA_BROKER_GRPC_URL = os.getenv('DATA_BROKER_GRPC_URL', 'localhost:9090')

# Redis configuration (for backward compatibility)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

def get_storage_client():
    """Get the appropriate storage client based on configuration"""
    if DATA_SOURCE == 'redis':
        from storage.redis_client import OrderFlowRedisClient
        return OrderFlowRedisClient(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD
        )
    else:  # Default to gRPC
        from storage.grpc_client import OrderFlowRedisClient
        return OrderFlowRedisClient(
            server_url=DATA_BROKER_GRPC_URL
        )