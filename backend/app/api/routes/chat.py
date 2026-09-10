# Creado por Aldo Garcia.
"""Ruta de chat. Punto unico por el que el frontend consulta a Matrix RH."""

from __future__ import annotations

from contextlib import suppress

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.api.deps import get_db, get_user_context, require_csrf
from app.api.schemas import ChatRequest, ChatResponse
from app.authorization.context import UserContext
from app.authorization.policy import get_policy_engine
from app.common.errors import (
    ForbiddenError,
    NotFoundError,
    OllamaUnavailableError,
    RateLimitedError,
    ValidationFailedError,
)
from app.common.ids import sha256_text
from app.common.logging import get_logger
from app.config import get_settings
from app.database.engine import get_sessionmaker
from app.database.models import ChatOperation
from app.llm.provider import inference_deadline
from app.memory.service import MemoryService, authorization_fingerprint
from app.security.admission import admission
from app.security.rate_limit import get_rate_limiter

logger = get_logger(__name__)
router = APIRouter(tags=["chat"])

_orchestrator: Orchestrator | None = None
_memory = MemoryService()


def get_orchestrator() -> Orchestrator:
    """Orquestador perezoso: evita construir clientes al importar el modulo."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def reset_orchestrator() -> None:
    global _orchestrator
    _orchestrator = None


def _expire_stalled_operation(db: Session, operation: ChatOperation) -> None:
    """Recuperar solicitudes tras caida de proceso, sin reenviarlas automaticamente."""
    from datetime import timedelta

    from sqlalchemy import update

    from app.common.ids import utcnow_naive

    cutoff = utcnow_naive() - timedelta(seconds=get_settings().llm_request_deadline_seconds + 60)
    if operation.status == "running" and operation.created_at < cutoff:
        db.execute(
            update(ChatOperation)
            .where(
                ChatOperation.id == operation.id, ChatOperation.status == "running", ChatOperation.created_at < cutoff
            )
            .values(status="expired")
        )
        db.refresh(operation)


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_csrf)])
def chat(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    ctx: UserContext = Depends(get_user_context),
) -> ChatResponse:
    """Procesa un turno de conversacion."""
    settings = get_settings()
    limiter = get_rate_limiter()
    if not limiter.check(f"chat:{sha256_text(ctx.user_id)}", limit=settings.rate_limit_chat_per_minute).allowed:
        raise RateLimitedError()

    operation_id = sha256_text(f"{ctx.user_id}|{payload.client_request_id}") if payload.client_request_id else None
    request_hash = sha256_text(f"{payload.conversation_id}|{payload.message}")
    expected_scope = authorization_fingerprint(db, ctx, get_policy_engine().effective_categories(ctx))
    existing = db.get(ChatOperation, operation_id) if operation_id else None
    if existing:
        _expire_stalled_operation(db, existing)
        if existing.request_hash != request_hash:
            raise ValidationFailedError("La clave de solicitud ya se utilizo con otro contenido.")
        if existing.authorization_scope != expected_scope:
            raise ForbiddenError()
        if existing.status == "completed":
            _memory.get_owned_conversation(db, ctx, existing.conversation_id)
            return ChatResponse.model_validate(existing.response)
        raise OllamaUnavailableError(
            f"La solicitud ya esta registrada: {existing.status}. Revise su estado antes de reenviar."
        )

    if payload.conversation_id:
        conversation = _memory.get_owned_conversation(db, ctx, payload.conversation_id)
    else:
        conversation = _memory.create_conversation(db, ctx)

    with (
        admission("chat", settings.chat_max_inflight),
        admission(f"conversation:{conversation.id}", 1),
        inference_deadline(),
    ):
        if operation_id:
            db.add(
                ChatOperation(
                    id=operation_id,
                    user_id=ctx.user_id,
                    conversation_id=conversation.id,
                    request_hash=request_hash,
                    authorization_scope=expected_scope,
                    status="running",
                )
            )
        db.commit()
        try:
            outcome = get_orchestrator().handle_chat(db, ctx=ctx, conversation=conversation, message=payload.message)
            response = ChatResponse(
                conversation_id=outcome.conversation_id,
                message_id=outcome.message_id,
                answer=outcome.answer,
                sources=outcome.public_sources(),
                intent=outcome.intent,
                grounded=outcome.grounded,
                latency_ms=outcome.latency_ms,
            )
            # Revalidar contra una transaccion nueva: ve revocaciones durante IA.
            with get_sessionmaker()() as check_db:
                current = get_user_context(request, check_db)
                categories = get_policy_engine().effective_categories(current)
                if authorization_fingerprint(check_db, current, categories) != expected_scope:
                    raise ForbiddenError("Sus permisos cambiaron durante la consulta. Vuelva a consultar.")
                _memory.get_owned_conversation(check_db, current, outcome.conversation_id)
                operation = check_db.get(ChatOperation, operation_id) if operation_id else None
                if operation is not None and operation.status == "cancelled":
                    raise ValidationFailedError("Solicitud cancelada.")
            if operation_id:
                from sqlalchemy import update

                changed = db.execute(
                    update(ChatOperation)
                    .where(ChatOperation.id == operation_id, ChatOperation.status == "running")
                    .values(status="completed", response=response.model_dump())
                )
                if changed.rowcount != 1:
                    raise ValidationFailedError("Solicitud cancelada.")
            db.commit()
            return response
        except Exception:
            db.rollback()
            if operation_id:
                with suppress(Exception), get_sessionmaker()() as failure_db:
                    from sqlalchemy import update

                    failure_db.execute(
                        update(ChatOperation)
                        .where(ChatOperation.id == operation_id, ChatOperation.status == "running")
                        .values(status="failed")
                    )
                    failure_db.commit()
            raise


@router.get("/chat/requests/{client_request_id}")
def chat_status(
    client_request_id: str, db: Session = Depends(get_db), ctx: UserContext = Depends(get_user_context)
) -> dict:
    operation = db.get(ChatOperation, sha256_text(f"{ctx.user_id}|{client_request_id}"))
    if operation is None:
        raise NotFoundError()
    _expire_stalled_operation(db, operation)
    _memory.get_owned_conversation(db, ctx, operation.conversation_id)
    scope = authorization_fingerprint(db, ctx, get_policy_engine().effective_categories(ctx))
    if operation.authorization_scope != scope:
        raise ForbiddenError()
    return {
        "status": operation.status,
        "conversation_id": operation.conversation_id,
        "response": operation.response if operation.status == "completed" else None,
    }


@router.post("/chat/requests/{client_request_id}/cancel", dependencies=[Depends(require_csrf)])
def cancel_chat(
    client_request_id: str, db: Session = Depends(get_db), ctx: UserContext = Depends(get_user_context)
) -> dict:
    from sqlalchemy import update

    operation_id = sha256_text(f"{ctx.user_id}|{client_request_id}")
    operation = db.get(ChatOperation, operation_id)
    if operation is None:
        raise NotFoundError()
    db.execute(
        update(ChatOperation)
        .where(ChatOperation.id == operation_id, ChatOperation.status == "running")
        .values(status="cancelled")
    )
    return {"ok": True}
