"""
Database models for CapiStack.

This module defines all SQLAlchemy models for the CapiStack application including
users, projects, deployments, secrets, and audit logs.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Boolean, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from capistack.db.session import Base


class User(Base):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    role = Column(String(50), nullable=False, default='user')  # admin | user
    password_hash = Column(String(255))  # nullable for OAuth users
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="user")
    secrets = relationship("Secret", back_populates="created_by_user")


class OAuthAccount(Base):
    """OAuth account linking."""
    __tablename__ = 'oauth_accounts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    provider = Column(String(50), nullable=False)  # github | gitlab | oidc
    provider_user_id = Column(String(255), nullable=False)
    access_token = Column(LargeBinary)  # encrypted
    refresh_token = Column(LargeBinary)  # encrypted
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="oauth_accounts")
    
    # Unique constraint per provider
    __table_args__ = (
        {'extend_existing': True}
    )


class Project(Base):
    """Project model (single project for MVP)."""
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    repo_url = Column(Text, nullable=False)
    git_provider = Column(String(50), nullable=False)  # github | gitlab | generic
    default_branch = Column(String(255), nullable=False, default='main')
    runner_type = Column(String(50), nullable=False, default='local')  # local | docker
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    secrets = relationship("Secret", back_populates="project", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="project", cascade="all, delete-orphan")


class Secret(Base):
    """Encrypted secrets for projects."""
    __tablename__ = 'secrets'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    key = Column(String(255), nullable=False)
    value_encrypted = Column(LargeBinary, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="secrets")
    created_by_user = relationship("User", back_populates="secrets")
    
    # Unique constraint per project and key
    __table_args__ = (
        {'extend_existing': True}
    )


class Deployment(Base):
    """Deployment model."""
    __tablename__ = 'deployments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    ref_type = Column(String(50), nullable=False)  # branch | tag | release | commit
    ref_name = Column(String(255), nullable=False)
    commit_sha = Column(String(40))  # Git SHA
    status = Column(String(50), nullable=False, default='queued')  # queued | running | succeeded | failed | canceled
    logs_path = Column(Text)
    artifacts_path = Column(Text)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    cancel_requested = Column(Boolean, default=False)
    
    # Relationships
    project = relationship("Project", back_populates="deployments")
    user = relationship("User", back_populates="deployments")
    steps = relationship("DeploymentStep", back_populates="deployment", cascade="all, delete-orphan")
    
    @property
    def runtime_seconds(self) -> int:
        """Calculate runtime in seconds."""
        if not self.started_at:
            return 0
        end_time = self.finished_at or datetime.utcnow()
        return int((end_time - self.started_at).total_seconds())


class DeploymentStep(Base):
    """Individual steps in a deployment."""
    __tablename__ = 'deployment_steps'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(UUID(as_uuid=True), ForeignKey('deployments.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)  # preflight | checkout | build | deploy | post_deploy | finalize
    status = Column(String(50), nullable=False, default='queued')  # queued | running | succeeded | failed | skipped
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    log_excerpt = Column(Text)  # Last few lines of logs
    
    # Relationships
    deployment = relationship("Deployment", back_populates="steps")


class AuditLog(Base):
    """Audit trail for actions."""
    __tablename__ = 'audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    action = Column(String(255), nullable=False)  # deploy_started | deploy_completed | secret_created | etc.
    target_type = Column(String(100))  # deployment | secret | project | user
    target_id = Column(String(255))  # ID of the target object
    data_json = Column(Text)  # Additional data as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    actor = relationship("User")
