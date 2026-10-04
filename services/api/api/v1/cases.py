import json
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from db.database import get_db
from db.models import (
    Case, User, CaseStatus, CaseVisibility, Subject, Evidence, Decision,
    Response as CaseResponse_DB, Appeal, ContentVersion, ReputationReview,
    Notification, OutboxEvent, AppealStatus, DecisionType, ExperienceType
)
from schemas.models import (
    CaseCreate, CaseResponse, CaseDraftSave, CaseSupplement,
    EvidenceResponse, DecisionCreate, DecisionResponse,
    ResponseCreate, ResponseResponse, AppealCreate, AppealDecision, AppealResponse
)
from api.deps import get_current_user, get_current_staff_user

router = APIRouter()

def case_visible(case: Case, current_user: User) -> bool:
    """Evaluate if a user may read a case."""
    if case.creator_id == current_user.id:
        return True
    if case.visibility == CaseVisibility.PUBLISHED:
        return True
    return False


@router.post("", response_model=CaseResponse)
async def create_case(
    case_in: CaseCreate,
    idempotency_key: str = Header(min_length=1, max_length=128),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Case).where(Case.creator_id == current_user.id, Case.idempotency_key == idempotency_key)
    previous = await db.scalar(stmt)
    if previous:
        if (previous.subject_id != case_in.subject_id or previous.description != case_in.description):
            raise HTTPException(409, "Idempotency key already used with different content")
        return previous

    data = case_in.model_dump()
    subject = None
    if data.get("subject_id"):
        from api.v1.subjects import visible_to
        subject = await db.scalar(select(Subject).where(Subject.id == data["subject_id"], visible_to(current_user)))
        if not subject:
            raise HTTPException(404, "Subject not found")
        if subject.telegram_id == current_user.telegram_id:
            raise HTTPException(422, "Self reviews are not allowed")

    data.pop("subject_id", None)
    case = Case(
        **data,
        subject_id=case_in.subject_id,
        creator_id=current_user.id,
        status=CaseStatus.PENDING,
        idempotency_key=idempotency_key
    )
    db.add(case)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        previous = await db.scalar(stmt)
        if previous is None:
            raise HTTPException(409, "Conflicting data") from None
        if previous.subject_id != case_in.subject_id or previous.description != case_in.description:
            raise HTTPException(409, "Idempotency key already used with different content")
        return previous
    await db.refresh(case)
    return case


