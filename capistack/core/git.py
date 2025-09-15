"""
Git integration for CapiStack.

This module provides Git repository integration including support for GitHub,
GitLab, and generic Git repositories with API-based and CLI-based operations.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

import requests
import subprocess
import tempfile
import os
from typing import List, Dict, Optional
from capistack.core.settings import get_config
from capistack.core.logging import get_logger

config = get_config()
logger = get_logger(__name__)


class GitProvider:
    """Base class for Git providers."""
    
    def __init__(self, repo_url: str, auth_token: Optional[str] = None):
        self.repo_url = repo_url
        self.auth_token = auth_token
    
    def get_branches(self) -> List[Dict[str, str]]:
        """Get list of branches."""
        raise NotImplementedError
    
    def get_tags(self) -> List[Dict[str, str]]:
        """Get list of tags."""
        raise NotImplementedError
    
    def get_releases(self) -> List[Dict[str, str]]:
        """Get list of releases."""
        raise NotImplementedError
    
    def get_commit_sha(self, ref: str) -> Optional[str]:
        """Get commit SHA for a reference."""
        raise NotImplementedError


class GitHubProvider(GitProvider):
    """GitHub Git provider."""
    
    def __init__(self, repo_url: str, auth_token: Optional[str] = None):
        super().__init__(repo_url, auth_token)
        self.owner, self.repo = self._parse_repo_url()
        self.api_base = 'https://api.github.com'
    
    def _parse_repo_url(self) -> tuple:
        """Parse GitHub repo URL to extract owner and repo name."""
        # Handle both https://github.com/owner/repo.git and https://github.com/owner/repo
        url = self.repo_url.rstrip('/')
        if url.endswith('.git'):
            url = url[:-4]
        
        parts = url.split('/')
        if len(parts) >= 2:
            return parts[-2], parts[-1]
        raise ValueError(f"Invalid GitHub repo URL: {self.repo_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers with authentication."""
        headers = {'Accept': 'application/vnd.github.v3+json'}
        if self.auth_token:
            headers['Authorization'] = f'token {self.auth_token}'
        return headers
    
    def get_branches(self) -> List[Dict[str, str]]:
        """Get list of branches from GitHub API."""
        try:
            url = f'{self.api_base}/repos/{self.owner}/{self.repo}/branches'
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            branches = []
            for branch in response.json():
                branches.append({
                    'name': branch['name'],
                    'sha': branch['commit']['sha'],
                    'protected': branch.get('protected', False)
                })
            
            return branches
        except Exception as e:
            logger.error(f"Failed to fetch branches from GitHub: {e}")
            return []
    
    def get_tags(self) -> List[Dict[str, str]]:
        """Get list of tags from GitHub API."""
        try:
            url = f'{self.api_base}/repos/{self.owner}/{self.repo}/tags'
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            tags = []
            for tag in response.json():
                tags.append({
                    'name': tag['name'],
                    'sha': tag['commit']['sha']
                })
            
            return tags
        except Exception as e:
            logger.error(f"Failed to fetch tags from GitHub: {e}")
            return []
    
    def get_releases(self) -> List[Dict[str, str]]:
        """Get list of releases from GitHub API."""
        try:
            url = f'{self.api_base}/repos/{self.owner}/{self.repo}/releases'
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            releases = []
            for release in response.json():
                releases.append({
                    'name': release['tag_name'],
                    'title': release['name'],
                    'sha': release['target_commitish'],
                    'draft': release['draft'],
                    'prerelease': release['prerelease']
                })
            
            return releases
        except Exception as e:
            logger.error(f"Failed to fetch releases from GitHub: {e}")
            return []
    
    def get_commit_sha(self, ref: str) -> Optional[str]:
        """Get commit SHA for a reference."""
        try:
            url = f'{self.api_base}/repos/{self.owner}/{self.repo}/commits/{ref}'
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            return response.json()['sha']
        except Exception as e:
            logger.error(f"Failed to get commit SHA for {ref}: {e}")
            return None


