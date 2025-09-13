#!/bin/bash
# CapyStack Development Environment Activation Script

echo "🚀 Activating CapyStack development environment..."

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
    echo "📦 Available commands:"
    echo "   python app.py          # Start web application"
    echo "   python jobs/worker.py  # Start background worker"
    echo "   python setup.py        # Run setup wizard"
    echo "   python run.py [cmd]    # Run with command (web/worker/migrate)"
    echo "   alembic upgrade head   # Run database migrations"
    echo ""
    echo "🌐 Access the application at: http://localhost:5000"
    echo "📚 See README.md for more information"
else
    echo "❌ Virtual environment not found. Run ./setup-dev.sh first."
    exit 1
fi
