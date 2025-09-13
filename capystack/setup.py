#!/usr/bin/env python3
"""
CapyStack Setup CLI.

Interactive setup tool to generate .env configuration file using Rich.
This tool guides users through the initial configuration process with
secure defaults and validation.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

import os
import secrets
import base64
import hashlib
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich import print as rprint


console = Console()


def generate_secret_key():
    """Generate a secure Flask secret key."""
    return secrets.token_urlsafe(32)


def generate_fernet_key():
    """Generate a secure Fernet encryption key."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def hash_password(password):
    """Hash password using PBKDF2."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"pbkdf2:sha256:100000${salt}${hash_obj.hex()}"


def validate_repo_url(url):
    """Validate repository URL format."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        if parsed.scheme not in ['http', 'https', 'git']:
            return False
        return True
    except:
        return False


def show_welcome():
    """Display welcome message."""
    welcome_text = """
[bold blue]🚀 CapyStack Setup[/bold blue]

[dim]This tool will help you create a .env configuration file for CapyStack.
The setup process will guide you through all necessary configuration options
with secure defaults and validation.[/dim]
"""
    console.print(Panel(welcome_text, title="Welcome", border_style="blue"))


def show_configuration_summary(config):
    """Display configuration summary before writing."""
    table = Table(title="Configuration Summary", show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    
    # Core settings
    table.add_row("App Name", config['app_name'])
    table.add_row("Flask Environment", config['flask_env'])
    table.add_row("Authentication", config['auth_mode'])
    
    if config['auth_mode'] == 'basic':
        table.add_row("Basic Username", config['basic_username'])
        table.add_row("Basic Password", "[dim]••••••••[/dim]")
    elif config['auth_mode'] == 'oauth':
        table.add_row("OAuth Provider", config['oauth_provider'])
        table.add_row("OAuth Client ID", config['oauth_client_id'])
    
    table.add_row("Database", config['db_vendor'])
    table.add_row("Git Provider", config['git_provider'])
    table.add_row("Repository", config['repo_url'])
    table.add_row("Default Branch", config['default_branch'])
    table.add_row("Runner Type", config['runner_type'])
    table.add_row("Work Directory", config['work_dir'])
    table.add_row("Retain Deployments", str(config['retain_deployments']))
    
    console.print(table)


def main():
    """Main setup function."""
    show_welcome()
    
    # Check if .env already exists
    env_file = Path('.env')
    if env_file.exists():
        console.print("\n[yellow]⚠️  .env file already exists![/yellow]")
        if not Confirm.ask("Do you want to overwrite it?", default=False):
            console.print("[red]Setup cancelled.[/red]")
            return
    
    config = {}
    
    # Core settings
    console.print("\n[bold cyan]🔧 Core Settings[/bold cyan]")
    config['app_name'] = Prompt.ask("Application name", default="CapyStack")
    config['flask_env'] = Prompt.ask(
        "Flask environment", 
        choices=["development", "production", "testing"],
        default="development"
    )
    
    # Security settings
    console.print("\n[bold cyan]🔐 Security Settings[/bold cyan]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating secure keys...", total=None)
        config['secret_key'] = generate_secret_key()
        config['fernet_key'] = generate_fernet_key()
        progress.update(task, description="✅ Keys generated successfully")
    
    # Authentication
    console.print("\n[bold cyan]🔑 Authentication[/bold cyan]")
    config['auth_mode'] = Prompt.ask(
        "Authentication mode",
        choices=["none", "basic", "oauth"],
        default="none"
    )
    
    if config['auth_mode'] == 'basic':
        config['basic_username'] = Prompt.ask("Basic auth username", default="admin")
        config['basic_password'] = Prompt.ask("Basic auth password", password=True)
        config['basic_password_hash'] = hash_password(config['basic_password'])
        console.print("[green]✅ Password hashed securely[/green]")
    elif config['auth_mode'] == 'oauth':
        config['oauth_provider'] = Prompt.ask(
            "OAuth provider",
            choices=["github", "gitlab", "oidc"],
            default="github"
        )
        config['oauth_client_id'] = Prompt.ask("OAuth client ID")
        config['oauth_client_secret'] = Prompt.ask("OAuth client secret", password=True)
        config['oauth_redirect_url'] = Prompt.ask(
            "OAuth redirect URL",
            default="http://localhost:5000/oauth/callback"
        )
    
    # Database settings
    console.print("\n[bold cyan]🗄️  Database Settings[/bold cyan]")
    config['db_vendor'] = Prompt.ask(
        "Database vendor",
        choices=["postgres", "mysql"],
        default="postgres"
    )
    
    if config['db_vendor'] == 'postgres':
        default_db_url = "postgresql+psycopg://capystack:capystack@127.0.0.1:5432/capystack"
    else:
        default_db_url = "mysql+pymysql://capystack:capystack@localhost:3306/capystack"
    
    config['database_url'] = Prompt.ask("Database URL", default=default_db_url)
    
    # Redis settings
    console.print("\n[bold cyan]📡 Redis Settings[/bold cyan]")
    config['redis_url'] = Prompt.ask("Redis URL", default="redis://127.0.0.1:6379/0")
    
    # Project settings
    console.print("\n[bold cyan]📁 Project Settings[/bold cyan]")
    config['project_name'] = Prompt.ask("Project name", default="My App")
    config['git_provider'] = Prompt.ask(
        "Git provider",
        choices=["github", "gitlab", "generic"],
        default="github"
    )
    
    # Repository URL with validation
    while True:
        repo_url = Prompt.ask("Repository URL")
        if validate_repo_url(repo_url):
            config['repo_url'] = repo_url
            break
        else:
            console.print("[red]❌ Invalid repository URL. Please try again.[/red]")
    
    config['git_auth_token'] = Prompt.ask("Git authentication token", password=True)
    config['default_branch'] = Prompt.ask("Default branch", default="main")
    
    # Runner settings
    console.print("\n[bold cyan]⚙️  Runner Settings[/bold cyan]")
    config['runner_type'] = Prompt.ask(
        "Runner type",
        choices=["local", "docker"],
        default="local"
    )
    config['work_dir'] = Prompt.ask("Work directory", default="/tmp/capystack/runs")
    config['retain_deployments'] = IntPrompt.ask("Retain deployments count", default=10)
    
    # Show configuration summary
    console.print("\n[bold cyan]📋 Configuration Summary[/bold cyan]")
    show_configuration_summary(config)
    
    if not Confirm.ask("\nDo you want to create the .env file with these settings?", default=True):
        console.print("[red]Setup cancelled.[/red]")
        return
    
    # Generate .env file
    console.print("\n[bold cyan]📝 Generating .env file...[/bold cyan]")
    
    env_content = f"""# CapyStack Configuration
# Generated by setup.py

# Core
APP_NAME={config['app_name']}
FLASK_ENV={config['flask_env']}
SECRET_KEY={config['secret_key']}
FERNET_KEY={config['fernet_key']}

# Auth
AUTH_MODE={config['auth_mode']}"""
    
    if config['auth_mode'] == 'basic':
        env_content += f"""
BASIC_USERNAME={config['basic_username']}
BASIC_PASSWORD_HASH={config['basic_password_hash']}"""
    
    if config['auth_mode'] == 'oauth':
        env_content += f"""

# OAuth
OAUTH_PROVIDER={config['oauth_provider']}
OAUTH_CLIENT_ID={config['oauth_client_id']}
OAUTH_CLIENT_SECRET={config['oauth_client_secret']}
OAUTH_REDIRECT_URL={config['oauth_redirect_url']}"""
    
    env_content += f"""

# Database
DB_VENDOR={config['db_vendor']}
DATABASE_URL={config['database_url']}

# Redis
REDIS_URL={config['redis_url']}

# Project
PROJECT_NAME={config['project_name']}
GIT_PROVIDER={config['git_provider']}
REPO_URL={config['repo_url']}
GIT_AUTH_TOKEN={config['git_auth_token']}
DEFAULT_BRANCH={config['default_branch']}

# Runner
RUNNER_TYPE={config['runner_type']}
WORK_DIR={config['work_dir']}
RETAIN_DEPLOYMENTS={config['retain_deployments']}
"""
    
    # Write .env file
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        console.print("[green]✅ .env file created successfully![/green]")
    except Exception as e:
        console.print(f"[red]❌ Error creating .env file: {e}[/red]")
        return
    
    # Next steps
    next_steps = """
[bold green]🎉 Setup Complete![/bold green]

[bold cyan]Next steps:[/bold cyan]
1. Review your .env file and adjust settings if needed
2. Start the database and Redis services
3. Run database migrations:
   [dim]docker-compose exec web alembic upgrade head[/dim]
   [dim]# or manually: alembic upgrade head[/dim]
4. Start CapyStack:
   [dim]docker-compose up -d[/dim]
   [dim]# or manually: python app.py[/dim]
5. Access the application at [bold]http://localhost:5000[/bold]

[bold cyan]📚 For more information, see README.md[/bold cyan]
"""
    
    console.print(Panel(next_steps, title="Setup Complete", border_style="green"))
    
    # Security reminder
    if config['auth_mode'] == 'none':
        security_warning = """
[bold yellow]⚠️  Security Reminder:[/bold yellow]

You're using AUTH_MODE=none which is not recommended for production!
Consider switching to 'basic' or 'oauth' for production use.
"""
        console.print(Panel(security_warning, title="Security Warning", border_style="yellow"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Setup failed: {e}[/red]")
        console.print("[dim]Please check your input and try again.[/dim]")