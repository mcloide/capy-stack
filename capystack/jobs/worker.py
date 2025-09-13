"""
RQ worker for CapyStack.

This module provides the entry point for the RQ background worker process
that handles deployment tasks and other background operations.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

import sys
import os
from jobs.tasks import start_worker
from core.logging import setup_logging

if __name__ == '__main__':
    # Set up logging
    setup_logging()
    
    # Start worker
    start_worker()
