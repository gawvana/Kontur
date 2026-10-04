"""
Catalog members and invites: shared catalogs.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from typing import List

from db.database import get_db
from db.models import Catalog, CatalogItem, CatalogMember, CatalogInvite, User, Subject, CatalogMemberRole
from schemas.models import (
    CatalogCreate, CatalogUpdate, CatalogResponse, CatalogItemCreate, CatalogItemResponse,
    CatalogMemberResponse, CatalogMemberUpdate, CatalogInviteCreate, CatalogInviteResponse
)
from api.deps import get_current_user
from api.v1.subjects import visible_to

router = APIRouter()


def _is_member(catalog: Catalog, user: User) -> Optional[CatalogMemberRole]:
    """Returns member role if user can access this catalog."""
    if catalog.owner_id == user.id:
        return CatalogMemberRole.OWNER
    return None


async def _resolve_catalog(db: AsyncSession, catalog_id: int, user: User, require_editor: bool = False) -> Catalog:
    """Resolve catalog owned by or shared with user."""
    catalog = await db.scalar(
        select(Catalog).where(Catalog.id == catalog_id)
    )
    if not catalog:
        raise HTTPException(404, "Catalog not found")
    if catalog.owner_id == user.id:
        return catalog
    # Check membership
    member = await db.scalar(
        select(CatalogMember).where(CatalogMember.catalog_id == catalog_id, CatalogMember.user_id == user.id)
    )
    if not member:
        raise HTTPException(404, "Catalog not found")
    if require_editor and member.role == CatalogMemberRole.VIEWER:
        raise HTTPException(403, "Editor permission required")
    return catalog


@router.get("", response_model=List[CatalogResponse])
async def get_my_catalogs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Catalog).where(Catalog.owner_id == current_user.id).order_by(Catalog.id).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=CatalogResponse)
async def create_catalog(
    catalog_in: CatalogCreate,
    idempotency_key: str = Header(min_length=1, max_length=128),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Catalog).where(Catalog.owner_id == current_user.id, Catalog.idempotency_key == idempotency_key)

    def replay(previous):
        if previous.name != catalog_in.name or previous.is_private != catalog_in.is_private:
            raise HTTPException(409, "Idempotency key already used with different content")
        return previous

    previous = await db.scalar(stmt)
    if previous:
        return replay(previous)
    catalog = Catalog(**catalog_in.model_dump(), owner_id=current_user.id, idempotency_key=idempotency_key)
    db.add(catalog)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        previous = await db.scalar(stmt)
        if previous is None:
            raise HTTPException(409, "Conflicting data") from None
        return replay(previous)
    await db.refresh(catalog)
    return catalog


@router.patch("/{id}", response_model=CatalogResponse)
async def update_catalog(
    id: int,
    body: CatalogUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    catalog = await db.scalar(select(Catalog).where(Catalog.id == id, Catalog.owner_id == current_user.id))
    if not catalog:
        raise HTTPException(404, "Catalog not found")
    for attr, val in body.model_dump(exclude_none=True).items():
        setattr(catalog, attr, val)
    await db.commit()
    await db.refresh(catalog)
    return catalog


@router.delete("/{id}", status_code=204)
async def delete_catalog(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    catalog = await db.scalar(select(Catalog).where(Catalog.id == id, Catalog.owner_id == current_user.id))
    if not catalog:
        raise HTTPException(404, "Catalog not found")
    await db.delete(catalog)
    await db.commit()


# ── Contacts (CatalogItems) ───────────────────────────────────────────────────

@router.post("/{id}/contacts", response_model=CatalogItemResponse)
async def add_contact_to_catalog(
    id: int,
    item_in: CatalogItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _resolve_catalog(db, id, current_user, require_editor=True)
    subject = await db.scalar(select(Subject).where(Subject.id == item_in.subject_id, visible_to(current_user)))
    if not subject:
        raise HTTPException(404, "Subject not found")

    stmt = select(CatalogItem).where(CatalogItem.catalog_id == id, CatalogItem.subject_id == item_in.subject_id)

    def replay(previous):
        if previous.note != item_in.note or previous.is_private != item_in.is_private:
            raise HTTPException(409, "Contact already exists; note was not overwritten")
        return previous

    previous = await db.scalar(stmt)
    if previous:
        return replay(previous)
    item = CatalogItem(**item_in.model_dump(), catalog_id=id)
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        previous = await db.scalar(stmt)
        if previous is None:
            raise HTTPException(409, "Conflicting data") from None
        return replay(previous)
    await db.refresh(item)
    return item


@router.get("/{id}/contacts", response_model=List[CatalogItemResponse])
async def get_contacts(
    id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _resolve_catalog(db, id, current_user)
    result = await db.execute(
        select(CatalogItem).where(CatalogItem.catalog_id == id).order_by(CatalogItem.id).offset(offset).limit(limit)
    )
    return result.scalars().all()


# ── Members ───────────────────────────────────────────────────────────────────

@router.get("/{id}/members", response_model=List[CatalogMemberResponse])
async def list_members(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _resolve_catalog(db, id, current_user)
    result = await db.execute(
        select(CatalogMember, User).join(User, CatalogMember.user_id == User.id)
        .where(CatalogMember.catalog_id == id)
    )
    rows = result.all()
    out = []
    for member, user in rows:
        out.append(CatalogMemberResponse(
            id=member.id, catalog_id=member.catalog_id, user_id=member.user_id,
            telegram_id=user.telegram_id, username=user.username,
            role=member.role, created_at=member.created_at
        ))
    return out


@router.patch("/{id}/members/{user_id}", response_model=CatalogMemberResponse)
async def update_member_role(
    id: int,
    user_id: int,
    body: CatalogMemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only catalog owner may change roles
    catalog = await db.scalar(select(Catalog).where(Catalog.id == id, Catalog.owner_id == current_user.id))
    if not catalog:
        raise HTTPException(403, "Only catalog owner can manage members")
    member = await db.scalar(
        select(CatalogMember).where(CatalogMember.catalog_id == id, CatalogMember.user_id == user_id)
    )
    if not member:
        raise HTTPException(404, "Member not found")
    member.role = body.role
    await db.commit()
    await db.refresh(member)
    target_user = await db.scalar(select(User).where(User.id == user_id))
    return CatalogMemberResponse(
        id=member.id, catalog_id=member.catalog_id, user_id=member.user_id,
        telegram_id=target_user.telegram_id, username=target_user.username,
        role=member.role, created_at=member.created_at
    )


@router.delete("/{id}/members/{user_id}", status_code=204)
async def remove_member(
    id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    catalog = await db.scalar(select(Catalog).where(Catalog.id == id, Catalog.owner_id == current_user.id))
    if not catalog:
        raise HTTPException(403, "Only catalog owner can manage members")
    member = await db.scalar(
        select(CatalogMember).where(CatalogMember.catalog_id == id, CatalogMember.user_id == user_id)
    )
    if not member:
        raise HTTPException(404, "Member not found")
    await db.delete(member)
    await db.commit()


# ── Invites ───────────────────────────────────────────────────────────────────

@router.post("/{id}/invites", response_model=CatalogInviteResponse)
async def create_invite(
    id: int,
    body: CatalogInviteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    catalog = await db.scalar(select(Catalog).where(Catalog.id == id, Catalog.owner_id == current_user.id))
    if not catalog:
        raise HTTPException(403, "Only catalog owner can create invites")
    token = uuid.uuid4().hex + uuid.uuid4().hex  # 64 chars
    invite = CatalogInvite(
        catalog_id=id,
        inviter_id=current_user.id,
        token=token,
        role=body.role,
        expires_at=datetime.utcnow() + timedelta(hours=body.expires_in_hours)
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite


@router.post("/join/{token}", response_model=CatalogMemberResponse)
async def accept_invite(
    token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invite = await db.scalar(
        select(CatalogInvite).where(
            CatalogInvite.token == token,
            CatalogInvite.is_revoked.is_(False)
        )
    )
    if not invite or invite.expires_at < datetime.utcnow():
        raise HTTPException(404, "Invite not found or expired")

    # Check not already a member
    existing = await db.scalar(
        select(CatalogMember).where(
            CatalogMember.catalog_id == invite.catalog_id,
            CatalogMember.user_id == current_user.id
        )
    )
    if existing:
        catalog = await db.scalar(select(Catalog).where(Catalog.id == invite.catalog_id))
        if catalog and catalog.owner_id == current_user.id:
            raise HTTPException(409, "You are already the owner of this catalog")
        raise HTTPException(409, "Already a member of this catalog")

    member = CatalogMember(
        catalog_id=invite.catalog_id,
        user_id=current_user.id,
        role=invite.role
    )
    db.add(member)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Already a member") from None
    await db.refresh(member)
    return CatalogMemberResponse(
        id=member.id, catalog_id=member.catalog_id, user_id=member.user_id,
        telegram_id=current_user.telegram_id, username=current_user.username,
        role=member.role, created_at=member.created_at
    )