@router.post("/draft", response_model=CaseResponse)
async def save_case_draft(
    draft: CaseDraftSave,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save a draft case (step-by-step form autosave)."""
    case = Case(
        creator_id=current_user.id,
        status=CaseStatus.DRAFT,
        description=draft.description or "",
        target_username=draft.target_username,
        experience_type=draft.experience_type or ExperienceType.NEGATIVE,
        category=draft.category,
        deal_date=draft.deal_date,
        agreed_terms=draft.agreed_terms,
        author_actions=draft.author_actions,
        result_description=draft.result_description,
        amount=draft.amount,
        currency=draft.currency,
        violation_details=draft.violation_details,
        idempotency_key=uuid.uuid4().hex,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return case


@router.put("/{case_id}/draft", response_model=CaseResponse)
async def update_case_draft(
    case_id: int,
    draft: CaseDraftSave,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = await db.scalar(
        select(Case).where(Case.id == case_id, Case.creator_id == current_user.id, Case.status == CaseStatus.DRAFT)
    )
    if not case:
        raise HTTPException(404, "Draft case not found")

    update_data = {k: v for k, v in draft.model_dump().items() if v is not None}
    for attr, value in update_data.items():
        setattr(case, attr, value)
    await db.commit()
    await db.refresh(case)
    return case


@router.post("/{case_id}/submit", response_model=CaseResponse)
async def submit_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a draft case for moderation review."""
    case = await db.scalar(
        select(Case).where(Case.id == case_id, Case.creator_id == current_user.id, Case.status == CaseStatus.DRAFT)
    )
    if not case:
        raise HTTPException(404, "Draft case not found or already submitted")
    if not case.description or len(case.description.strip()) < 20:
        raise HTTPException(422, "Description must be at least 20 characters")

    case.status = CaseStatus.SUBMITTED
    await db.commit()
    await db.refresh(case)
    return case


@router.post("/{case_id}/withdraw", response_model=CaseResponse)
async def withdraw_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Withdraw a pending or submitted case (before moderation)."""
    case = await db.scalar(
        select(Case).where(Case.id == case_id, Case.creator_id == current_user.id)
    )
    if not case:
        raise HTTPException(404, "Case not found")
    if case.status not in (CaseStatus.PENDING, CaseStatus.SUBMITTED, CaseStatus.DRAFT):
        raise HTTPException(422, f"Cannot withdraw case in status: {case.status.value}")
    case.status = CaseStatus.WITHDRAWN
    await db.commit()
    await db.refresh(case)
    return case


@router.get("/my", response_model=list[CaseResponse])
async def get_my_cases(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Case).where(Case.creator_id == current_user.id).order_by(Case.created_at.desc()).offset(offset).limit(limit)
    )
    return result.scalars().all()


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = await db.scalar(select(Case).where(Case.id == case_id))
    if not case or not case_visible(case, current_user):
        raise HTTPException(404, "Case not found")
    return case


@router.post("/{case_id}/supplement", response_model=CaseResponse)
async def supplement_case(
    case_id: int,
    sup: CaseSupplement,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a supplemental version of case content (requires re-review by moderator).
    """
    case = await db.scalar(
        select(Case).where(Case.id == case_id, Case.creator_id == current_user.id)
    )
    if not case:
        raise HTTPException(404, "Case not found")
    if case.status in (CaseStatus.WITHDRAWN, CaseStatus.DRAFT):
        raise HTTPException(422, "Cannot supplement a withdrawn or draft case")

    version_num = case.current_version + 1
    version = ContentVersion(
        case_id=case.id,
        version_num=version_num,
        author_id=current_user.id,
        changelog=sup.changelog,
        agreed_terms=sup.agreed_terms,
        author_actions=sup.author_actions,
        result_description=sup.result_description,
        violation_details=sup.violation_details
    )
    db.add(version)
    case.current_version = version_num
    if case.status == CaseStatus.APPROVED:
        case.status = CaseStatus.IN_REVIEW
    if sup.agreed_terms:
        case.agreed_terms = sup.agreed_terms
    if sup.author_actions:
        case.author_actions = sup.author_actions
    if sup.result_description:
        case.result_description = sup.result_description
    if sup.violation_details:
        case.violation_details = sup.violation_details

    await db.commit()
    await db.refresh(case)
    return case


@router.post("/{case_id}/response", response_model=ResponseResponse)
async def respond_to_case(
    case_id: int,
    body: ResponseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    The subject of a case (the person it is about) may respond to a published case.
    """
    case = await db.scalar(select(Case).where(Case.id == case_id))
    if not case or case.visibility != CaseVisibility.PUBLISHED:
        raise HTTPException(404, "Published case not found")

    if case.creator_id == current_user.id:
        raise HTTPException(422, "Case author cannot respond to their own case")

    # Must be the subject of the case
    if case.subject_id:
        subject = await db.scalar(select(Subject).where(Subject.id == case.subject_id, Subject.telegram_id == current_user.telegram_id))
        if not subject:
            raise HTTPException(403, "Only the subject of this case may respond")

    response_obj = CaseResponse_DB(
        case_id=case.id,
        responder_id=current_user.id,
        response_text=body.response_text,
        status="SUBMITTED"
    )
    db.add(response_obj)
    await db.commit()
    await db.refresh(response_obj)
    return response_obj


@router.post("/{case_id}/appeal", response_model=AppealResponse)
async def submit_appeal(
    case_id: int,
    body: AppealCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creator or subject of a decided case may appeal the decision.
    """
    case = await db.scalar(select(Case).where(Case.id == case_id))
    if not case:
        raise HTTPException(404, "Case not found")
    if case.status not in (CaseStatus.APPROVED, CaseStatus.REJECTED, CaseStatus.RESOLVED):
        raise HTTPException(422, f"Cannot appeal a case with status: {case.status.value}")
    if case.creator_id != current_user.id:
        # Also allow subject to appeal
        if case.subject_id:
            subject = await db.scalar(select(Subject).where(Subject.id == case.subject_id, Subject.telegram_id == current_user.telegram_id))
            if not subject:
                raise HTTPException(403, "Only the case creator or subject may appeal")
        else:
            raise HTTPException(403, "Only the case creator may appeal this case")

    # Prevent duplicate appeals
    existing = await db.scalar(
        select(Appeal).where(
            Appeal.case_id == case.id,
            Appeal.appellant_id == current_user.id,
            Appeal.status.not_in([AppealStatus.REJECTED, AppealStatus.RETURNED])
        )
    )
    if existing:
        raise HTTPException(409, "An active appeal already exists for this case")

    appeal = Appeal(
        case_id=case.id,
        appellant_id=current_user.id,
        reason=body.reason,
        status=AppealStatus.SUBMITTED
    )
    db.add(appeal)
    await db.commit()
    await db.refresh(appeal)
    return appeal


@router.get("/appeals/my", response_model=list[AppealResponse])
async def get_my_appeals(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Appeal).where(Appeal.appellant_id == current_user.id).order_by(Appeal.created_at.desc()).offset(offset).limit(limit)
    )
    return result.scalars().all()
