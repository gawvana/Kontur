"""
Admin panel API: dashboard, moderation queue, decisions, appeals,
user role management, support tickets, audit log, evidence queue.
"""
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from db.database import get_db
from db.models import (
    Case, User, Subject, Appeal, SupportTicket, Evidence, AuditLog,
    CaseStatus, EvidenceStatus, AppealStatus, SupportStatus, Role, Decision,
    DecisionType, Notification
)
from schemas.models import (
    CaseResponse, DecisionCreate, DecisionResponse,
    AppealDecision, AppealResponse,
    SupportTicketAnswer, SupportTicketResponse,
    AdminDashboardStats, UserRoleUpdate, AuditLogResponse, EvidenceResponse
)
from api.deps import get_current_staff_user, get_current_admin_user, get_current_user

router = APIRouter()


async def _audit(db: AsyncSession, actor_id: int, action: str, obj_type: str, obj_id, details=None, ip=None):
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        object_type=obj_type,
        object_id=str(obj_id),
        details=json.dumps(details) if details else None,
        ip_address=ip
    )
    db.add(entry)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=AdminDashboardStats)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(get_current_staff_user)
):
    async def count(stmt):
        return await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    pending_cases = await count(select(Case).where(Case.status.in_([CaseStatus.PENDING, CaseStatus.SUBMITTED, CaseStatus.IN_REVIEW])))
    pending_appeals = await count(select(Appeal).where(Appeal.status.in_([AppealStatus.SUBMITTED, AppealStatus.IN_REVIEW])))
    open_support = await count(select(SupportTicket).where(SupportTicket.status == SupportStatus.OPEN))
    quarantine_evidence = await count(select(Evidence).where(Evidence.status == EvidenceStatus.QUARANTINED))
    total_users = await count(select(User))
    total_subjects = await count(select(Subject))

    return AdminDashboardStats(
        pending_cases_count=pending_cases,
        pending_appeals_count=pending_appeals,
        open_support_count=open_support,
        quarantined_evidence_count=quarantine_evidence,
        total_users_count=total_users,
        total_subjects_count=total_subjects,
    )


# ── Moderation Queue ──────────────────────────────────────────────────────────

@router.get("/cases", response_model=list[CaseResponse])
async def moderation_queue(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(get_current_staff_user)
):
    stmt = select(Case)
    if status:
        try:
            stmt = stmt.where(Case.status == CaseStatus(status.upper()))
        except ValueError:
            raise HTTPException(422, f"Unknown status: {status}")
    else:
        stmt = stmt.where(Case.status.in_([CaseStatus.SUBMITTED, CaseStatus.IN_REVIEW]))
    result = await db.execute(stmt.order_by(Case.created_at).offset(offset).limit(limit))
    return result.scalars().all()


@router.post("/cases/{case_id}/decision", response_model=DecisionResponse)
async def create_decision(
    case_id: int,
    body: DecisionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(get_current_staff_user)
):
    case = await db.scalar(select(Case).where(Case.id == case_id))
    if not case:
        raise HTTPException(404, "Case not found")
    if case.status not in (CaseStatus.SUBMITTED, CaseStatus.IN_REVIEW, CaseStatus.NEEDS_INFO):
        raise HTTPException(422, f"Cannot decide case in status: {case.status.value}")

    # Map decision to resulting case status and visibility
    if body.decision == DecisionType.APPROVE:
        case.status = CaseStatus.APPROVED
        from db.models import CaseVisibility
        case.visibility = CaseVisibility.PUBLISHED
    elif body.decision == DecisionType.REJECT:
        case.status = CaseStatus.REJECTED
    elif body.decision == DecisionType.REQUEST_INFO:
        case.status = CaseStatus.NEEDS_INFO
    elif body.decision == DecisionType.HIDE:
        from db.models import CaseVisibility
        case.visibility = CaseVisibility.HIDDEN
    elif body.decision == DecisionType.RESTORE:
        from db.models import CaseVisibility
        case.visibility = CaseVisibility.PUBLISHED

    decision = Decision(
        case_id=case.id,
        moderator_id=staff.id,
        decision=body.decision,
        reason=body.reason,
        limitations_note=body.limitations_note,
        content_version=case.current_version
    )
    db.add(decision)

    # Notify case creator
    db.add(Notification(
        user_id=case.creator_id,
        event_type="CASE_DECISION",
        title=f"Решение по обращению #{case.id}",
        message=f"Ваше обращение {body.decision.value.lower()}: {body.reason[:200]}",
        object_type="Case",
        object_id=case.id
    ))

    await _audit(db, staff.id, "DECISION", "Case", case.id, {"decision": body.decision.value}, request.client.host if request.client else None)
    await db.commit()
    await db.refresh(decision)
    return decision


# ── Appeals ───────────────────────────────────────────────────────────────────

@router.get("/appeals", response_model=list[AppealResponse])
async def list_appeals(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(get_current_staff_user)
):
    result = await db.execute(
        select(Appeal).where(Appeal.status.in_([AppealStatus.SUBMITTED, AppealStatus.IN_REVIEW]))
        .order_by(Appeal.created_at).offset(offset).limit(limit)
    )
    return result.scalars().all()


