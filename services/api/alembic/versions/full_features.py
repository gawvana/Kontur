"""Full domain models for Kontur: saved contacts, multi-step cases, evidence, decisions, appeals, reputation, invites, notifications, audit.

Revision ID: full_features
Revises: audit_subject_search
Create Date: 2026-10-04
"""
from alembic import op
import sqlalchemy as sa
from db.models import Role, CaseStatus

revision = "full_features"
down_revision = "audit_subject_search"
branch_labels = depends_on = None

def upgrade():
    # 1. New columns on users
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("first_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("last_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("totp_secret", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("is_2fa_enabled", sa.Boolean(), server_default=sa.text("0"), nullable=False))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    # 2. New columns on subjects
    with op.batch_alter_table("subjects") as batch_op:
        batch_op.add_column(sa.Column("is_verified", sa.Boolean(), server_default=sa.text("0"), nullable=False))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.execute("CREATE INDEX IF NOT EXISTS ix_subjects_username_lower ON subjects (lower(username))")

    # 3. New columns on sessions
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(sa.Column("is_revoked", sa.Boolean(), server_default=sa.text("0"), nullable=False))
        batch_op.add_column(sa.Column("user_agent", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("ip_address", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))

    # 4. New columns on catalogs
    with op.batch_alter_table("catalogs") as batch_op:
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))

    # 5. New columns on cases
    with op.batch_alter_table("cases") as batch_op:
        batch_op.add_column(sa.Column("target_username", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("experience_type", sa.String(), server_default="NEGATIVE", nullable=False))
        batch_op.add_column(sa.Column("category", sa.String(), server_default="SERVICE", nullable=False))
        batch_op.add_column(sa.Column("deal_date", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("agreed_terms", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("author_actions", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("result_description", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("amount", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("currency", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("violation_details", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("visibility", sa.String(), server_default="PRIVATE", nullable=False))
        batch_op.add_column(sa.Column("current_version", sa.Integer(), server_default="1", nullable=False))
        batch_op.add_column(sa.Column("outcome_note", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch_op.alter_column("subject_id", nullable=True)
        batch_op.alter_column(
            "status",
            type_=sa.Enum('PENDING', 'DRAFT', 'SUBMITTED', 'IN_REVIEW', 'NEEDS_INFO', 'APPROVED', 'REJECTED', 'WITHDRAWN', 'RESOLVED', name='casestatus'),
            existing_type=sa.VARCHAR(length=8),
            nullable=False
        )
        batch_op.create_index("ix_cases_subject_id", ["subject_id"])
        batch_op.create_index("ix_cases_target_username", ["target_username"])

    # 6. admin_recovery_codes
    op.create_table(
        "admin_recovery_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("is_used", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_admin_recovery_codes_user_id", "admin_recovery_codes", ["user_id"])

    # 7. username_observations
    op.create_table(
        "username_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("raw_username", sa.String(), nullable=False),
        sa.Column("normalized_username", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("0"), nullable=False),
    )
    op.create_index("ix_username_observations_subject_id", "username_observations", ["subject_id"])
    op.create_index("ix_username_observations_normalized_username", "username_observations", ["normalized_username"])

    # 8. catalog_members
    op.create_table(
        "catalog_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("catalog_id", sa.Integer(), sa.ForeignKey("catalogs.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("catalog_id", "user_id", name="uq_catalog_member")
    )
    op.create_index("ix_catalog_members_catalog_id", "catalog_members", ["catalog_id"])
    op.create_index("ix_catalog_members_user_id", "catalog_members", ["user_id"])

    # 9. catalog_invites
    op.create_table(
        "catalog_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("catalog_id", sa.Integer(), sa.ForeignKey("catalogs.id"), nullable=False),
        sa.Column("inviter_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(length=64), unique=True, nullable=False),
        sa.Column("role", sa.String(), server_default="VIEWER", nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_catalog_invites_catalog_id", "catalog_invites", ["catalog_id"])
    op.create_index("ix_catalog_invites_token", "catalog_invites", ["token"], unique=True)

    # 10. saved_contacts (F01)
    op.create_table(
        "saved_contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("catalog_id", sa.Integer(), sa.ForeignKey("catalogs.id"), nullable=True),
        sa.Column("raw_input", sa.String(), nullable=False),
        sa.Column("normalized_username", sa.String(), nullable=True),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("tags", sa.String(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("personal_rating", sa.String(), nullable=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_saved_contacts_user_id", "saved_contacts", ["user_id"])
    op.create_index("ix_saved_contacts_catalog_id", "saved_contacts", ["catalog_id"])
    op.create_index("ix_saved_contacts_normalized_username", "saved_contacts", ["normalized_username"])
    op.create_index("ix_saved_contacts_subject_id", "saved_contacts", ["subject_id"])

    # 11. content_versions
    op.create_table(
        "content_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("version_num", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("agreed_terms", sa.Text(), nullable=True),
        sa.Column("author_actions", sa.Text(), nullable=True),
        sa.Column("result_description", sa.Text(), nullable=True),
        sa.Column("violation_details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_content_versions_case_id", "content_versions", ["case_id"])

    # 12. evidence
    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("uploader_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("author_explanation", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), server_default="PENDING", nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("redacted_storage_key", sa.String(), nullable=True),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_evidence_case_id", "evidence", ["case_id"])

    # 13. decisions
    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("moderator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("limitations_note", sa.Text(), nullable=True),
        sa.Column("content_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_decisions_case_id", "decisions", ["case_id"])

    # 14. responses
    op.create_table(
        "responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("responder_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), server_default="SUBMITTED", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_responses_case_id", "responses", ["case_id"])

    # 15. appeals
    op.create_table(
        "appeals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("appellant_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), server_default="SUBMITTED", nullable=False),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_appeals_case_id", "appeals", ["case_id"])

    # 16. reputation_reviews
    op.create_table(
        "reputation_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("score_type", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("subject_id", "author_id", name="uq_subject_author_review")
    )
    op.create_index("ix_reputation_reviews_subject_id", "reputation_reviews", ["subject_id"])
    op.create_index("ix_reputation_reviews_author_id", "reputation_reviews", ["author_id"])

    # 17. subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "subject_id", name="uq_user_subject_sub")
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_subject_id", "subscriptions", ["subject_id"])

    # 18. notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("object_type", sa.String(), nullable=True),
        sa.Column("object_id", sa.Integer(), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    # 19. outbox_events
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), server_default="PENDING", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])

    # 20. support_tickets
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), server_default="OPEN", nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("answered_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"])

    # 21. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("object_type", sa.String(), nullable=False),
        sa.Column("object_id", sa.String(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # 22. export_jobs
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(), server_default="PENDING", nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_export_jobs_user_id", "export_jobs", ["user_id"])

    # 23. account_deletion_requests
    op.create_table(
        "account_deletion_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(), server_default="PENDING", nullable=False),
        sa.Column("scheduled_for", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_account_deletion_requests_user_id", "account_deletion_requests", ["user_id"])


def downgrade():
    op.drop_table("account_deletion_requests")
    op.drop_table("export_jobs")
    op.drop_table("audit_logs")
    op.drop_table("support_tickets")
    op.drop_table("outbox_events")
    op.drop_table("notifications")
    op.drop_table("subscriptions")
    op.drop_table("reputation_reviews")
    op.drop_table("appeals")
    op.drop_table("responses")
    op.drop_table("decisions")
    op.drop_table("evidence")
    op.drop_table("content_versions")
    op.drop_table("saved_contacts")
    op.drop_table("catalog_invites")
    op.drop_table("catalog_members")
    op.drop_table("username_observations")
    op.drop_table("admin_recovery_codes")
    with op.batch_alter_table("cases") as batch_op:
        batch_op.drop_index("ix_cases_target_username")
        batch_op.drop_index("ix_cases_subject_id")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("outcome_note")
        batch_op.drop_column("current_version")
        batch_op.drop_column("visibility")
        batch_op.drop_column("violation_details")
        batch_op.drop_column("currency")
        batch_op.drop_column("amount")
        batch_op.drop_column("result_description")
        batch_op.drop_column("author_actions")
        batch_op.drop_column("agreed_terms")
        batch_op.drop_column("deal_date")
        batch_op.drop_column("category")
        batch_op.drop_column("experience_type")
        batch_op.drop_column("target_username")
    with op.batch_alter_table("catalogs") as batch_op:
        batch_op.drop_column("description")
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_column("created_at")
        batch_op.drop_column("ip_address")
        batch_op.drop_column("user_agent")
        batch_op.drop_column("is_revoked")
    with op.batch_alter_table("subjects") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("is_verified")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("is_2fa_enabled")
        batch_op.drop_column("totp_secret")
        batch_op.drop_column("last_name")
        batch_op.drop_column("first_name")
        batch_op.drop_column("username")
