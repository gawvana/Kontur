from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from db.models import (
    Role, CaseStatus, CaseVisibility, ExperienceType, CaseCategory,
    AppealStatus, DecisionType, EvidenceStatus, CatalogMemberRole,
    PersonalRating, SupportStatus, ExportStatus
)

# ----------------- Auth & User -----------------

class Token(BaseModel):
    access_token: str
    token_type: str

class UserBase(BaseModel):
    telegram_id: str
    role: Role

class UserResponse(UserBase):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_2fa_enabled: bool = False
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SessionResponse(BaseModel):
    id: str
    user_id: int
    expires_at: datetime
    is_revoked: bool
    user_agent: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TwoFactorSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    recovery_codes: List[str]

class TwoFactorVerifyRequest(BaseModel):
    code: str

# ----------------- Subjects & Reputation -----------------

class SubjectBase(BaseModel):
    telegram_id: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_verified: bool = False

class SubjectReputationSummary(BaseModel):
    positive_count: int = 0
    negative_count: int = 0
    total_cases: int = 0
    last_observed_at: Optional[datetime] = None

class SubjectSearchItem(BaseModel):
    id: int
    telegram_id: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_verified: bool = False
    reputation: SubjectReputationSummary
    model_config = ConfigDict(from_attributes=True)

class SubjectSearchResponse(BaseModel):
    items: List[SubjectSearchItem]
    total: int

class SubjectResponse(SubjectBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ObservationResponse(BaseModel):
    id: int
    raw_username: str
    normalized_username: str
    source: str
    observed_at: datetime
    is_verified: bool
    model_config = ConfigDict(from_attributes=True)

class PublishedReviewItem(BaseModel):
    id: int
    case_id: int
    author_pseudonym: str
    score_type: ExperienceType
    category: CaseCategory
    deal_date: Optional[datetime] = None
    result_description: Optional[str] = None
    outcome_note: Optional[str] = None
    created_at: datetime
    has_response: bool = False
    model_config = ConfigDict(from_attributes=True)

class SubjectCardDetailed(BaseModel):
    id: int
    telegram_id: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_verified: bool = False
    reputation: SubjectReputationSummary
    observations: List[ObservationResponse]
    published_reviews: List[PublishedReviewItem]
    private_note: Optional[str] = None
    is_subscribed: bool = False
    model_config = ConfigDict(from_attributes=True)

# ----------------- Catalogs & Contacts (F01, F05, F06) -----------------

class CatalogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=1000)
    is_private: bool = True

class CatalogUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=1000)
    is_private: Optional[bool] = None

class CatalogResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: Optional[str] = None
    is_private: bool
    contact_count: int = 0
    role: CatalogMemberRole = CatalogMemberRole.OWNER
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CatalogMemberResponse(BaseModel):
    id: int
    catalog_id: int
    user_id: int
    telegram_id: str
    username: Optional[str] = None
    role: CatalogMemberRole
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CatalogMemberUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: CatalogMemberRole

class CatalogInviteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: CatalogMemberRole = CatalogMemberRole.VIEWER
    expires_in_hours: int = Field(default=72, ge=1, le=720)

class CatalogInviteResponse(BaseModel):
    id: int
    catalog_id: int
    token: str
    role: CatalogMemberRole
    expires_at: datetime
    is_revoked: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Legacy CatalogItem
class CatalogItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    subject_id: int = Field(gt=0)
    note: Optional[str] = Field(None, max_length=10000)
    is_private: bool = True

class CatalogItemResponse(CatalogItemCreate):
    id: int
    catalog_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# SavedContact (F01: Private user contact independent of Subject)
class SavedContactCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    raw_input: str = Field(min_length=1, max_length=256)
    catalog_id: Optional[int] = None
    display_name: Optional[str] = Field(None, max_length=128)
    note: Optional[str] = Field(None, max_length=10000)
    tags: Optional[str] = Field(None, max_length=256)
    is_favorite: bool = False
    is_pinned: bool = False
    personal_rating: Optional[PersonalRating] = None

class SavedContactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    catalog_id: Optional[int] = None
    display_name: Optional[str] = Field(None, max_length=128)
    note: Optional[str] = Field(None, max_length=10000)
    tags: Optional[str] = Field(None, max_length=256)
    is_favorite: Optional[bool] = None
    is_pinned: Optional[bool] = None
    personal_rating: Optional[PersonalRating] = None

class SavedContactResponse(BaseModel):
    id: int
    user_id: int
    catalog_id: Optional[int] = None
    raw_input: str
    normalized_username: Optional[str] = None
    display_name: Optional[str] = None
    note: Optional[str] = None
    tags: Optional[str] = None
    is_favorite: bool
    is_pinned: bool
    personal_rating: Optional[PersonalRating] = None
    subject_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SavedContactListResponse(BaseModel):
    items: List[SavedContactResponse]
    total: int
    limit: int
    offset: int

# ----------------- Cases & Evidence & Decisions (F02, F03) -----------------

