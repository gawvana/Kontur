"""
F01 — Saved Contacts: private contacts per user, independent of Subject
"""
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from db.database import get_db
from db.models import SavedContact, User
from schemas.models import (
    SavedContactCreate, SavedContactUpdate,
    SavedContactResponse, SavedContactListResponse
)
from api.deps import get_current_user

router = APIRouter()


def _normalize(raw: str) -> Optional[str]:
    """Normalize @username: lowercase, strip @."""
    if raw.startswith("@"):
        raw = raw[1:]
    if re.fullmatch(r"[a-zA-Z0-9_]{4,32}", raw):
        return raw.lower()
    return None


@router.get("", response_model=SavedContactListResponse)
async def list_contacts(
    search: Optional[str] = Query(None, max_length=128),
    favorite: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(SavedContact).where(SavedContact.user_id == current_user.id)
    if search:
        pattern = f"%{search.lower()}%"
        stmt = stmt.where(
            (SavedContact.normalized_username.like(pattern))
            | (SavedContact.display_name.ilike(f"%{search}%"))
        )
    if favorite is not None:
        stmt = stmt.where(SavedContact.is_favorite == favorite)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0
    result = await db.execute(stmt.order_by(SavedContact.is_pinned.desc(), SavedContact.created_at.desc()).offset(offset).limit(limit))
    items = result.scalars().all()
    return SavedContactListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=SavedContactResponse)
async def create_contact(
    body: SavedContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    normalized = _normalize(body.raw_input)
    contact = SavedContact(
        user_id=current_user.id,
        raw_input=body.raw_input,
        normalized_username=normalized,
        catalog_id=body.catalog_id,
        display_name=body.display_name,
        note=body.note,
        tags=body.tags,
        is_favorite=body.is_favorite,
        is_pinned=body.is_pinned,
        personal_rating=body.personal_rating,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=SavedContactResponse)
async def get_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contact = await db.scalar(
        select(SavedContact).where(SavedContact.id == contact_id, SavedContact.user_id == current_user.id)
    )
    if not contact:
        raise HTTPException(404, "Contact not found")
    return contact


@router.patch("/{contact_id}", response_model=SavedContactResponse)
async def update_contact(
    contact_id: int,
    body: SavedContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contact = await db.scalar(
        select(SavedContact).where(SavedContact.id == contact_id, SavedContact.user_id == current_user.id)
    )
    if not contact:
        raise HTTPException(404, "Contact not found")
    for attr, val in body.model_dump(exclude_none=True).items():
        setattr(contact, attr, val)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contact = await db.scalar(
        select(SavedContact).where(SavedContact.id == contact_id, SavedContact.user_id == current_user.id)
    )
    if not contact:
        raise HTTPException(404, "Contact not found")
    await db.delete(contact)
    await db.commit()
