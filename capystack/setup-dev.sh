#!/bin/bash

# CapyStack Development Setup Script
# This script creates a virtual environment and installs dependencies

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3 is available
check_python() {
    print_status "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Found Python $PYTHON_VERSION"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
        if [[ $PYTHON_VERSION == 3.* ]]; then
            PYTHON_CMD="python"
            print_success "Found Python $PYTHON_VERSION"
        else
            print_error "Python 3 is required. Found Python $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
}

# Check if pip is available
check_pip() {
    print_status "Checking pip installation..."
    
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
    else
        print_error "pip is not installed. Please install pip."
        exit 1
    fi
    
    print_success "Found pip"
}

# Check system dependencies
check_system_deps() {
    print_status "Checking system dependencies..."
    
    # Check for PostgreSQL development headers (common issue on macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! command -v pg_config &> /dev/null; then
            print_warning "PostgreSQL development headers not found."
            print_status "To install PostgreSQL on macOS:"
            print_status "  brew install postgresql"
            print_status "  # or install PostgreSQL.app from https://postgresapp.com/"
            echo ""
        fi
    fi
    
    # Check for Redis
    if ! command -v redis-server &> /dev/null; then
        print_warning "Redis not found in PATH."
        print_status "To install Redis:"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            print_status "  brew install redis"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            print_status "  sudo apt-get install redis-server  # Ubuntu/Debian"
            print_status "  sudo yum install redis             # CentOS/RHEL"
        fi
        echo ""
    fi
}

# Create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment 'venv' already exists."
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Removing existing virtual environment..."
            rm -rf venv
        else
            print_status "Using existing virtual environment."
            return 0
        fi
    fi
    
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created successfully"
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_success "Virtual environment activated"
    else
        print_error "Failed to activate virtual environment. venv/bin/activate not found."
        exit 1
    fi
}

# Upgrade pip
upgrade_pip() {
    print_status "Upgrading pip..."
    pip install --upgrade pip
    print_success "pip upgraded successfully"
}

# Install requirements
install_requirements() {
    print_status "Installing requirements..."
    
    if [ -f "requirements.txt" ]; then
        # Try to install requirements
        if pip install -r requirements.txt; then
            print_success "Requirements installed successfully"
        else
            print_warning "Some packages failed to install. This might be due to missing system dependencies."
            
            # Try development requirements as fallback
            if [ -f "requirements-dev.txt" ]; then
                print_status "Trying development requirements (without database drivers)..."
                if pip install -r requirements-dev.txt; then
                    print_success "Development requirements installed successfully"
                    print_warning "Database drivers not installed. You may need to install them separately:"
                    print_status "  pip install psycopg2-binary  # for PostgreSQL"
                    print_status "  pip install PyMySQL         # for MySQL"
                else
                    print_error "Failed to install even development requirements"
                    exit 1
                fi
            else
                print_status "Attempting to install core packages individually..."
                
                # Install core packages that should work
                pip install "Flask>=3.0.0" "SQLAlchemy>=2.0.0" "Alembic>=1.13.0"
                pip install "redis>=5.0.0" "rq>=1.15.0" "cryptography>=41.0.0"
                pip install "requests>=2.31.0" "httpx>=0.25.0" "GitPython>=3.1.0"
                pip install "python-dotenv>=1.0.0" "Werkzeug>=3.0.0" "Jinja2>=3.1.0"
                pip install "gunicorn>=21.0.0" "rich>=13.0.0"
                
                # Try database drivers separately
                print_status "Installing database drivers..."
                if ! pip install psycopg2-binary>=2.9.0; then
                    print_warning "psycopg2-binary failed. Trying alternative installation..."
                    if command -v brew &> /dev/null; then
                        print_status "Installing PostgreSQL via Homebrew (if not already installed)..."
                        brew install postgresql || true
                    fi
                    pip install psycopg2>=2.9.0 || print_warning "PostgreSQL driver installation failed"
                fi
                
                pip install "PyMySQL>=1.1.0" || print_warning "MySQL driver installation failed"
                
                print_success "Core requirements installed (some optional packages may have failed)"
            fi
        fi
    else
        print_error "requirements.txt not found in current directory"
        exit 1
    fi
}

# Create activation script
create_activation_script() {
    print_status "Creating activation script..."
    
    cat > activate-dev.sh << 'EOF'
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
EOF
    
    chmod +x activate-dev.sh
    print_success "Activation script created: ./activate-dev.sh"
}

# Main execution
main() {
    echo "🚀 CapyStack Development Setup"
    echo "=============================="
    echo ""
    
    # Check prerequisites
    check_python
    check_pip
    check_system_deps
    
    # Setup virtual environment
    create_venv
    activate_venv
    upgrade_pip
    install_requirements
    
    # Create helpful scripts
    create_activation_script
    
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Activate the virtual environment:"
    echo "   source venv/bin/activate"
    echo "   # or use: ./activate-dev.sh"
    echo ""
    echo "2. Run the setup wizard:"
    echo "   python setup.py"
    echo ""
    echo "3. Start the application:"
    echo "   python app.py"
    echo ""
    echo "📚 For more information, see README.md"
}

# Run main function
main "$@"
