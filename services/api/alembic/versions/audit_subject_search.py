"""Index the actual normalized username search predicate."""
from alembic import op
import sqlalchemy as sa
revision = "audit_subject_search"
down_revision = "audit_catalog_requests"
branch_labels = depends_on = None

def upgrade():
    op.create_index("ix_subjects_username_lower", "subjects", [sa.text("lower(username)")])

def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_subjects_username_lower")