class GitLabProvider(GitProvider):
    """GitLab Git provider."""
    
    def __init__(self, repo_url: str, auth_token: Optional[str] = None):
        super().__init__(repo_url, auth_token)
        self.project_id = self._parse_project_id()
        self.api_base = 'https://gitlab.com/api/v4'  # Could be configurable
    
    def _parse_project_id(self) -> str:
        """Parse GitLab repo URL to extract project ID."""
        # This is simplified - GitLab project IDs can be numeric or path-based
        url = self.repo_url.rstrip('/')
        if url.endswith('.git'):
            url = url[:-4]
        
        # Extract the project path
        parts = url.split('/')
        if len(parts) >= 2:
            return '/'.join(parts[-2:])
        raise ValueError(f"Invalid GitLab repo URL: {self.repo_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers with authentication."""
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        return headers
    
    def get_branches(self) -> List[Dict[str, str]]:
        """Get list of branches from GitLab API."""
        try:
            url = f'{self.api_base}/projects/{self.project_id}/repository/branches'
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            branches = []
            for branch in response.json():
                branches.append({
                    'name': branch['name'],
                    'sha': branch['commit']['id'],
                    'protected': branch.get('protected', False)
                })
            
            return branches
        except Exception as e:
            logger.error(f"Failed to fetch branches from GitLab: {e}")
            return []
    
    def get_tags(self) -> List[Dict[str, str]]:
        """Get list of tags from GitLab API."""
        try:
            url = f'{self.api_base}/projects/{self.project_id}/repository/tags'
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            tags = []
            for tag in response.json():
                tags.append({
                    'name': tag['name'],
                    'sha': tag['commit']['id']
                })
            
            return tags
        except Exception as e:
            logger.error(f"Failed to fetch tags from GitLab: {e}")
            return []
    
    def get_releases(self) -> List[Dict[str, str]]:
        """Get list of releases from GitLab API."""
        try:
            url = f'{self.api_base}/projects/{self.project_id}/releases'
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            releases = []
            for release in response.json():
                releases.append({
                    'name': release['tag_name'],
                    'title': release['name'],
                    'sha': release['commit']['id'],
                    'draft': False,  # GitLab doesn't have draft releases
                    'prerelease': False
                })
            
            return releases
        except Exception as e:
            logger.error(f"Failed to fetch releases from GitLab: {e}")
            return []
    
    def get_commit_sha(self, ref: str) -> Optional[str]:
        """Get commit SHA for a reference."""
        try:
            url = f'{self.api_base}/projects/{self.project_id}/repository/commits/{ref}'
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            return response.json()['id']
        except Exception as e:
            logger.error(f"Failed to get commit SHA for {ref}: {e}")
            return None


class GenericGitProvider(GitProvider):
    """Generic Git provider using git CLI."""
    
    def get_branches(self) -> List[Dict[str, str]]:
        """Get list of branches using git ls-remote."""
        try:
            cmd = ['git', 'ls-remote', '--heads', self.repo_url]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            branches = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    sha, ref = line.split('\t')
                    branch_name = ref.replace('refs/heads/', '')
                    branches.append({
                        'name': branch_name,
                        'sha': sha,
                        'protected': False
                    })
            
            return branches
        except Exception as e:
            logger.error(f"Failed to fetch branches using git ls-remote: {e}")
            return []
    
    def get_tags(self) -> List[Dict[str, str]]:
        """Get list of tags using git ls-remote."""
        try:
            cmd = ['git', 'ls-remote', '--tags', self.repo_url]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            tags = []
            for line in result.stdout.strip().split('\n'):
                if line and not line.endswith('^{}'):  # Skip dereferenced tags
                    sha, ref = line.split('\t')
                    tag_name = ref.replace('refs/tags/', '')
                    tags.append({
                        'name': tag_name,
                        'sha': sha
                    })
            
            return tags
        except Exception as e:
            logger.error(f"Failed to fetch tags using git ls-remote: {e}")
            return []
    
    def get_releases(self) -> List[Dict[str, str]]:
        """Generic provider doesn't support releases - return tags as releases."""
        tags = self.get_tags()
        releases = []
        for tag in tags:
            releases.append({
                'name': tag['name'],
                'title': tag['name'],
                'sha': tag['sha'],
                'draft': False,
                'prerelease': False
            })
        return releases
    
    def get_commit_sha(self, ref: str) -> Optional[str]:
        """Get commit SHA using git ls-remote."""
        try:
            cmd = ['git', 'ls-remote', self.repo_url, ref]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.stdout.strip():
                sha, _ = result.stdout.strip().split('\t')
                return sha
            return None
        except Exception as e:
            logger.error(f"Failed to get commit SHA for {ref}: {e}")
            return None


def get_git_provider(repo_url: str, provider: str = None, auth_token: str = None) -> GitProvider:
    """Get appropriate Git provider based on configuration."""
    if provider is None:
        provider = config.GIT_PROVIDER
    
    if auth_token is None:
        auth_token = config.GIT_AUTH_TOKEN
    
    if provider == 'github':
        return GitHubProvider(repo_url, auth_token)
    elif provider == 'gitlab':
        return GitLabProvider(repo_url, auth_token)
    elif provider == 'generic':
        return GenericGitProvider(repo_url, auth_token)
    else:
        raise ValueError(f"Unsupported Git provider: {provider}")


def clone_repository(repo_url: str, target_dir: str, ref: str = None, auth_token: str = None) -> bool:
    """Clone repository to target directory."""
    try:
        # Prepare git command
        cmd = ['git', 'clone', '--depth', '1']
        
        if ref:
            cmd.extend(['--branch', ref])
        
        # Add authentication if provided
        if auth_token:
            # Replace https:// with https://token@ for authentication
            if repo_url.startswith('https://'):
                repo_url = repo_url.replace('https://', f'https://{auth_token}@')
            elif repo_url.startswith('http://'):
                repo_url = repo_url.replace('http://', f'http://{auth_token}@')
        
        cmd.extend([repo_url, target_dir])
        
        # Execute clone
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Successfully cloned repository to {target_dir}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone repository: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during clone: {e}")
        return False
