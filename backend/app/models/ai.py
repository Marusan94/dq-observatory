"""AI Models for chat logs, fix suggestions, and model versions."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base


class AIChatLog(Base):
    __tablename__ = "ai_chat_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=True, index=True)
    user_role = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    model = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", backref="ai_chat_logs")


class AIFixSuggestion(Base):
    __tablename__ = "ai_fix_suggestions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id = Column(String, ForeignKey("quality_issues.id"), nullable=False, index=True)
    operation = Column(String, nullable=False)
    column = Column(String, nullable=True)
    params = Column(Text, default="{}")  # JSON
    preview_json = Column(Text, default="{}")  # JSON
    confidence = Column(Float, default=0.0)
    reasoning = Column(Text, default="")
    accepted = Column(Integer, default=0)  # 0=no, 1=yes
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("QualityIssue", backref="ai_fix_suggestions")


class PredictiveModelVersion(Base):
    __tablename__ = "predictive_model_versions"

    version = Column(String, primary_key=True)
    model_path = Column(String, nullable=False)
    features_json = Column(Text, default="[]")  # JSON
    metrics_json = Column(Text, default="{}")  # JSON (MAE, RMSE, etc.)
    trained_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, default=0)

    __table_args__ = (Index("ix_pred_model_active", "is_active"),)


# Migration for new tables (to be added to alembic)
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('ai_chat_logs',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('dataset_id', sa.String, sa.ForeignKey('datasets.id'), nullable=True),
        sa.Column('user_role', sa.String, nullable=False),
        sa.Column('question', sa.Text, nullable=False),
        sa.Column('answer', sa.Text, nullable=False),
        sa.Column('tokens_used', sa.Integer, default=0),
        sa.Column('latency_ms', sa.Integer, default=0),
        sa.Column('model', sa.String, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    op.create_index('ix_ai_chat_dataset', 'ai_chat_logs', ['dataset_id'])

    op.create_table('ai_fix_suggestions',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('issue_id', sa.String, sa.ForeignKey('quality_issues.id'), nullable=False),
        sa.Column('operation', sa.String, nullable=False),
        sa.Column('column', sa.String, nullable=True),
        sa.Column('params', sa.Text, default='{}'),
        sa.Column('preview_json', sa.Text, default='{}'),
        sa.Column('confidence', sa.Float, default=0.0),
        sa.Column('reasoning', sa.Text, default=''),
        sa.Column('accepted', sa.Integer, default=0),
        sa.Column('applied_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    op.create_index('ix_ai_fix_issue', 'ai_fix_suggestions', ['issue_id'])

    op.create_table('predictive_model_versions',
        sa.Column('version', sa.String, primary_key=True),
        sa.Column('model_path', sa.String, nullable=False),
        sa.Column('features_json', sa.Text, default='[]'),
        sa.Column('metrics_json', sa.Text, default='{}'),
        sa.Column('trained_at', sa.DateTime, default=sa.func.now()),
        sa.Column('is_active', sa.Integer, default=0),
    )
    op.create_index('ix_pred_model_active', 'predictive_model_versions', ['is_active'])

def downgrade():
    op.drop_table('predictive_model_versions')
    op.drop_table('ai_fix_suggestions')
    op.drop_table('ai_chat_logs')
"""