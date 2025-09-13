# CapyStack

A lightweight Python CI/CD web application for deploying applications from Git repositories via a browser interface.

## 🚀 Key Features Implemented

### 🔐 Authentication System
- **None mode** (development)
- **Basic authentication** with configurable credentials
- **OAuth** (GitHub, GitLab, OIDC) with full provider support

### 🗄️ Database Support
- **PostgreSQL and MySQL** support with unified configuration
- **Encrypted secrets storage** using Fernet encryption
- **Alembic migrations** for database schema management
- **Complete data model** with users, projects, deployments, and audit trails

### 🚀 Deployment Pipeline
- **Preflight checks** for validation and resource verification
- **Git checkout** with support for branches, tags, and releases
- **Build steps** with configurable commands
- **Deploy execution** with customizable deployment scripts
- **Post-deployment tasks** for notifications and cleanup
- **Live progress tracking** with real-time status updates

### 🎨 Modern Web Interface
- **Bootstrap 5 responsive design** with mobile support
- **Real-time logs** via Server-Sent Events
- **Interactive deployment management** with cancel/retry capabilities
- **Settings and health monitoring** with system status

### ⚙️ Background Processing
- **RQ job queue** for reliable background task execution
- **Redis pub/sub** for live log streaming
- **Worker process management** with automatic restart

### 🔗 Git Integration
- **GitHub API integration** with full branch/tag/release support
- **GitLab API integration** with project management
- **Generic Git support** using git CLI commands
- **Branch/tag/release listing** with caching and pagination

## ✅ Ready to Use

The application is production-ready with:

- **Docker Compose setup** for easy deployment
- **Comprehensive documentation** in README.md
- **Environment configuration** with validation
- **Security features** (encrypted secrets, auth modes)
- **Health monitoring** and error handling
- **Retention policies** for deployment cleanup

## 🚀 Quick Start

### Option 1: Development Setup (Recommended for local development)
```bash
cd capystack
./setup-dev.sh
```
This script will:
- Create a Python virtual environment
- Install all dependencies
- Create helpful activation scripts
- Guide you through the next steps

Then run the configuration setup:
```bash
source venv/bin/activate  # or ./activate-dev.sh
python setup.py
```

### Option 2: Interactive Setup (Docker/Production)
```bash
cd capystack
python setup.py
```
The setup script will guide you through creating your `.env` file with:
- Automatic generation of secure keys
- Interactive prompts for all configuration options
- Validation of inputs
- Default values for development setup

### Option 3: Manual Configuration
```bash
cd capystack
cp env.example .env
# Edit .env with your settings
```

### Start with Docker:
```bash
docker-compose up -d
docker-compose exec web alembic upgrade head
```

### Access the application:
Open http://localhost:5000

The project follows all specifications and is ready for immediate use. All components are properly integrated and the codebase is well-structured for future enhancements.

## 📁 Project Structure

capystack/
├── app.py                    # Main Flask application
├── run.py                    # Startup script
├── setup.py                  # Interactive setup CLI
├── setup-dev.sh              # Development environment setup
├── requirements.txt          # Python dependencies
├── Dockerfile               # Docker configuration
├── docker-compose.yml       # Multi-service setup
├── alembic.ini              # Database migration config
├── env.example              # Environment variables template
├── capystack.yml.example     # Deployment config template
├── README.md                # Comprehensive documentation
├── auth/                    # Authentication system
│   ├── __init__.py          # Auth decorators and utilities
│   └── oauth.py             # OAuth providers (GitHub, GitLab, OIDC)
├── web/                     # Web interface
│   ├── templates/           # Jinja2 templates
│   │   ├── base.html        # Base template
│   │   ├── dashboard.html   # Main dashboard
│   │   ├── new_deployment.html # Deployment form
│   │   ├── deployment_detail.html # Live deployment view
│   │   ├── settings.html    # Configuration view
│   │   └── error.html       # Error pages
│   └── static/              # Static assets
│       ├── css/style.css    # Custom styling
│       ├── js/app.js        # JavaScript functionality
│       └── images/          # Images and icons
│           ├── logo.svg     # CapyStack logo
│           └── favicon.*    # Favicon files
├── api/                     # API endpoints (ready for expansion)
├── core/                    # Core functionality
│   ├── settings.py          # Configuration management
│   ├── secrets.py           # Encrypted secrets handling
│   ├── logging.py           # Structured logging
│   ├── git.py               # Git provider integrations
│   └── runner.py            # Deployment pipeline runner
├── db/                      # Database layer
│   ├── models.py            # SQLAlchemy models
│   └── session.py           # Database session management
├── jobs/                    # Background processing
│   ├── tasks.py             # RQ job definitions
│   └── worker.py            # Worker process
├── migrations/              # Database migrations
│   ├── env.py               # Alembic environment
│   └── script.py.mako       # Migration template
└── tests/                   # Test framework (ready)

