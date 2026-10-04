from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Enum,
    UniqueConstraint, Index, func
)
from sqlalchemy.orm import relationship
import enum
from .database import Base

class Role(str, enum.Enum):
    USER = "USER"
    MODERATOR = "MODERATOR"
    SENIOR_MODERATOR = "SENIOR_MODERATOR"
    ADMIN = "ADMIN"
    OWNER = "OWNER"

class CaseStatus(str, enum.Enum):
    PENDING = "PENDING"
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    IN_REVIEW = "IN_REVIEW"
    NEEDS_INFO = "NEEDS_INFO"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    RESOLVED = "RESOLVED"

class CaseVisibility(str, enum.Enum):
    PRIVATE = "PRIVATE"
    PUBLISHED = "PUBLISHED"
    HIDDEN = "HIDDEN"

class ExperienceType(str, enum.Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"

class CaseCategory(str, enum.Enum):
    GOODS = "GOODS"
    DIGITAL = "DIGITAL"
    SERVICE = "SERVICE"
    EXCHANGE = "EXCHANGE"
    OTHER = "OTHER"

class AppealStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    SCREENING = "SCREENING"
    IN_REVIEW = "IN_REVIEW"
    UPHELD = "UPHELD"
    CHANGED = "CHANGED"
    OVERTURNED = "OVERTURNED"
    RETURNED = "RETURNED"
    REJECTED = "REJECTED"

class DecisionType(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_INFO = "REQUEST_INFO"
    HIDE = "HIDE"
    RESTORE = "RESTORE"

class EvidenceStatus(str, enum.Enum):
    PENDING = "PENDING"
    QUARANTINED = "QUARANTINED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"

class CatalogMemberRole(str, enum.Enum):
    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

class PersonalRating(str, enum.Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"

class SupportStatus(str, enum.Enum):
    OPEN = "OPEN"
    ANSWERED = "ANSWERED"
    CLOSED = "CLOSED"

class ExportStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(Enum(Role), default=Role.USER, nullable=False)
    totp_secret = Column(String, nullable=True)
    is_2fa_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    catalogs = relationship("Catalog", back_populates="owner")
    cases = relationship("Case", back_populates="creator", foreign_keys="[Case.creator_id]")
    reviews = relationship("Review", back_populates="author")
    saved_contacts = relationship("SavedContact", back_populates="user")
    sessions = relationship("Session", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String(32), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")


class AdminRecoveryCode(Base):
    __tablename__ = "admin_recovery_codes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code_hash = Column(String, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("ix_subjects_username_lower", func.lower(username)),)

    cases = relationship("Case", back_populates="subject")
    catalog_items = relationship("CatalogItem", back_populates="subject")
    saved_contacts = relationship("SavedContact", back_populates="subject")
    observations = relationship("UsernameObservation", back_populates="subject")
    reputation_reviews = relationship("ReputationReview", back_populates="subject")
    subscriptions = relationship("Subscription", back_populates="subject")


class UsernameObservation(Base):
    __tablename__ = "username_observations"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    raw_username = Column(String, nullable=False)
    normalized_username = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)
    observed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    subject = relationship("Subject", back_populates="observations")


class Catalog(Base):
    __tablename__ = "catalogs"
    __table_args__ = (UniqueConstraint("owner_id", "idempotency_key", name="uq_catalog_request"),)

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    is_private = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="catalogs")
    items = relationship("CatalogItem", back_populates="catalog")
    members = relationship("CatalogMember", back_populates="catalog")
    invites = relationship("CatalogInvite", back_populates="catalog")
    contacts = relationship("SavedContact", back_populates="catalog")


class CatalogMember(Base):
    __tablename__ = "catalog_members"
    __table_args__ = (UniqueConstraint("catalog_id", "user_id", name="uq_catalog_member"),)

    id = Column(Integer, primary_key=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(Enum(CatalogMemberRole), default=CatalogMemberRole.VIEWER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    catalog = relationship("Catalog", back_populates="members")
    user = relationship("User")


class CatalogInvite(Base):
    __tablename__ = "catalog_invites"

    id = Column(Integer, primary_key=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=False, index=True)
    inviter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(64), unique=True, index=True, nullable=False)
    role = Column(Enum(CatalogMemberRole), default=CatalogMemberRole.VIEWER, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    catalog = relationship("Catalog", back_populates="invites")


class CatalogItem(Base):
    __tablename__ = "catalog_items"
    __table_args__ = (UniqueConstraint("catalog_id", "subject_id", name="uq_catalog_contact"),)

    id = Column(Integer, primary_key=True, index=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    note = Column(Text, nullable=True)
    is_private = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    catalog = relationship("Catalog", back_populates="items")
    subject = relationship("Subject", back_populates="catalog_items")


class SavedContact(Base):
    __tablename__ = "saved_contacts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=True, index=True)
    raw_input = Column(String, nullable=False)
    normalized_username = Column(String, nullable=True, index=True)
    display_name = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    tags = Column(String, nullable=True)
    is_favorite = Column(Boolean, default=False, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)
    personal_rating = Column(Enum(PersonalRating), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="saved_contacts")
    catalog = relationship("Catalog", back_populates="contacts")
    subject = relationship("Subject", back_populates="saved_contacts")


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (UniqueConstraint("creator_id", "idempotency_key", name="uq_case_request"),)

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)
    target_username = Column(String, nullable=True, index=True)
    experience_type = Column(Enum(ExperienceType), default=ExperienceType.NEGATIVE, nullable=False)
    category = Column(Enum(CaseCategory), default=CaseCategory.SERVICE, nullable=False)
    deal_date = Column(DateTime, nullable=True)
    agreed_terms = Column(Text, nullable=True)
    author_actions = Column(Text, nullable=True)
    result_description = Column(Text, nullable=True)
    amount = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    violation_details = Column(Text, nullable=True)
    status = Column(Enum(CaseStatus), default=CaseStatus.PENDING, nullable=False, index=True)
    visibility = Column(Enum(CaseVisibility), default=CaseVisibility.PRIVATE, nullable=False)
    description = Column(Text, nullable=False)
    idempotency_key = Column(String(128), nullable=True)
    current_version = Column(Integer, default=1, nullable=False)
    outcome_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", back_populates="cases", foreign_keys=[creator_id])
    subject = relationship("Subject", back_populates="cases")
    reviews = relationship("Review", back_populates="case")
    evidence_items = relationship("Evidence", back_populates="case")
    versions = relationship("ContentVersion", back_populates="case")
    decisions = relationship("Decision", back_populates="case")
    responses = relationship("Response", back_populates="case")
    appeals = relationship("Appeal", back_populates="case")


class ContentVersion(Base):
    __tablename__ = "content_versions"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    version_num = Column(Integer, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    changelog = Column(Text, nullable=True)
    agreed_terms = Column(Text, nullable=True)
    author_actions = Column(Text, nullable=True)
    result_description = Column(Text, nullable=True)
    violation_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="versions")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    file_hash = Column(String(64), nullable=False)
    author_explanation = Column(Text, nullable=True)
    status = Column(Enum(EvidenceStatus), default=EvidenceStatus.PENDING, nullable=False)
    storage_key = Column(String, nullable=False)
    redacted_storage_key = Column(String, nullable=True)
    is_published = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="evidence_items")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    moderator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    decision = Column(Enum(DecisionType), nullable=False)
    reason = Column(Text, nullable=False)
    limitations_note = Column(Text, nullable=True)
    content_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="decisions")
    moderator = relationship("User")


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    responder_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    response_text = Column(Text, nullable=False)
    status = Column(String, default="SUBMITTED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="responses")
    responder = relationship("User")


class Appeal(Base):
    __tablename__ = "appeals"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    appellant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(Enum(AppealStatus), default=AppealStatus.SUBMITTED, nullable=False)
    decision_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case = relationship("Case", back_populates="appeals")
    appellant = relationship("User", foreign_keys=[appellant_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class ReputationReview(Base):
    __tablename__ = "reputation_reviews"
    __table_args__ = (UniqueConstraint("subject_id", "author_id", name="uq_subject_author_review"),)

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    score_type = Column(Enum(ExperienceType), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="reputation_reviews")
    case = relationship("Case")
    author = relationship("User")


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "subject_id", name="uq_user_subject_sub"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    subject = relationship("Subject", back_populates="subscriptions")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    object_type = Column(String, nullable=True)
    object_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String, default="PENDING", nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(Enum(SupportStatus), default=SupportStatus.OPEN, nullable=False)
    answer = Column(Text, nullable=True)
    answered_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    moderator = relationship("User", foreign_keys=[answered_by])


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    object_type = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(ExportStatus), default=ExportStatus.PENDING, nullable=False)
    file_path = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class AccountDeletionRequest(Base):
    __tablename__ = "account_deletion_requests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, default="PENDING", nullable=False)
    scheduled_for = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    is_private = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="reviews")
    author = relationship("User", back_populates="reviews")
