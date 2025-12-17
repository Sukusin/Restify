from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import ModerationStatus
from app.models.places import Place
from app.models.users import UserAuth, UserProfile
from app.schemas.chat import ChatRequest, ChatResponse
from app.routers.places import _to_place_response
from app.services.llm import llm, LLMError
from app.services.recommendations import parse_categories

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def _build_system_prompt(*, profile: UserProfile | None, candidates: list[Place]) -> str:
    cats = parse_categories(profile.preferred_categories) if profile else []
    lines = [
        "Ты — ассистент для подбора мест отдыха и развлечений.",
        "Отвечай по-русски, коротко и по делу.",
        "Если информации недостаточно — задай 1 уточняющий вопрос.",
    ]

    if profile:
        if profile.city:
            lines.append(f"Город пользователя: {profile.city}.")
        if cats:
            lines.append(f"Предпочтительные категории: {', '.join(cats)}.")

    if candidates:
        lines.append("\nКандидаты мест (можно предлагать только из списка):")
        for p in candidates:
            lines.append(
                f"- {p.name} | категория: {p.category} | город: {p.city} | рейтинг: {p.average_rating:.2f} ({p.review_count})"
            )
    else:
        lines.append("\nКандидатов нет. Предложи изменить фильтры.")

    return "\n".join(lines)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    profile = db.get(UserProfile, current.id)

    stmt = select(Place).where(Place.status == ModerationStatus.approved.value)
    if payload.category:
        stmt = stmt.where(Place.category == payload.category.strip().lower())
    if payload.city:
        stmt = stmt.where(Place.city == payload.city.strip())
    elif profile and profile.city:
        stmt = stmt.where(Place.city == profile.city)
    if payload.min_rating is not None:
        stmt = stmt.where(Place.average_rating >= payload.min_rating)

    candidates = list(
        db.scalars(
            stmt.order_by(desc(Place.average_rating), desc(Place.review_count), Place.name).limit(payload.limit_places)
        ).all()
    )

    system = _build_system_prompt(profile=profile, candidates=candidates)

    try:
        reply = await llm.chat(system=system, user_message=payload.message)
    except LLMError:
        logger.exception("LLM chat error")
        reply = "(Ошибка LLM) Попробуйте позже или используйте /recommendations и /places."

    return ChatResponse(reply=reply, places=[_to_place_response(p) for p in candidates])
