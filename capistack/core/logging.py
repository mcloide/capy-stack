"""
Logging configuration for CapiStack.

This module provides structured logging capabilities including JSON formatting,
deployment-specific loggers, and real-time log streaming via Redis.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any
from capistack.core.settings import get_config

config = get_config()


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields
        if hasattr(record, 'deployment_id'):
            log_entry['deployment_id'] = record.deployment_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


def setup_logging():
    """Set up logging configuration."""
    # Create logger
    logger = logging.getLogger('capistack')
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Set formatter
    if config.FLASK_ENV == 'production':
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Set levels for third-party loggers
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str = 'capistack') -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


class DeploymentLogger:
    """Logger for deployment processes."""
    
    def __init__(self, deployment_id: str, redis_client=None):
        self.deployment_id = deployment_id
        self.redis_client = redis_client
        self.logger = get_logger(f'deployment.{deployment_id}')
    
    def log(self, level: str, message: str, step: str = None, **kwargs):
        """Log a message for the deployment."""
        # Add deployment context to the log record
        extra = {
            'deployment_id': self.deployment_id,
            'step': step,
            **kwargs
        }
        
        # Log to standard logger
        getattr(self.logger, level.lower())(message, extra=extra)
        
        # Publish to Redis for real-time streaming
        if self.redis_client:
            log_event = {
                'deployment_id': self.deployment_id,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'level': level.upper(),
                'step': step,
                'message': message,
                **kwargs
            }
            
            channel = f'capistack.logs.{self.deployment_id}'
            self.redis_client.publish(channel, json.dumps(log_event))
    
    def info(self, message: str, step: str = None, **kwargs):
        """Log info message."""
        self.log('info', message, step, **kwargs)
    
    def warning(self, message: str, step: str = None, **kwargs):
        """Log warning message."""
        self.log('warning', message, step, **kwargs)
    
    def error(self, message: str, step: str = None, **kwargs):
        """Log error message."""
        self.log('error', message, step, **kwargs)
    
    def debug(self, message: str, step: str = None, **kwargs):
        """Log debug message."""
        self.log('debug', message, step, **kwargs)
