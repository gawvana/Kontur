"""
Support tickets: user-facing submission and viewing own tickets.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from db.models import SupportTicket, User, SupportStatus
from schemas.models import SupportTicketCreate, SupportTicketResponse
from api.deps import get_current_user

router = APIRouter()


@router.post("", response_model=SupportTicketResponse)
async def create_ticket(
    body: SupportTicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = SupportTicket(
        user_id=current_user.id,
        subject=body.subject,
        message=body.message,
        status=SupportStatus.OPEN
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.get("", response_model=list[SupportTicketResponse])
async def list_my_tickets(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(SupportTicket)
        .where(SupportTicket.user_id == current_user.id)
        .order_by(SupportTicket.created_at.desc())
        .offset(offset).limit(limit)
    )
    return result.scalars().all()


@router.get("/{ticket_id}", response_model=SupportTicketResponse)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = await db.scalar(
        select(SupportTicket).where(SupportTicket.id == ticket_id, SupportTicket.user_id == current_user.id)
    )
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return ticket
