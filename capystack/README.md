# CapyStack

A lightweight Python CI/CD web application for deploying applications from Git repositories via a browser interface.

## Features

- **Simple Deployment**: Select a branch, tag, or release and deploy with one click
- **Live Progress**: Watch deployment progress with real-time logs via Server-Sent Events
- **Multiple Auth Modes**: None, Basic Auth, or OAuth (GitHub, GitLab, OIDC)
- **Database Support**: PostgreSQL or MySQL with encrypted secrets storage
- **Background Processing**: RQ-based job queue for reliable deployment execution
- **Git Integration**: Support for GitHub, GitLab, and generic Git repositories
- **Retention Policy**: Automatic cleanup of old deployments
- **Modern UI**: Bootstrap-based responsive web interface

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and configure**:
   ```bash
   git clone <repository-url>
   cd capystack
   cp env.example .env
   ```

2. **Edit `.env` file** with your configuration:
   ```bash
   # Required settings
   REPO_URL=https://github.com/your-org/your-repo.git
   GIT_AUTH_TOKEN=your_github_token
   PROJECT_NAME=Your App Name
   
   # Security (change these!)
   SECRET_KEY=your_secret_key_here
   FERNET_KEY=your_32_byte_encryption_key_here
   ```

3. **Start the services**:
   ```bash
   docker-compose up -d
   ```

4. **Initialize the database**:
   ```bash
   docker-compose exec web alembic upgrade head
   ```

5. **Access the application**:
   Open http://localhost:5000 in your browser

### Manual Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up database**:
   - Install PostgreSQL or MySQL
   - Create a database named `capystack`
   - Update `DATABASE_URL` in your `.env` file

3. **Set up Redis**:
   - Install and start Redis server
   - Update `REDIS_URL` in your `.env` file

4. **Initialize database**:
   ```bash
   alembic upgrade head
   ```

5. **Start the application**:
   ```bash
   # Terminal 1: Web application
   python app.py
   
   # Terminal 2: Background worker
   python jobs/worker.py
   ```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `APP_NAME` | Application name | CapyStack | No |
| `SECRET_KEY` | Flask secret key | Generated | Yes |
| `FERNET_KEY` | Encryption key for secrets | Generated | Yes |
| `AUTH_MODE` | Authentication mode | none | No |
| `DATABASE_URL` | Database connection string | - | Yes |
| `REDIS_URL` | Redis connection string | - | Yes |
| `REPO_URL` | Git repository URL | - | Yes |
| `GIT_AUTH_TOKEN` | Git authentication token | - | Yes |
| `PROJECT_NAME` | Project name | My App | No |
| `RUNNER_TYPE` | Runner type (local/docker) | local | No |

### Authentication Modes

#### None (Development Only)
```bash
AUTH_MODE=none
```

#### Basic Authentication
```bash
AUTH_MODE=basic
BASIC_USERNAME=admin
BASIC_PASSWORD_HASH=pbkdf2:sha256:260000$salt$hash
```

#### OAuth Authentication
```bash
AUTH_MODE=oauth
OAUTH_PROVIDER=github  # or gitlab, oidc
OAUTH_CLIENT_ID=your_client_id
OAUTH_CLIENT_SECRET=your_client_secret
OAUTH_REDIRECT_URL=https://yourapp.com/oauth/callback
```

## Deployment Pipeline

CapyStack runs deployments through the following steps:

1. **Preflight**: Validate configuration and check resources
2. **Checkout**: Clone the repository at the specified reference
3. **Build**: Run build commands (if configured)
4. **Deploy**: Execute deployment commands
5. **Post-deploy**: Run post-deployment tasks (if configured)
6. **Finalize**: Clean up and update status

### Configuration File

Create a `capystack.yml` file in your repository root:

```yaml
version: 1
runner: local  # or docker:image: "python:3.12-slim"

env:
  - KEY_FROM_SECRET  # resolved from database

steps:
  build:
    - make build
    - npm run build
  
  deploy:
    - ./deploy.sh --env=$ENV --ref=$CAPY_REF
  
  post_deploy:
    - curl -XPOST $WEBHOOK_URL -d "{\"status\":\"$CAPY_STATUS\"}"
```

## API Endpoints

### Web Interface
- `GET /` - Dashboard
- `GET /deploy/new` - New deployment form
- `GET /deployments/<id>` - Deployment details
- `GET /settings` - Settings page

### API
- `POST /api/deploy` - Start deployment
- `POST /api/deployments/<id>/cancel` - Cancel deployment
- `GET /api/refs/branches` - List branches
- `GET /api/refs/tags` - List tags
- `GET /api/refs/releases` - List releases
- `GET /deployments/<id>/stream` - Live logs (SSE)
- `GET /healthz` - Health check

## Development

### Project Structure
```
capystack/
├── app.py                 # Main Flask application
├── auth/                  # Authentication modules
├── web/                   # Web templates and static files
├── api/                   # API endpoints
├── core/                  # Core functionality
├── db/                    # Database models and session
├── jobs/                  # Background worker tasks
├── migrations/            # Database migrations
└── tests/                 # Test files
```

### Running Tests
```bash
python -m pytest tests/
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Security

- Secrets are encrypted at rest using Fernet encryption
- Sensitive values are masked in the web interface
- Per-deployment workspaces with restricted permissions
- Optional Docker runner for process isolation
- Configurable authentication modes

## Monitoring

- Health check endpoint at `/healthz`
- Structured JSON logging
- Real-time deployment progress via SSE
- Audit trail for all actions

## Troubleshooting

### Common Issues

1. **Database connection errors**:
   - Check `DATABASE_URL` format
   - Ensure database server is running
   - Verify credentials and permissions

2. **Redis connection errors**:
   - Check `REDIS_URL` format
   - Ensure Redis server is running
   - Verify network connectivity

3. **Git authentication errors**:
   - Verify `GIT_AUTH_TOKEN` is valid
   - Check token permissions (read access to repository)
   - Ensure repository URL is correct

4. **Deployment failures**:
   - Check deployment logs in the web interface
   - Verify `capystack.yml` syntax
   - Ensure build/deploy commands exist and are executable

### Logs

- Application logs: Check Docker logs or console output
- Deployment logs: Available in the web interface
- Database logs: Check PostgreSQL/MySQL logs
- Redis logs: Check Redis server logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section
- Review the logs for error messages
- Open an issue on GitHub
