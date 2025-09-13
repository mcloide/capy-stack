#!/usr/bin/env python3
"""
CapyStack startup script.

This script provides a convenient way to start different components of CapyStack
including the web application, background worker, and database migrations.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python run.py [web|worker|migrate]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "web":
        # Start web application
        os.system("python app.py")
    elif command == "worker":
        # Start background worker
        os.system("python jobs/worker.py")
    elif command == "migrate":
        # Run database migrations
        os.system("alembic upgrade head")
    elif command == "init":
        # Initialize database
        print("Initializing database...")
        os.system("alembic upgrade head")
        print("Database initialized successfully!")
    else:
        print(f"Unknown command: {command}")
        print("Available commands: web, worker, migrate, init")
        sys.exit(1)

if __name__ == "__main__":
    main()
