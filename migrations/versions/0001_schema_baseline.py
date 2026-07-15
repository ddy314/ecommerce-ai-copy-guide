"""Create the current application schema and upgrade legacy installations."""

from alembic import op
import sqlalchemy as sa

import backend.models  # noqa: F401
from backend.database import Base

revision = "0001_schema_baseline"
down_revision = None
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    additions = {
        "users": [
            sa.Column("password_plain", sa.String(100), nullable=True),
            sa.Column("display_id", sa.String(64), nullable=True),
        ],
        "products": [
            sa.Column("display_id", sa.String(64), nullable=True),
            sa.Column("image_urls", sa.JSON(), nullable=True),
            sa.Column("videos", sa.JSON(), nullable=True),
        ],
        "orders": [
            sa.Column("tracking_no", sa.String(100), nullable=True),
            sa.Column("return_tracking_no", sa.String(100), nullable=True),
            sa.Column("return_status", sa.String(20), nullable=True),
            sa.Column("return_reason", sa.String(500), nullable=True),
            sa.Column("return_applied_at", sa.DateTime(), nullable=True),
            sa.Column("return_completed_at", sa.DateTime(), nullable=True),
        ],
    }
    for table, columns in additions.items():
        existing = _columns(table)
        if not existing:
            continue
        with op.batch_alter_table(table) as batch:
            for column in columns:
                if column.name not in existing:
                    batch.add_column(column)


def downgrade() -> None:
    # This baseline may adopt an existing installation, so destructive rollback is intentionally disabled.
    pass