@router.post("/appeals/{appeal_id}/decide", response_model=AppealResponse)
async def decide_appeal(
    appeal_id: int,
    body: AppealDecision,
    request: Request,
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(get_current_staff_user)
):
    # Senior moderator or above for appeal decisions
    if staff.role not in (Role.SENIOR_MODERATOR, Role.ADMIN, Role.OWNER):
        raise HTTPException(403, "Senior moderator or above required for appeal decisions")

    appeal = await db.scalar(select(Appeal).where(Appeal.id == appeal_id))
    if not appeal:
        raise HTTPException(404, "Appeal not found")
    if appeal.status in (AppealStatus.UPHELD, AppealStatus.OVERTURNED, AppealStatus.REJECTED):
        raise HTTPException(422, f"Appeal already decided: {appeal.status.value}")

    appeal.status = body.status
    appeal.decision_note = body.decision_note
    appeal.reviewer_id = staff.id

    # Notify appellant
    db.add(Notification(
        user_id=appeal.appellant_id,
        event_type="APPEAL_DECISION",
        title=f"Решение по апелляции #{appeal.id}",
        message=f"Апелляция {body.status.value.lower()}: {body.decision_note[:200]}",
        object_type="Appeal",
        object_id=appeal.id
    ))

    await _audit(db, staff.id, "APPEAL_DECISION", "Appeal", appeal.id, {"status": body.status.value}, request.client.host if request.client else None)
    await db.commit()
    await db.refresh(appeal)
    return appeal


# ── Evidence moderation ───────────────────────────────────────────────────────

@router.get("/evidence/queue", response_model=list[EvidenceResponse])
async def evidence_queue(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(get_current_staff_user)
):
    result = await db.execute(
        select(Evidence).where(Evidence.status == EvidenceStatus.QUARANTINED)
        .order_by(Evidence.created_at).offset(offset).limit(limit)
    )
    return result.scalars().all()


@router.post("/evidence/{evidence_id}/approve", response_model=EvidenceResponse)
async def approve_evidence(
    evidence_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(get_current_staff_user)
):
    ev = await db.scalar(select(Evidence).where(Evidence.id == evidence_id))
    if not ev:
        raise HTTPException(404, "Evidence not found")
    ev.status = EvidenceStatus.READY
    ev.is_published = True
    await _audit(db, staff.id, "EVIDENCE_APPROVE", "Evidence", ev.id, ip=request.client.host if request.client else None)
    await db.commit()
    await db.refresh(ev)
    return ev


@router.post("/evidence/{evidence_id}/block", response_model=EvidenceResponse)
async def block_evidence(
    evidence_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(get_current_staff_user)
):
    ev = await db.scalar(select(Evidence).where(Evidence.id == evidence_id))
    if not ev:
        raise HTTPException(404, "Evidence not found")
    ev.status = EvidenceStatus.BLOCKED
    ev.is_published = False
    await _audit(db, staff.id, "EVIDENCE_BLOCK", "Evidence", ev.id, ip=request.client.host if request.client else None)
    await db.commit()
    await db.refresh(ev)
    return ev


# ── Support Tickets ───────────────────────────────────────────────────────────

@router.get("/support", response_model=list[SupportTicketResponse])
async def list_support(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(get_current_staff_user)
):
    stmt = select(SupportTicket)
    if status:
        stmt = stmt.where(SupportTicket.status == SupportStatus(status.upper()))
    result = await db.execute(stmt.order_by(SupportTicket.created_at).offset(offset).limit(limit))
    return result.scalars().all()


@router.post("/support/{ticket_id}/answer", response_model=SupportTicketResponse)
async def answer_ticket(
    ticket_id: int,
    body: SupportTicketAnswer,
    db: AsyncSession = Depends(get_db),
    staff: User = Depends(get_current_staff_user)
):
    ticket = await db.scalar(select(SupportTicket).where(SupportTicket.id == ticket_id))
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket.answer = body.answer
    ticket.answered_by = staff.id
    ticket.status = SupportStatus.ANSWERED

    db.add(Notification(
        user_id=ticket.user_id,
        event_type="SUPPORT_ANSWERED",
        title=f"Ответ на обращение в поддержку",
        message=body.answer[:200],
        object_type="SupportTicket",
        object_id=ticket.id
    ))
    await db.commit()
    await db.refresh(ticket)
    return ticket


# ── User management ───────────────────────────────────────────────────────────

@router.get("/users", response_model=list[dict])
async def list_users(
    search: Optional[str] = Query(None, max_length=128),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user)
):
    stmt = select(User)
    if search:
        stmt = stmt.where(
            (User.username.ilike(f"%{search}%")) |
            (User.telegram_id.contains(search))
        )
    result = await db.execute(stmt.order_by(User.id).offset(offset).limit(limit))
    users = result.scalars().all()
    return [{"id": u.id, "telegram_id": u.telegram_id, "username": u.username, "role": u.role.value} for u in users]


@router.post("/users/{user_id}/role", response_model=dict)
async def update_user_role(
    user_id: int,
    body: UserRoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_admin_user)
):
    target = await db.scalar(select(User).where(User.id == user_id))
    if not target:
        raise HTTPException(404, "User not found")
    if target.role == Role.OWNER:
        raise HTTPException(422, "Cannot change role of OWNER")
    old_role = target.role
    target.role = body.role
    await _audit(db, actor.id, "ROLE_CHANGE", "User", user_id,
                 {"old": old_role.value, "new": body.role.value, "reason": body.reason},
                 request.client.host if request.client else None)
    await db.commit()
    return {"id": target.id, "role": target.role.value}


# ── Audit Log ─────────────────────────────────────────────────────────────────

@router.get("/audit-log", response_model=list[AuditLogResponse])
async def audit_log(
    action: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user)
):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action.upper())
    result = await db.execute(stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit))
    return result.scalars().all()
