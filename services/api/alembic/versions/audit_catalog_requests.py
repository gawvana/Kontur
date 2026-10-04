"""Deduplicate catalog requests and contact membership without deleting data."""
from alembic import op, context
import sqlalchemy as sa
revision = "audit_catalog_requests"
down_revision = "audit_security"
branch_labels = depends_on = None

def upgrade():
    duplicates = None if context.is_offline_mode() else op.get_bind().execute(sa.text("SELECT catalog_id, subject_id FROM catalog_items GROUP BY catalog_id, subject_id HAVING COUNT(*) > 1 LIMIT 1")).first()
    if duplicates:
        raise RuntimeError("Duplicate catalog memberships exist. Back up and reconcile their private notes before retrying; no data was deleted.")
    with op.batch_alter_table("catalogs") as batch:
        batch.add_column(sa.Column("idempotency_key", sa.String(128), nullable=True))
        batch.create_unique_constraint("uq_catalog_request", ["owner_id", "idempotency_key"])
    with op.batch_alter_table("catalog_items") as batch:
        batch.create_unique_constraint("uq_catalog_contact", ["catalog_id", "subject_id"])

def downgrade():
    with op.batch_alter_table("catalog_items") as batch:
        batch.drop_constraint("uq_catalog_contact", type_="unique")
    with op.batch_alter_table("catalogs") as batch:
        batch.drop_constraint("uq_catalog_request", type_="unique")
        batch.drop_column("idempotency_key")
