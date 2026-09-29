"""Data contracts + checks (governance baseline)."""
revision = "0004_contracts"
down_revision = "0002_add_scheduler_webhooks_rbac"

from alembic import op
import sqlalchemy as sa


def _create(table, *cols):
    try:
        op.create_table(table, *cols, checkfirst=True)
    except Exception:
        pass


def upgrade():
    _create("data_contracts",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("dataset_id", sa.String, sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("schema_json", sa.Text, default="{}"),
        sa.Column("rules_json", sa.Text, default="[]"),
        sa.Column("sla_json", sa.Text, default="{}"),
        sa.Column("status", sa.String, default="ACTIVE"),
        sa.Column("created_by", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime), sa.Column("updated_at", sa.DateTime))
    _create("contract_checks",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("contract_id", sa.String, sa.ForeignKey("data_contracts.id"), nullable=False),
        sa.Column("version_id", sa.String, sa.ForeignKey("dataset_versions.id"), nullable=True),
        sa.Column("passed", sa.Integer, default=0),
        sa.Column("violations_json", sa.Text, default="[]"),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime))
    try:
        op.create_index("ix_data_contracts_dataset", "data_contracts", ["dataset_id"])
    except Exception:
        pass
    try:
        op.create_index("ix_contract_checks_contract", "contract_checks", ["contract_id"])
    except Exception:
        pass


def downgrade():
    for t in ("contract_checks", "data_contracts"):
        try:
            op.drop_table(t)
        except Exception:
            pass
