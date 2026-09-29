"""Add scheduler, webhooks, RBAC, and export format tables.

Revision ID: 0002_add_scheduler_webhooks_rbac
Revises: 0001_init
Create Date: 2026-09-24

"""
from alembic import op
import sqlalchemy as sa

revision = '0002_add_scheduler_webhooks_rbac'
down_revision = '0001_init'
branch_labels = None
depends_on = None


def _create(table, *cols):
    try:
        op.create_table(table, *cols, checkfirst=True)
    except Exception:
        pass


def _index(name, table, cols, **kw):
    try:
        op.create_index(name, table, cols, **kw)
    except Exception:
        pass


def upgrade():
    # Scheduled Jobs
    _create('scheduled_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cron_expression', sa.String(), nullable=False),
        sa.Column('dataset_id', sa.String(), nullable=True),
        sa.Column('ruleset', sa.String(), nullable=False, default='general-v1'),
        sa.Column('config', sa.Text(), nullable=False, default='{}'),
        sa.Column('status', sa.String(), nullable=False, default='PENDING'),
        sa.Column('last_run', sa.DateTime(), nullable=True),
        sa.Column('next_run', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, default=3600),
        sa.PrimaryKeyConstraint('id')
    )
    _index('ix_scheduled_jobs_dataset_id', 'scheduled_jobs', ['dataset_id'])
    _index('ix_scheduled_jobs_next_run', 'scheduled_jobs', ['next_run'])

    # Webhooks
    _create('webhooks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('secret', sa.String(), nullable=True, default=''),
        sa.Column('events', sa.Text(), nullable=False, default='[]'),
        sa.Column('headers', sa.Text(), nullable=False, default='{}'),
        sa.Column('active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('last_triggered', sa.DateTime(), nullable=True),
        sa.Column('failure_count', sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id')
    )

    # Job Runs
    _create('job_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('dataset_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, default='PENDING'),
        sa.Column('started_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=False, default=0),
        sa.Column('quality_score', sa.Text(), nullable=False, default='{}'),
        sa.Column('issues_found', sa.Integer(), nullable=False, default=0),
        sa.Column('error_message', sa.Text(), nullable=True, default=''),
        sa.Column('triggered_by', sa.String(), nullable=False, default='scheduled'),
        sa.ForeignKeyConstraint(['job_id'], ['scheduled_jobs.id']),
        sa.PrimaryKeyConstraint('id')
    )
    _index('ix_job_runs_job_id', 'job_runs', ['job_id'])
    _index('ix_job_runs_dataset_id', 'job_runs', ['dataset_id'])

    # Webhook Deliveries
    _create('webhook_deliveries',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('webhook_id', sa.String(), nullable=False),
        sa.Column('event', sa.String(), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False, default='{}'),
        sa.Column('response_status', sa.Integer(), nullable=False, default=0),
        sa.Column('response_body', sa.Text(), nullable=True, default=''),
        sa.Column('attempt', sa.Integer(), nullable=False, default=1),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id']),
        sa.PrimaryKeyConstraint('id')
    )
    _index('ix_webhook_deliveries_webhook_id', 'webhook_deliveries', ['webhook_id'])

    # Users (RBAC)
    _create('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    _index('ix_users_email', 'users', ['email'], unique=True)

    # Workspaces (RBAC)
    _create('workspaces',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True, default=''),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('settings', sa.Text(), nullable=False, default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    _index('ix_workspaces_slug', 'workspaces', ['slug'], unique=True)

    # Workspace Members (many-to-many User <-> Workspace with role)
    _create('workspace_members',
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, default='viewer'),
        sa.Column('joined_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workspace_id', 'user_id')
    )

    # Dataset Permissions (explicit per-user per-dataset)
    _create('dataset_permissions',
        sa.Column('dataset_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('permission', sa.String(), nullable=False),
        sa.Column('granted_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('granted_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('dataset_id', 'user_id', 'permission')
    )

    # Add workspace_id to datasets table (0001 baseline already includes it -> idempotent)
    try:
        from sqlalchemy import inspect as sa_inspect
        bind = op.get_bind()
        cols = [c["name"] for c in sa_inspect(bind).get_columns("datasets")]
        if "workspace_id" not in cols:
            op.add_column('datasets', sa.Column('workspace_id', sa.String(), nullable=True))
    except Exception:
        pass
    try:
        op.create_foreign_key('fk_datasets_workspace', 'datasets', 'workspaces', ['workspace_id'], ['id'])
    except Exception:
        pass
    _index('ix_datasets_workspace_id', 'datasets', ['workspace_id'])


def downgrade():
    for name in ('ix_datasets_workspace_id',):
        try:
            op.drop_index(name, table_name='datasets')
        except Exception:
            pass
    try:
        op.drop_constraint('fk_datasets_workspace', 'datasets', type_='foreignkey')
    except Exception:
        pass
    for t in ('dataset_permissions', 'workspace_members', 'workspaces', 'users',
              'webhook_deliveries', 'job_runs', 'webhooks', 'scheduled_jobs'):
        try:
            op.drop_table(t)
        except Exception:
            pass
