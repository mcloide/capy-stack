"""
Deployment runner for CapyStack.

This module handles the execution of deployment pipelines including preflight checks,
repository checkout, build steps, deployment execution, and post-deployment tasks.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

import os
import yaml
import subprocess
import tempfile
import shutil
from typing import Dict, List, Optional, Any
from pathlib import Path
from core.settings import get_config
from core.logging import DeploymentLogger
from core.git import clone_repository, get_git_provider

config = get_config()


class DeploymentRunner:
    """Runs deployment pipelines."""
    
    def __init__(self, deployment_id: str, redis_client=None):
        self.deployment_id = deployment_id
        self.redis_client = redis_client
        self.logger = DeploymentLogger(deployment_id, redis_client)
        self.work_dir = Path(config.WORK_DIR) / deployment_id
        self.repo_dir = self.work_dir / 'repo'
        self.config_file = None
        self.config = {}
        self.ref_type = None
        self.ref_name = None
    
    def run_deployment(self, project_id: str, ref_type: str, ref_name: str, 
                      user_id: str, secrets: Dict[str, str] = None) -> bool:
        """Run the complete deployment pipeline."""
        try:
            self.ref_type = ref_type
            self.ref_name = ref_name
            self.logger.info(f"Starting deployment {self.deployment_id}", "preflight")
            
            # Step 1: Preflight checks
            if not self._preflight_checks():
                return False
            
            # Step 2: Checkout
            if not self._checkout_repo(ref_type, ref_name):
                return False
            
            # Step 3: Load configuration
            self._load_configuration()
            
            # Step 4: Environment injection
            self._inject_environment(secrets or {})
            
            # Step 5: Build (if configured)
            if self._should_build():
                if not self._run_build():
                    return False
            
            # Step 6: Deploy
            if not self._run_deploy():
                return False
            
            # Step 7: Post-deploy (if configured)
            if self._should_post_deploy():
                self._run_post_deploy()
            
            # Step 8: Finalize
            self._finalize_deployment()
            
            self.logger.info(f"Deployment {self.deployment_id} completed successfully", "finalize")
            return True
            
        except Exception as e:
            self.logger.error(f"Deployment failed: {e}", "finalize")
            return False
        finally:
            # Cleanup
            self._cleanup()
    
    def _preflight_checks(self) -> bool:
        """Run preflight checks."""
        self.logger.info("Running preflight checks", "preflight")
        
        # Check disk space
        if not self._check_disk_space():
            return False
        
        # Check repository URL
        if not config.REPO_URL:
            self.logger.error("Repository URL not configured", "preflight")
            return False
        
        # Create work directory
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Created work directory: {self.work_dir}", "preflight")
        
        return True
    
    def _checkout_repo(self, ref_type: str, ref_name: str) -> bool:
        """Checkout repository."""
        self.logger.info(f"Checking out {ref_type}: {ref_name}", "checkout")
        
        # Clone repository
        if not clone_repository(config.REPO_URL, str(self.repo_dir), ref_name, config.GIT_AUTH_TOKEN):
            self.logger.error("Failed to clone repository", "checkout")
            return False
        
        # Get commit SHA
        provider = get_git_provider(config.REPO_URL, config.GIT_PROVIDER, config.GIT_AUTH_TOKEN)
        commit_sha = provider.get_commit_sha(ref_name)
        
        if commit_sha:
            self.logger.info(f"Checked out commit: {commit_sha}", "checkout")
        else:
            self.logger.warning("Could not determine commit SHA", "checkout")
        
        return True
    
    def _load_configuration(self):
        """Load capystack.yml configuration if present."""
        config_path = self.repo_dir / 'capystack.yml'
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
                self.logger.info("Loaded capystack.yml configuration", "checkout")
            except Exception as e:
                self.logger.warning(f"Failed to load capystack.yml: {e}", "checkout")
                self.config = {}
        else:
            self.logger.info("No capystack.yml found, using defaults", "checkout")
            self.config = {}
    
    def _inject_environment(self, secrets: Dict[str, str]):
        """Inject environment variables and secrets."""
        self.logger.info("Injecting environment variables", "checkout")
        
        env_file = self.work_dir / '.env'
        with open(env_file, 'w') as f:
            # Add deployment context
            f.write(f"CAPY_DEPLOYMENT_ID={self.deployment_id}\n")
            f.write(f"CAPY_REF_TYPE={self.ref_type}\n")
            f.write(f"CAPY_REF_NAME={self.ref_name}\n")
            f.write(f"CAPY_WORK_DIR={self.work_dir}\n")
            f.write(f"CAPY_REPO_DIR={self.repo_dir}\n")
            f.write(f"CAPY_STATUS=running\n")
            
            # Add secrets
            for key, value in secrets.items():
                f.write(f"{key}={value}\n")
            
            # Add configured environment variables
            if 'env' in self.config:
                for env_var in self.config['env']:
                    if env_var in secrets:
                        f.write(f"{env_var}={secrets[env_var]}\n")
        
        self.logger.info(f"Environment file created: {env_file}", "checkout")
    
    def _should_build(self) -> bool:
        """Check if build step should run."""
        return 'build' in self.config and self.config['build']
    
    def _run_build(self) -> bool:
        """Run build step."""
        self.logger.info("Running build step", "build")
        
        build_commands = self.config.get('build', [])
        if not build_commands:
            self.logger.info("No build commands configured, skipping", "build")
            return True
        
        return self._run_commands(build_commands, "build")
    
    def _run_deploy(self) -> bool:
        """Run deploy step."""
        self.logger.info("Running deploy step", "deploy")
        
        deploy_commands = self.config.get('deploy', [])
        if not deploy_commands:
            # Try to find deploy script
            deploy_script = self.repo_dir / 'deploy.sh'
            if deploy_script.exists():
                deploy_commands = [f"./deploy.sh --env={self.work_dir / '.env'} --ref={self.ref_name}"]
            else:
                self.logger.error("No deploy commands configured and no deploy.sh found", "deploy")
                return False
        
        return self._run_commands(deploy_commands, "deploy")
    
    def _should_post_deploy(self) -> bool:
        """Check if post-deploy step should run."""
        return 'post_deploy' in self.config and self.config['post_deploy']
    
    def _run_post_deploy(self) -> bool:
        """Run post-deploy step."""
        self.logger.info("Running post-deploy step", "post_deploy")
        
        post_deploy_commands = self.config.get('post_deploy', [])
        if not post_deploy_commands:
            self.logger.info("No post-deploy commands configured, skipping", "post_deploy")
            return True
        
        return self._run_commands(post_deploy_commands, "post_deploy")
    
    def _run_commands(self, commands: List[str], step_name: str) -> bool:
        """Run a list of shell commands."""
        for i, command in enumerate(commands):
            self.logger.info(f"Running command {i+1}/{len(commands)}: {command}", step_name)
            
            if not self._run_command(command, step_name):
                self.logger.error(f"Command failed: {command}", step_name)
                return False
        
        return True
    
    def _run_command(self, command: str, step_name: str) -> bool:
        """Run a single shell command."""
        try:
            # Set up environment
            env = os.environ.copy()
            env_file = self.work_dir / '.env'
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.strip().split('=', 1)
                            env[key] = value
            
            # Run command in repository directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.repo_dir,
                env=env,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Log output
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    self.logger.info(f"STDOUT: {line}", step_name)
            
            if result.stderr:
                for line in result.stderr.strip().split('\n'):
                    self.logger.warning(f"STDERR: {line}", step_name)
            
            if result.returncode != 0:
                self.logger.error(f"Command failed with exit code {result.returncode}", step_name)
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}", step_name)
            return False
    
    def _finalize_deployment(self):
        """Finalize deployment."""
        self.logger.info("Finalizing deployment", "finalize")
        
        # Save logs
        logs_path = self.work_dir / 'deployment.log'
        # TODO: Save deployment logs to logs_path
        
        # Save artifacts if any
        artifacts_path = self.work_dir / 'artifacts'
        if artifacts_path.exists():
            self.logger.info(f"Artifacts saved to: {artifacts_path}", "finalize")
        
        self.logger.info("Deployment finalized", "finalize")
    
    def _cleanup(self):
        """Cleanup deployment workspace."""
        try:
            if self.work_dir.exists():
                shutil.rmtree(self.work_dir)
                self.logger.info(f"Cleaned up workspace: {self.work_dir}", "finalize")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup workspace: {e}", "finalize")
    
    def _check_disk_space(self) -> bool:
        """Check available disk space."""
        try:
            statvfs = os.statvfs(self.work_dir.parent if self.work_dir.exists() else '/tmp')
            free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
            
            if free_space_gb < 1.0:  # Require at least 1GB free
                self.logger.error(f"Insufficient disk space: {free_space_gb:.2f}GB available", "preflight")
                return False
            
            self.logger.info(f"Disk space check passed: {free_space_gb:.2f}GB available", "preflight")
            return True
            
        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}", "preflight")
            return True  # Continue if we can't check
