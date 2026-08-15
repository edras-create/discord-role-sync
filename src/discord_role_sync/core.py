from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterable
from typing import Any

from .models import Action, Candidate, SourceMode, SyncSummary


def _display_name(user: Any) -> str:
    return str(getattr(user, "display_name", None) or getattr(user, "name", None) or user.id)


async def _remember_users(
    users: AsyncIterator[Any],
    candidates: dict[int, Candidate],
) -> None:
    async for user in users:
        if getattr(user, "bot", False):
            continue
        candidates[user.id] = Candidate(user_id=user.id, display_name=_display_name(user))


async def collect_candidates(message: Any, source: SourceMode) -> list[Candidate]:
    """Collect and deduplicate eligible users from reactions and/or a native poll."""

    candidates: dict[int, Candidate] = {}

    if source in {SourceMode.AUTO, SourceMode.REACTIONS}:
        for reaction in getattr(message, "reactions", ()):
            await _remember_users(reaction.users(limit=None), candidates)

    if source in {SourceMode.AUTO, SourceMode.POLL}:
        poll = getattr(message, "poll", None)
        if poll is not None:
            for answer in getattr(poll, "answers", ()):
                await _remember_users(answer.voters(limit=None), candidates)

    return [candidates[user_id] for user_id in sorted(candidates)]


def _role_ids(roles: Iterable[Any]) -> set[int]:
    return {role.id for role in roles}


async def synchronize_role(
    *,
    guild: Any,
    role: Any,
    candidates: Iterable[Candidate],
    action: Action,
    dry_run: bool,
    logger: logging.Logger,
) -> SyncSummary:
    """Apply an idempotent role change to each candidate, continuing after failures."""

    candidate_list = list(candidates)
    summary = SyncSummary(matched=len(candidate_list))
    reason = "One-shot role sync from message reactions or poll votes"

    for candidate in candidate_list:
        try:
            member = guild.get_member(candidate.user_id)
            if member is None:
                member = await guild.fetch_member(candidate.user_id)

            if getattr(member, "bot", False):
                summary.skipped += 1
                logger.info(
                    "SKIP user=%s id=%s reason=bot",
                    candidate.display_name,
                    candidate.user_id,
                )
                continue

            has_role = role.id in _role_ids(member.roles)
            needs_change = (action is Action.ADD and not has_role) or (
                action is Action.REMOVE and has_role
            )

            if not needs_change:
                summary.skipped += 1
                state = "already_has_role" if has_role else "role_already_absent"
                logger.info(
                    "SKIP user=%s id=%s reason=%s",
                    candidate.display_name,
                    candidate.user_id,
                    state,
                )
                continue

            if dry_run:
                summary.would_change += 1
                logger.info(
                    "DRY_RUN action=%s user=%s id=%s role=%s",
                    action.value,
                    candidate.display_name,
                    candidate.user_id,
                    role.id,
                )
                continue

            if action is Action.ADD:
                await member.add_roles(role, reason=reason)
            else:
                await member.remove_roles(role, reason=reason)

            summary.changed += 1
            logger.info(
                "SUCCESS action=%s user=%s id=%s role=%s",
                action.value,
                candidate.display_name,
                candidate.user_id,
                role.id,
            )
        except Exception as exc:  # Continue so one user cannot abort the whole batch.
            summary.failed += 1
            logger.error(
                "FAILED action=%s user=%s id=%s error=%s",
                action.value,
                candidate.display_name,
                candidate.user_id,
                exc,
            )

    return summary
