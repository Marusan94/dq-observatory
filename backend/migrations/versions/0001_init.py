"""Initial tables mirror app.models.entities (Alembic baseline)."""
revision = "0001_init"
down_revision = None

from alembic import op
import sqlalchemy as sa


def _create(table, *cols):
    try:
        op.create_table(table, *cols, checkfirst=True)
    except Exception:
        pass


def upgrade():
    _create("datasets",
        sa.Column("id", sa.String, primary_key=True), sa.Column("name", sa.String, nullable=False),
        sa.Column("original_filename", sa.String, nullable=False), sa.Column("file_hash", sa.String),
        sa.Column("file_size", sa.Integer, default=0), sa.Column("file_format", sa.String),
        sa.Column("rows", sa.Integer, default=0), sa.Column("columns", sa.Integer, default=0),
        sa.Column("workspace_id", sa.String, nullable=True), sa.Column("owner_id", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime), sa.Column("updated_at", sa.DateTime))
    _create("dataset_versions",
        sa.Column("id", sa.String, primary_key=True), sa.Column("dataset_id", sa.String, sa.ForeignKey("datasets.id")),
        sa.Column("version_number", sa.Integer), sa.Column("label", sa.String),
        sa.Column("parent_version_id", sa.String, nullable=True), sa.Column("storage_path", sa.String),
        sa.Column("rows", sa.Integer, default=0), sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime))
    _create("quality_runs",
        sa.Column("id", sa.String, primary_key=True), sa.Column("dataset_id", sa.String),
        sa.Column("version_id", sa.String), sa.Column("status", sa.String, default="COMPLETED"),
        sa.Column("score", sa.Float, nullable=True), sa.Column("dimensions", sa.Text),
        sa.Column("warnings", sa.Text), sa.Column("duration_ms", sa.Integer, default=0),
        sa.Column("engine_version", sa.String), sa.Column("ruleset", sa.String),
        sa.Column("created_at", sa.DateTime))
    _create("quality_issues",
        sa.Column("id", sa.String, primary_key=True), sa.Column("dataset_id", sa.String),
        sa.Column("version_id", sa.String), sa.Column("run_id", sa.String),
        sa.Column("severity", sa.String), sa.Column("category", sa.String), sa.Column("column", sa.String, nullable=True),
        sa.Column("row_count", sa.Integer), sa.Column("percentage", sa.Float),
        sa.Column("description", sa.Text), sa.Column("examples", sa.Text), sa.Column("rule", sa.String),
        sa.Column("auto_fix_available", sa.Integer, default=0), sa.Column("status", sa.String, default="OPEN"),
        sa.Column("created_at", sa.DateTime))
    _create("cleaning_operations",
        sa.Column("id", sa.String, primary_key=True), sa.Column("dataset_id", sa.String),
        sa.Column("from_version_id", sa.String, nullable=True), sa.Column("to_version_id", sa.String, nullable=True),
        sa.Column("operation", sa.String), sa.Column("column", sa.String, nullable=True),
        sa.Column("params", sa.Text), sa.Column("affected_rows", sa.Integer, default=0),
        sa.Column("actor", sa.String, default="user"), sa.Column("created_at", sa.DateTime))
    _create("validation_rules",
        sa.Column("id", sa.String, primary_key=True), sa.Column("dataset_id", sa.String, nullable=True),
        sa.Column("name", sa.String), sa.Column("column", sa.String), sa.Column("operator", sa.String),
        sa.Column("value", sa.Text), sa.Column("severity", sa.String), sa.Column("ruleset", sa.String, default="custom"),
        sa.Column("created_at", sa.DateTime))
    _create("audit_log",
        sa.Column("id", sa.String, primary_key=True), sa.Column("dataset_id", sa.String, nullable=True),
        sa.Column("action", sa.String), sa.Column("detail", sa.Text), sa.Column("created_at", sa.DateTime))


def downgrade():
    for t in ("audit_log", "validation_rules", "cleaning_operations", "quality_issues", "quality_runs", "dataset_versions", "datasets"):
        try:
            op.drop_table(t)
        except Exception:
            pass
