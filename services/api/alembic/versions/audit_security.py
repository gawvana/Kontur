"""Persistent sessions, deduplication and query indexes."""
from alembic import op
import sqlalchemy as sa
revision = "audit_security"
down_revision = "e2c31251b2de"
branch_labels = depends_on = None

def upgrade():
    op.create_table("sessions", sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False))
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    with op.batch_alter_table("cases") as batch:
        batch.add_column(sa.Column("idempotency_key", sa.String(128), nullable=True))
        batch.create_unique_constraint("uq_case_request", ["creator_id", "idempotency_key"])
    for table, column in [("cases", "creator_id"), ("cases", "status"), ("catalogs", "owner_id"), ("catalog_items", "catalog_id")]:
        op.create_index(f"ix_{table}_{column}", table, [column])

def downgrade():
    for table, column in [("cases", "creator_id"), ("cases", "status"), ("catalogs", "owner_id"), ("catalog_items", "catalog_id")]:
        op.drop_index(f"ix_{table}_{column}", table_name=table)
    with op.batch_alter_table("cases") as batch:
        batch.drop_constraint("uq_case_request", type_="unique")
        batch.drop_column("idempotency_key")
    op.drop_table("sessions")
