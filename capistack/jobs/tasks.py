"""
Background tasks for CapiStack.

This module defines RQ background tasks for deployment execution, cancellation,
and cleanup operations with proper error handling and logging.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

import redis
from rq import Worker, Queue, connections
from capistack.core.settings import get_config
from capistack.core.runner import DeploymentRunner
from capistack.core.logging import get_logger
from capistack.db.session import SessionLocal
from capistack.db.models import Deployment, DeploymentStep, Project, Secret
from capistack.core.secrets import secrets_manager
import uuid
from datetime import datetime

config = get_config()
logger = get_logger(__name__)

# Redis connection
redis_conn = redis.from_url(config.REDIS_URL)

# RQ queue
deployment_queue = Queue('deployments', connection=redis_conn)


def run_deployment(deployment_id: str, project_id: str, ref_type: str, 
                  ref_name: str, user_id: str) -> bool:
    """Background task to run a deployment."""
    logger.info(f"Starting deployment task: {deployment_id}")
    
    db = SessionLocal()
    try:
        # Get deployment record
        deployment = capistack.db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            logger.error(f"Deployment {deployment_id} not found")
            return False
        
        # Update deployment status
        deployment.status = 'running'
        deployment.started_at = datetime.utcnow()
        capistack.db.commit()
        
        # Get project secrets
        secrets = {}
        project_secrets = capistack.db.query(Secret).filter(Secret.project_id == project_id).all()
        for secret in project_secrets:
            try:
                decrypted_value = secrets_manager.decrypt_secret(secret.value_encrypted)
                secrets[secret.key] = decrypted_value
            except Exception as e:
                logger.warning(f"Failed to decrypt secret {secret.key}: {e}")
        
        # Create deployment runner
        runner = DeploymentRunner(deployment_id, redis_conn)
        
        # Run deployment steps
        steps = [
            ('preflight', 'Preflight checks'),
            ('checkout', 'Checkout repository'),
            ('build', 'Build application'),
            ('deploy', 'Deploy application'),
            ('post_deploy', 'Post-deployment tasks'),
            ('finalize', 'Finalize deployment')
        ]
        
        success = True
        for step_name, step_description in steps:
            # Create step record
            step = DeploymentStep(
                id=uuid.uuid4(),
                deployment_id=deployment.id,
                name=step_name,
                status='running',
                started_at=datetime.utcnow()
            )
            capistack.db.add(step)
            capistack.db.commit()
            
            try:
                # Run the actual deployment
                if step_name == 'preflight':
                    success = runner._preflight_checks()
                elif step_name == 'checkout':
                    success = runner._checkout_repo(ref_type, ref_name)
                elif step_name == 'build':
                    if runner._should_build():
                        success = runner._run_build()
                    else:
                        step.status = 'skipped'
                        step.finished_at = datetime.utcnow()
                        capistack.db.commit()
                        continue
                elif step_name == 'deploy':
                    success = runner._run_deploy()
                elif step_name == 'post_deploy':
                    if runner._should_post_deploy():
                        success = runner._run_post_deploy()
                    else:
                        step.status = 'skipped'
                        step.finished_at = datetime.utcnow()
                        capistack.db.commit()
                        continue
                elif step_name == 'finalize':
                    runner._finalize_deployment()
                    success = True
                
                # Update step status
                step.status = 'succeeded' if success else 'failed'
                step.finished_at = datetime.utcnow()
                capistack.db.commit()
                
                if not success:
                    break
                    
            except Exception as e:
                logger.error(f"Step {step_name} failed: {e}")
                step.status = 'failed'
                step.finished_at = datetime.utcnow()
                step.log_excerpt = str(e)
                capistack.db.commit()
                success = False
                break
        
        # Update deployment status
        deployment.status = 'succeeded' if success else 'failed'
        deployment.finished_at = datetime.utcnow()
        capistack.db.commit()
        
        logger.info(f"Deployment {deployment_id} completed with status: {deployment.status}")
        return success
        
    except Exception as e:
        logger.error(f"Deployment task failed: {e}")
        
        # Update deployment status to failed
        try:
            deployment = capistack.db.query(Deployment).filter(Deployment.id == deployment_id).first()
            if deployment:
                deployment.status = 'failed'
                deployment.finished_at = datetime.utcnow()
                capistack.db.commit()
        except Exception as update_error:
            logger.error(f"Failed to update deployment status: {update_error}")
        
        return False
        
    finally:
        capistack.db.close()


def cancel_deployment(deployment_id: str) -> bool:
    """Cancel a running deployment."""
    logger.info(f"Canceling deployment: {deployment_id}")
    
    db = SessionLocal()
    try:
        deployment = capistack.db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            logger.error(f"Deployment {deployment_id} not found")
            return False
        
        if deployment.status not in ['queued', 'running']:
            logger.warning(f"Deployment {deployment_id} is not in a cancellable state: {deployment.status}")
            return False
        
        # Mark deployment as canceled
        deployment.status = 'canceled'
        deployment.finished_at = datetime.utcnow()
        deployment.cancel_requested = True
        capistack.db.commit()
        
        # Cancel any running RQ job
        job = deployment_queue.fetch_job(deployment_id)
        if job:
            job.cancel()
        
        logger.info(f"Deployment {deployment_id} canceled")
        return True
        
    except Exception as e:
        logger.error(f"Failed to cancel deployment {deployment_id}: {e}")
        return False
    finally:
        capistack.db.close()


def cleanup_old_deployments():
    """Cleanup old deployments based on retention policy."""
    logger.info("Starting cleanup of old deployments")
    
    db = SessionLocal()
    try:
        # Get all projects
        projects = capistack.db.query(Project).all()
        
        for project in projects:
            # Get deployments for this project, ordered by creation date
            deployments = capistack.db.query(Deployment).filter(
                Deployment.project_id == project.id
            ).order_by(Deployment.created_at.desc()).all()
            
            # Keep only the most recent N deployments
            deployments_to_delete = deployments[config.RETAIN_DEPLOYMENTS:]
            
            for deployment in deployments_to_delete:
                logger.info(f"Deleting old deployment: {deployment.id}")
                
                # Delete associated steps
                capistack.db.query(DeploymentStep).filter(
                    DeploymentStep.deployment_id == deployment.id
                ).delete()
                
                # Delete deployment
                capistack.db.delete(deployment)
            
            if deployments_to_delete:
                logger.info(f"Deleted {len(deployments_to_delete)} old deployments for project {project.id}")
        
        capistack.db.commit()
        logger.info("Cleanup completed")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        capistack.db.rollback()
    finally:
        capistack.db.close()


def start_worker():
    """Start the RQ worker."""
    logger.info("Starting RQ worker")
    
    worker = Worker([deployment_queue], connection=redis_conn)
    worker.work()


if __name__ == '__main__':
    start_worker()
