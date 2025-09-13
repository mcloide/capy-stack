"""
OAuth authentication implementation for CapyStack.

This module provides OAuth authentication support for GitHub, GitLab, and generic
OIDC providers with secure token handling and user session management.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

import secrets
import requests
from urllib.parse import urlencode, parse_qs, urlparse
from flask import request, session, redirect, url_for, flash, current_app
from core.settings import get_config

config = get_config()


class OAuthProvider:
    """Base OAuth provider class."""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.client_id = config.OAUTH_CLIENT_ID
        self.client_secret = config.OAUTH_CLIENT_SECRET
        self.redirect_uri = config.OAUTH_REDIRECT_URL
    
    def get_authorization_url(self) -> str:
        """Get OAuth authorization URL."""
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': state,
            'response_type': 'code',
            'scope': self.get_scope()
        }
        
        return f"{self.get_auth_url()}?{urlencode(params)}"
    
    def get_scope(self) -> str:
        """Get OAuth scope."""
        return 'read:user user:email'
    
    def get_auth_url(self) -> str:
        """Get authorization URL."""
        raise NotImplementedError
    
    def get_token_url(self) -> str:
        """Get token URL."""
        raise NotImplementedError
    
    def get_user_info_url(self) -> str:
        """Get user info URL."""
        raise NotImplementedError
    
    def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        
        response = requests.post(self.get_token_url(), data=data)
        response.raise_for_status()
        
        return response.json()
    
    def get_user_info(self, access_token: str) -> dict:
        """Get user information from provider."""
        headers = {'Authorization': f'token {access_token}'}
        response = requests.get(self.get_user_info_url(), headers=headers)
        response.raise_for_status()
        
        return response.json()


class GitHubOAuth(OAuthProvider):
    """GitHub OAuth provider."""
    
    def __init__(self):
        super().__init__('github')
    
    def get_auth_url(self) -> str:
        return 'https://github.com/login/oauth/authorize'
    
    def get_token_url(self) -> str:
        return 'https://github.com/login/oauth/access_token'
    
    def get_user_info_url(self) -> str:
        return 'https://api.github.com/user'
    
    def get_scope(self) -> str:
        return 'read:user user:email'


class GitLabOAuth(OAuthProvider):
    """GitLab OAuth provider."""
    
    def __init__(self):
        super().__init__('gitlab')
        self.base_url = 'https://gitlab.com'  # Could be configurable
    
    def get_auth_url(self) -> str:
        return f'{self.base_url}/oauth/authorize'
    
    def get_token_url(self) -> str:
        return f'{self.base_url}/oauth/token'
    
    def get_user_info_url(self) -> str:
        return f'{self.base_url}/api/v4/user'
    
    def get_scope(self) -> str:
        return 'read_user'


class OIDCOAuth(OAuthProvider):
    """Generic OIDC OAuth provider."""
    
    def __init__(self):
        super().__init__('oidc')
        self.issuer_url = config.OIDC_ISSUER_URL
        self.scopes = config.OIDC_SCOPES.split()
        self._discovery_doc = None
    
    def get_discovery_document(self) -> dict:
        """Get OIDC discovery document."""
        if not self._discovery_doc:
            response = requests.get(f'{self.issuer_url}/.well-known/openid_configuration')
            response.raise_for_status()
            self._discovery_doc = response.json()
        return self._discovery_doc
    
    def get_auth_url(self) -> str:
        doc = self.get_discovery_document()
        return doc['authorization_endpoint']
    
    def get_token_url(self) -> str:
        doc = self.get_discovery_document()
        return doc['token_endpoint']
    
    def get_user_info_url(self) -> str:
        doc = self.get_discovery_document()
        return doc['userinfo_endpoint']
    
    def get_scope(self) -> str:
        return ' '.join(self.scopes)
    
    def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        
        response = requests.post(self.get_token_url(), data=data)
        response.raise_for_status()
        
        return response.json()
    
    def get_user_info(self, access_token: str) -> dict:
        """Get user information from provider."""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(self.get_user_info_url(), headers=headers)
        response.raise_for_status()
        
        return response.json()


def get_oauth_provider() -> OAuthProvider:
    """Get OAuth provider based on configuration."""
    provider_name = config.OAUTH_PROVIDER.lower()
    
    if provider_name == 'github':
        return GitHubOAuth()
    elif provider_name == 'gitlab':
        return GitLabOAuth()
    elif provider_name == 'oidc':
        return OIDCOAuth()
    else:
        raise ValueError(f"Unsupported OAuth provider: {provider_name}")


def handle_oauth_callback():
    """Handle OAuth callback."""
    # Verify state parameter
    state = request.args.get('state')
    if not state or state != session.get('oauth_state'):
        flash('Invalid OAuth state parameter', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Get authorization code
    code = request.args.get('code')
    if not code:
        flash('Authorization code not provided', 'error')
        return redirect(url_for('web.dashboard'))
    
    try:
        provider = get_oauth_provider()
        
        # Exchange code for token
        token_data = provider.exchange_code_for_token(code)
        access_token = token_data.get('access_token')
        
        if not access_token:
            flash('Failed to obtain access token', 'error')
            return redirect(url_for('web.dashboard'))
        
        # Get user info
        user_info = provider.get_user_info(access_token)
        
        # Store user info in session
        session['user_id'] = str(user_info.get('id', user_info.get('sub')))
        session['user_name'] = user_info.get('name', user_info.get('login', user_info.get('preferred_username')))
        session['user_email'] = user_info.get('email')
        session['user_role'] = 'user'  # Default role
        
        # TODO: Store OAuth account in database
        # TODO: Check for admin users/domains
        
        flash('Successfully logged in', 'success')
        return redirect(url_for('web.dashboard'))
        
    except Exception as e:
        current_app.logger.error(f"OAuth callback error: {e}")
        flash('Authentication failed', 'error')
        return redirect(url_for('web.dashboard'))