class CaseCreate(BaseModel):
    """Compatible with legacy POST /cases"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    subject_id: Optional[int] = None
    target_username: Optional[str] = None
    description: str = Field(min_length=1, max_length=20000)
    experience_type: ExperienceType = ExperienceType.NEGATIVE
    category: CaseCategory = CaseCategory.SERVICE
    deal_date: Optional[datetime] = None
    agreed_terms: Optional[str] = None
    author_actions: Optional[str] = None
    result_description: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None
    violation_details: Optional[str] = None

class CaseSupplement(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    changelog: Optional[str] = Field(None, max_length=1000)
    agreed_terms: Optional[str] = Field(None, max_length=10000)
    author_actions: Optional[str] = Field(None, max_length=10000)
    result_description: Optional[str] = Field(None, max_length=10000)
    violation_details: Optional[str] = Field(None, max_length=10000)

class CaseDraftSave(BaseModel):
    target_username: Optional[str] = None
    experience_type: Optional[ExperienceType] = None
    category: Optional[CaseCategory] = None
    deal_date: Optional[datetime] = None
    agreed_terms: Optional[str] = None
    author_actions: Optional[str] = None
    result_description: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None
    violation_details: Optional[str] = None
    description: Optional[str] = None
    step: int = 1

class EvidenceResponse(BaseModel):
    id: int
    case_id: int
    uploader_id: int
    file_name: str
    file_size: int
    mime_type: str
    file_hash: str
    author_explanation: Optional[str] = None
    status: EvidenceStatus
    is_published: bool
    created_at: datetime
    download_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ContentVersionResponse(BaseModel):
    id: int
    case_id: int
    version_num: int
    author_id: int
    changelog: Optional[str] = None
    agreed_terms: Optional[str] = None
    author_actions: Optional[str] = None
    result_description: Optional[str] = None
    violation_details: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    decision: DecisionType
    reason: str = Field(min_length=5, max_length=5000)
    limitations_note: Optional[str] = Field(None, max_length=2000)
    content_version: int = 1

class DecisionResponse(BaseModel):
    id: int
    case_id: int
    moderator_id: int
    decision: DecisionType
    reason: str
    limitations_note: Optional[str] = None
    content_version: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ResponseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    response_text: str = Field(min_length=20, max_length=10000)

class ResponseResponse(BaseModel):
    id: int
    case_id: int
    responder_id: int
    response_text: str
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AppealCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str = Field(min_length=20, max_length=5000)

class AppealDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: AppealStatus
    decision_note: str = Field(min_length=5, max_length=5000)

class AppealResponse(BaseModel):
    id: int
    case_id: int
    appellant_id: int
    reviewer_id: Optional[int] = None
    reason: str
    status: AppealStatus
    decision_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CaseResponse(BaseModel):
    id: int
    creator_id: int
    subject_id: Optional[int] = None
    target_username: Optional[str] = None
    experience_type: ExperienceType = ExperienceType.NEGATIVE
    category: CaseCategory = CaseCategory.SERVICE
    deal_date: Optional[datetime] = None
    agreed_terms: Optional[str] = None
    author_actions: Optional[str] = None
    result_description: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None
    violation_details: Optional[str] = None
    status: CaseStatus
    visibility: CaseVisibility = CaseVisibility.PRIVATE
    description: str
    current_version: int = 1
    outcome_note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class CaseDetailResponse(CaseResponse):
    versions: List[ContentVersionResponse] = []
    decisions: List[DecisionResponse] = []
    responses: List[ResponseResponse] = []
    appeals: List[AppealResponse] = []

# ----------------- Notifications & Subscriptions -----------------

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    event_type: str
    title: str
    message: str
    object_type: Optional[str] = None
    object_id: Optional[int] = None
    is_read: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    subject_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ----------------- Support -----------------

class SupportTicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    subject: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=10, max_length=5000)

class SupportTicketAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    answer: str = Field(min_length=5, max_length=5000)

class SupportTicketResponse(BaseModel):
    id: int
    user_id: int
    subject: str
    message: str
    status: SupportStatus
    answer: Optional[str] = None
    answered_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ----------------- Import / Export -----------------

class ImportPreviewItem(BaseModel):
    raw_input: str
    display_name: Optional[str] = None
    note: Optional[str] = None
    tags: Optional[str] = None

class ImportPreviewResponse(BaseModel):
    items: List[ImportPreviewItem]
    total_count: int
    errors: List[str] = []

class ImportCommitRequest(BaseModel):
    catalog_id: Optional[int] = None
    items: List[ImportPreviewItem]
    duplicate_strategy: str = "skip" # "skip", "create_copy"

class ImportCommitResponse(BaseModel):
    imported_count: int
    skipped_count: int

class ExportJobResponse(BaseModel):
    id: int
    status: ExportStatus
    file_path: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ----------------- Admin -----------------

class AdminDashboardStats(BaseModel):
    pending_cases_count: int
    pending_appeals_count: int
    open_support_count: int
    quarantined_evidence_count: int
    total_users_count: int
    total_subjects_count: int

class UserRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    role: Role
    reason: str = Field(min_length=5, max_length=500)

class AuditLogResponse(BaseModel):
    id: int
    actor_id: Optional[int] = None
    action: str
    object_type: str
    object_id: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
