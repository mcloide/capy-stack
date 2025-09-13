"""
Main Flask application for CapyStack.

This module provides the main Flask web application with all routes, middleware,
and application configuration for the CapyStack CI/CD platform.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path
from core.settings import get_config
from core.logging import setup_logging, get_logger
from db.session import init_db, get_db
from db.models import Deployment, DeploymentStep, Project, Secret, User
from auth import require_auth, get_current_user, logout
from auth.oauth import handle_oauth_callback
from jobs.tasks import run_deployment, cancel_deployment, deployment_queue
from core.git import get_git_provider
from core.secrets import secrets_manager
import redis
import json


BASE_DIR = Path(__file__).resolve().parent

# Set up logging
setup_logging()
logger = get_logger(__name__)

# Get configuration
config = get_config()

# Validate configuration
config_errors = config.validate()
if config_errors:
    logger.error(f"Configuration errors: {config_errors}")
    raise ValueError(f"Configuration errors: {config_errors}")

# Create Flask app
app = Flask(
    __name__, 
    template_folder=str(BASE_DIR / "web" / "templates"),
    static_folder=str(BASE_DIR / "web" / "static"),
    static_url_path="/static",
)
app.config['SECRET_KEY'] = config.SECRET_KEY

# Initialize database
init_db()

# Redis connection for SSE
redis_client = redis.from_url(config.REDIS_URL)


@app.before_request
def before_request():
    """Set up request context."""
    # Get current user
    app.current_user = get_current_user()


@app.route('/')
@require_auth
def dashboard():
    """Dashboard page."""
    db = next(get_db())
    try:
        # Get project
        project = db.query(Project).first()
        if not project:
            # Create default project if none exists
            project = Project(
                id=uuid.uuid4(),
                name=config.PROJECT_NAME,
                repo_url=config.REPO_URL,
                git_provider=config.GIT_PROVIDER,
                default_branch=config.DEFAULT_BRANCH,
                runner_type=config.RUNNER_TYPE
            )
            db.add(project)
            db.commit()
        
        # Get recent deployments
        deployments = db.query(Deployment).filter(
            Deployment.project_id == project.id
        ).order_by(Deployment.created_at.desc()).limit(10).all()
        
        return render_template('dashboard.html', 
                             project=project, 
                             deployments=deployments,
                             current_user=app.current_user,
                             auth_mode=config.AUTH_MODE,
                             weglot_key=config.WEGLOT_KEY)
    
    finally:
        db.close()


@app.route('/deploy/new')
@require_auth
def new_deployment():
    """New deployment page."""
    db = next(get_db())
    project = db.query(Project).first()
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('dashboard'))
    return render_template('new_deployment.html', current_user=app.current_user, project=project)


@app.route('/deployments/<deployment_id>')
@require_auth
def deployment_detail(deployment_id):
    """Deployment detail page."""
    db = next(get_db())
    try:
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            flash('Deployment not found', 'error')
            return redirect(url_for('dashboard'))
        
        steps = db.query(DeploymentStep).filter(
            DeploymentStep.deployment_id == deployment_id
        ).order_by(DeploymentStep.started_at).all()
        
        return render_template('deployment_detail.html',
                             deployment=deployment,
                             steps=steps,
                             current_user=app.current_user)
    
    finally:
        db.close()


@app.route('/deployments/<deployment_id>/stream')
@require_auth
def deployment_stream(deployment_id):
    """Server-Sent Events stream for deployment logs."""
    def generate():
        pubsub = redis_client.pubsub()
        channel = f'capystack.logs.{deployment_id}'
        pubsub.subscribe(channel)
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield f"data: {message['data'].decode()}\n\n"
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            pubsub.close()
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/deploy', methods=['POST'])
@require_auth
def start_deployment():
    """Start a new deployment."""
    data = request.get_json()
    ref_type = data.get('ref_type')
    ref_name = data.get('ref_name')
    
    if not ref_type or not ref_name:
        return jsonify({'error': 'ref_type and ref_name are required'}), 400
    
    db = next(get_db())
    try:
        # Get project
        project = db.query(Project).first()
        if not project:
            return jsonify({'error': 'No project configured'}), 400
        
        # Create deployment record
        deployment = Deployment(
            id=uuid.uuid4(),
            project_id=project.id,
            user_id=app.current_user['id'] if app.current_user else None,
            ref_type=ref_type,
            ref_name=ref_name,
            status='queued'
        )
        db.add(deployment)
        db.commit()
        
        # Queue deployment job
        job = deployment_queue.enqueue(
            run_deployment,
            str(deployment.id),
            str(project.id),
            ref_type,
            ref_name,
            app.current_user['id'] if app.current_user else None,
            job_id=str(deployment.id)
        )
        
        logger.info(f"Queued deployment {deployment.id}")
        
        return jsonify({
            'deployment_id': str(deployment.id),
            'status': 'queued',
            'redirect_url': url_for('deployment_detail', deployment_id=deployment.id)
        })
    
    except Exception as e:
        logger.error(f"Failed to start deployment: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/deployments/<deployment_id>/cancel', methods=['POST'])
@require_auth
def cancel_deployment_api(deployment_id):
    """Cancel a deployment."""
    try:
        success = cancel_deployment(deployment_id)
        if success:
            return jsonify({'status': 'canceled'})
        else:
            return jsonify({'error': 'Failed to cancel deployment'}), 400
    except Exception as e:
        logger.error(f"Failed to cancel deployment: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/refs/branches')
@require_auth
def get_branches():
    """Get list of branches."""
    try:
        provider = get_git_provider(config.REPO_URL, config.GIT_PROVIDER, config.GIT_AUTH_TOKEN)
        branches = provider.get_branches()
        return jsonify(branches)
    except Exception as e:
        logger.error(f"Failed to get branches: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/refs/tags')
@require_auth
def get_tags():
    """Get list of tags."""
    try:
        provider = get_git_provider(config.REPO_URL, config.GIT_PROVIDER, config.GIT_AUTH_TOKEN)
        tags = provider.get_tags()
        return jsonify(tags)
    except Exception as e:
        logger.error(f"Failed to get tags: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/refs/releases')
@require_auth
def get_releases():
    """Get list of releases."""
    try:
        provider = get_git_provider(config.REPO_URL, config.GIT_PROVIDER, config.GIT_AUTH_TOKEN)
        releases = provider.get_releases()
        return jsonify(releases)
    except Exception as e:
        logger.error(f"Failed to get releases: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/settings')
@require_auth
def settings():
    """Settings page (read-only)."""
    # Mask sensitive values
    masked_config = {
        'APP_NAME': config.APP_NAME,
        'AUTH_MODE': config.AUTH_MODE,
        'GIT_PROVIDER': config.GIT_PROVIDER,
        'REPO_URL': config.REPO_URL,
        'DEFAULT_BRANCH': config.DEFAULT_BRANCH,
        'RUNNER_TYPE': config.RUNNER_TYPE,
        'RETAIN_DEPLOYMENTS': config.RETAIN_DEPLOYMENTS,
        'SECRET_KEY': '***masked***' if config.SECRET_KEY else None,
        'GIT_AUTH_TOKEN': '***masked***' if config.GIT_AUTH_TOKEN else None,
        'OAUTH_CLIENT_SECRET': '***masked***' if config.OAUTH_CLIENT_SECRET else None,
    }
    
    return render_template('settings.html',
                         config=masked_config,
                         current_user=app.current_user)


@app.route('/login')
def login():
    """Login page."""
    if config.AUTH_MODE == 'none':
        return redirect(url_for('dashboard'))
    
    if config.AUTH_MODE == 'oauth':
        from auth.oauth import get_oauth_provider
        provider = get_oauth_provider()
        auth_url = provider.get_authorization_url()
        return redirect(auth_url)
    
    # For basic auth, the browser will show the auth dialog
    return redirect(url_for('dashboard'))


@app.route('/oauth/callback')
def oauth_callback():
    """OAuth callback handler."""
    return handle_oauth_callback()


@app.route('/logout')
def logout_route():
    """Logout route."""
    logout()
    flash('Logged out successfully', 'info')
    return redirect(url_for('dashboard'))


@app.route('/healthz')
def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        query = text('SELECT 1')
        db = next(get_db())
        db.execute(query)
        db.close()
        
        # Check Redis connection
        redis_client.ping()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.errorhandler(404)
def not_found(error):
    """404 error handler."""
    return render_template('error.html',
                         error_code=404,
                         error_message='Page not found',
                         current_user=app.current_user), 404


@app.errorhandler(500)
def internal_error(error):
    """500 error handler."""
    logger.error(f"Internal server error: {error}")
    return render_template('error.html',
                         error_code=500,
                         error_message='Internal server error',
                         current_user=app.current_user), 500


@app.route('/about')
def about():
    """About page."""
    return render_template('about.html', current_user=app.current_user)


if __name__ == '__main__':
    app.run(debug=config.FLASK_ENV == 'development', host='0.0.0.0', port=5000)
