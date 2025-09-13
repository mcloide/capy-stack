"""
Configuration management for CapyStack.

This module handles all configuration settings for the CapyStack application,
including environment variable loading, validation, and default values.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

import os
import secrets
import base64
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration class."""
    
    # Core settings
    APP_NAME = os.getenv('APP_NAME', 'CapyStack')
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    # Encryption
    FERNET_KEY = os.getenv('FERNET_KEY')
    if not FERNET_KEY:
        # Generate a new key if not provided
        FERNET_KEY = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    
    # Database
    DB_VENDOR = os.getenv('DB_VENDOR', 'postgres')
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg://capystack:capystack@127.0.0.1:5432/capystack')
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
    
    # Authentication
    AUTH_MODE = os.getenv('AUTH_MODE', 'none')  # none | basic | oauth
    BASIC_USERNAME = os.getenv('BASIC_USERNAME', 'admin')
    BASIC_PASSWORD_HASH = os.getenv('BASIC_PASSWORD_HASH')
    
    # OAuth
    OAUTH_PROVIDER = os.getenv('OAUTH_PROVIDER', 'github')
    OAUTH_CLIENT_ID = os.getenv('OAUTH_CLIENT_ID')
    OAUTH_CLIENT_SECRET = os.getenv('OAUTH_CLIENT_SECRET')
    OAUTH_REDIRECT_URL = os.getenv('OAUTH_REDIRECT_URL')
    OIDC_ISSUER_URL = os.getenv('OIDC_ISSUER_URL')
    OIDC_SCOPES = os.getenv('OIDC_SCOPES', 'openid email profile')
    
    # Project settings
    PROJECT_NAME = os.getenv('PROJECT_NAME', 'My App')
    GIT_PROVIDER = os.getenv('GIT_PROVIDER', 'github')
    REPO_URL = os.getenv('REPO_URL')
    GIT_AUTH_TOKEN = os.getenv('GIT_AUTH_TOKEN')
    DEFAULT_BRANCH = os.getenv('DEFAULT_BRANCH', 'main')
    
    # Runner settings
    RUNNER_TYPE = os.getenv('RUNNER_TYPE', 'local')
    WORK_DIR = os.getenv('WORK_DIR', '/tmp/capystack/runs')
    RETAIN_DEPLOYMENTS = int(os.getenv('RETAIN_DEPLOYMENTS', '10'))
    
    # Flask settings
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # i18n
    WEGLOT_KEY = os.getenv('WEGLOT_KEY')
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if cls.AUTH_MODE not in ['none', 'basic', 'oauth']:
            errors.append(f"Invalid AUTH_MODE: {cls.AUTH_MODE}")
        
        if cls.AUTH_MODE == 'basic' and not cls.BASIC_PASSWORD_HASH:
            errors.append("BASIC_PASSWORD_HASH required when AUTH_MODE=basic")
        
        if cls.AUTH_MODE == 'oauth':
            if not cls.OAUTH_CLIENT_ID:
                errors.append("OAUTH_CLIENT_ID required when AUTH_MODE=oauth")
            if not cls.OAUTH_CLIENT_SECRET:
                errors.append("OAUTH_CLIENT_SECRET required when AUTH_MODE=oauth")
            if not cls.OAUTH_REDIRECT_URL:
                errors.append("OAUTH_REDIRECT_URL required when AUTH_MODE=oauth")
        
        if cls.DB_VENDOR not in ['postgres', 'mysql']:
            errors.append(f"Invalid DB_VENDOR: {cls.DB_VENDOR}")
        
        if not cls.REPO_URL:
            errors.append("REPO_URL is required")
        
        if cls.RUNNER_TYPE not in ['local', 'docker']:
            errors.append(f"Invalid RUNNER_TYPE: {cls.RUNNER_TYPE}")
        
        return errors


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL


def get_config() -> Config:
    """Get configuration based on environment."""
    env = os.getenv('FLASK_ENV', 'development')
    
    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()
