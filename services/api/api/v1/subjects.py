import re
from urllib.parse import urlsplit
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, exists, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import (
    Subject, User, Catalog, CatalogItem, Case, SavedContact,
    ReputationReview, UsernameObservation, Subscription, CaseVisibility,
    ExperienceType
)
from schemas.models import (
    SubjectResponse, SubjectCardDetailed, SubjectReputationSummary,
    ObservationResponse, PublishedReviewItem
)
from api.deps import get_current_user

router = APIRouter()

def visible_to(user: User):
    """
    Subject is visible if:
    1. It belongs to user's own telegram_id.
    2. User has it in their private catalogs/contacts.
    3. User has a case involving this subject.
    4. OR it has publicly published reviews / cases / is verified.
    Unpublished subjects that only exist as another user's private contact are completely hidden (404/empty).
    """
    owned_item = exists(
        select(CatalogItem.id).join(Catalog, Catalog.id == CatalogItem.catalog_id).where(
            CatalogItem.subject_id == Subject.id, Catalog.owner_id == user.id
        )
    )
    owned_saved = exists(
        select(SavedContact.id).where(
            SavedContact.subject_id == Subject.id, SavedContact.user_id == user.id
        )
    )
    own_case = exists(
        select(Case.id).where(Case.subject_id == Subject.id, Case.creator_id == user.id)
    )
    is_public = or_(
        Subject.is_verified.is_(True),
        exists(select(ReputationReview.id).where(
            ReputationReview.subject_id == Subject.id,
            ReputationReview.is_active.is_(True)
        )),
        exists(select(Case.id).where(
            Case.subject_id == Subject.id,
            Case.visibility == CaseVisibility.PUBLISHED
        ))
    )
    return or_(Subject.telegram_id == user.telegram_id, owned_item, owned_saved, own_case, is_public)

def normalize_query(value: str) -> str:
    value = value.strip()
    if "://" in value:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or parsed.netloc.lower() not in {"t.me", "telegram.me"} or parsed.query or parsed.fragment:
            raise HTTPException(422, "Use a Telegram profile username or HTTPS profile link")
        value = parsed.path.lstrip("/")
    value = value.removeprefix("@").lower()
    if not re.fullmatch(r"[a-z][a-z0-9_]{4,31}", value):
        raise HTTPException(422, "Invalid Telegram username")
    return value

async def get_reputation_summary(db: AsyncSession, subject_id: int) -> SubjectReputationSummary:
    pos_count = await db.scalar(
        select(func.count(func.distinct(ReputationReview.author_id))).where(
            ReputationReview.subject_id == subject_id,
            ReputationReview.score_type == ExperienceType.POSITIVE,
            ReputationReview.is_active.is_(True)
        )
    ) or 0

    neg_count = await db.scalar(
        select(func.count(func.distinct(ReputationReview.author_id))).where(
            ReputationReview.subject_id == subject_id,
            ReputationReview.score_type == ExperienceType.NEGATIVE,
            ReputationReview.is_active.is_(True)
        )
    ) or 0

    cases_count = await db.scalar(
        select(func.count(Case.id)).where(
            Case.subject_id == subject_id,
            Case.visibility == CaseVisibility.PUBLISHED
        )
    ) or 0

    last_obs = await db.scalar(
        select(func.max(UsernameObservation.observed_at)).where(UsernameObservation.subject_id == subject_id)
    )

    return SubjectReputationSummary(
        positive_count=pos_count,
        negative_count=neg_count,
        total_cases=cases_count,
        last_observed_at=last_obs
    )

@router.get("/search", response_model=list[SubjectResponse])
async def search_subjects(
    q: str = Query(min_length=1, max_length=256),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    username = normalize_query(q)
    result = await db.execute(
        select(Subject).where(
            visible_to(current_user),
            func.lower(Subject.username) == username
        ).order_by(Subject.id).limit(50)
    )
    return result.scalars().all()

@router.get("/{id}", response_model=SubjectResponse)
async def get_subject(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subject = await db.scalar(select(Subject).where(Subject.id == id, visible_to(current_user)))
    if subject is None:
        raise HTTPException(404, "Subject not found")
    return subject

@router.get("/{id}/card", response_model=SubjectCardDetailed)
async def get_subject_card(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subject = await db.scalar(select(Subject).where(Subject.id == id, visible_to(current_user)))
    if subject is None:
        raise HTTPException(404, "Subject not found")

    rep_summary = await get_reputation_summary(db, subject.id)

    # Observations
    obs_res = await db.scalars(
        select(UsernameObservation).where(UsernameObservation.subject_id == subject.id).order_by(UsernameObservation.observed_at.desc())
    )
    obs = [ObservationResponse.model_validate(o) for o in obs_res.all()]

    # Published reviews
    cases_res = await db.scalars(
        select(Case).where(Case.subject_id == subject.id, Case.visibility == CaseVisibility.PUBLISHED).order_by(Case.created_at.desc())
    )
    published_items = []
    for c in cases_res.all():
        published_items.append(
            PublishedReviewItem(
                id=c.id,
                case_id=c.id,
                author_pseudonym=f"Автор {c.creator_id:02d}",
                score_type=c.experience_type,
                category=c.category,
                deal_date=c.deal_date,
                result_description=c.result_description or c.description,
                outcome_note=c.outcome_note,
                created_at=c.created_at,
                has_response=len(c.responses) > 0 if hasattr(c, "responses") else False
            )
        )

    # User's own private note for this subject (if any)
    private_note = None
    saved = await db.scalar(
        select(SavedContact.note).where(SavedContact.subject_id == subject.id, SavedContact.user_id == current_user.id)
    )
    if saved:
        private_note = saved
    else:
        cat_note = await db.scalar(
            select(CatalogItem.note).join(Catalog, Catalog.id == CatalogItem.catalog_id).where(
                CatalogItem.subject_id == subject.id, Catalog.owner_id == current_user.id
            )
        )
        if cat_note:
            private_note = cat_note

    # Subscription status
    is_sub = await db.scalar(
        select(exists().where(Subscription.user_id == current_user.id, Subscription.subject_id == subject.id))
    )

    return SubjectCardDetailed(
        id=subject.id,
        telegram_id=subject.telegram_id if subject.telegram_id == current_user.telegram_id else None,
        username=subject.username,
        first_name=subject.first_name,
        last_name=subject.last_name,
        is_verified=subject.is_verified,
        reputation=rep_summary,
        observations=obs,
        published_reviews=published_items,
        private_note=private_note,
        is_subscribed=bool(is_sub)
    )

@router.post("/{id}/subscribe", status_code=204)
async def subscribe_subject(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subject = await db.scalar(select(Subject).where(Subject.id == id, visible_to(current_user)))
    if subject is None:
        raise HTTPException(404, "Subject not found")

    existing = await db.scalar(
        select(Subscription).where(Subscription.user_id == current_user.id, Subscription.subject_id == subject.id)
    )
    if not existing:
        db.add(Subscription(user_id=current_user.id, subject_id=subject.id))
        await db.commit()

@router.delete("/{id}/subscribe", status_code=204)
async def unsubscribe_subject(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sub = await db.scalar(
        select(Subscription).where(Subscription.user_id == current_user.id, Subscription.subject_id == id)
    )
    if sub:
        await db.delete(sub)
        await db.commit()
