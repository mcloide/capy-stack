"""
Authentication module for CapiStack.

This module provides authentication decorators and utilities for different
authentication modes including none, basic, and OAuth.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

from functools import wraps
from flask import request, session, redirect, url_for, flash, Response
from werkzeug.security import check_password_hash
from capistack.core.settings import get_config
from capistack.db.session import get_db
from capistack.db.models import User, OAuthAccount
import uuid

config = get_config()


def require_auth(f):
    """Decorator to require authentication based on AUTH_MODE."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if config.AUTH_MODE == 'none':
            return f(*args, **kwargs)
        
        if config.AUTH_MODE == 'basic':
            return require_basic_auth(f)(*args, **kwargs)
        
        if config.AUTH_MODE == 'oauth':
            return require_oauth_auth(f)(*args, **kwargs)
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_basic_auth(f):
    """Decorator for basic authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        
        if not auth or not check_basic_credentials(auth.username, auth.password):
            return Response(
                'Authentication required',
                401,
                {'WWW-Authenticate': 'Basic realm="CapiStack"'}
            )
        
        # Store user info in session
        session['user_id'] = str(uuid.uuid4())  # For basic auth, use a dummy UUID
        session['user_name'] = auth.username
        session['user_role'] = 'admin'
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_oauth_auth(f):
    """Decorator for OAuth authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    
    return decorated_function


def check_basic_credentials(username: str, password: str) -> bool:
    """Check basic authentication credentials."""
    if username != config.BASIC_USERNAME:
        return False
    
    if not config.BASIC_PASSWORD_HASH:
        return False
    
    return check_password_hash(config.BASIC_PASSWORD_HASH, password)


def get_current_user():
    """Get current user from session."""
    if config.AUTH_MODE == 'none':
        return {
            'id': str(uuid.uuid4()),
            'name': 'Anonymous',
            'email': 'anonymous@capistack.local',
            'role': 'admin'
        }
    
    if 'user_id' not in session:
        return None
    
    if config.AUTH_MODE == 'basic':
        return {
            'id': session.get('user_id'),
            'name': session.get('user_name'),
            'email': f"{session.get('user_name')}@capistack.local",
            'role': session.get('user_role', 'admin')
        }
    
    # For OAuth, we'd fetch from database
    # This is a simplified version
    return {
        'id': session.get('user_id'),
        'name': session.get('user_name'),
        'email': session.get('user_email'),
        'role': session.get('user_role', 'user')
    }


def logout():
    """Logout current user."""
    session.clear()
