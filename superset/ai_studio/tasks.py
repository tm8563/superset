"""Async execution of AI Studio chat via the Global Task Framework (GTF).

Runs the final provider call inside a GTF task instead of blocking the
Flask worker handling ``POST /api/v1/ai-studio/chat`` (see api.py). GTF
owns status/progress/cancellation once submitted; ``AIStudioTask`` stays
the AI-Studio-specific business record (provider, model, tool-call audit
trail).

Context-building and any MCP tool round trips happen synchronously in
api.py's ``chat()``, before this task is ever scheduled -- both need a real
Flask request context to resolve the acting user's identity correctly
(security_manager.can_access_dashboard, and the MCP service's own
``current_user``/``g.user`` resolution), which a GTF worker does not have.
By the time this task runs, ``messages`` is already fully resolved (system
context and any tool results already appended); this task's only job is
the one remaining provider call that produces the visible answer, which is
allowed to be slow without blocking anything.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from superset_core.tasks.types import TaskScope

from superset import db
from superset.tasks.ambient_context import get_context
from superset.tasks.decorators import task

from superset.ai_studio.models import AIStudioTask
from superset.ai_studio.services import AIStudioError, ProviderRegistry

# Re-exported so the plain Celery task defined in attachments.py registers
# under the worker's existing "superset.ai_studio.tasks" entry in
# CeleryConfig.imports, rather than needing a second imports entry.
from superset.ai_studio.attachments import prune_old_attachments  # noqa: F401

logger = logging.getLogger(__name__)

AI_STUDIO_CHAT_TASK = "superset.ai_studio.chat_v1"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fail(ai_studio_task: AIStudioTask, message: str) -> None:
    ai_studio_task.status = "failed"
    ai_studio_task.error_message = message
    ai_studio_task.completed_on = _utcnow()
    db.session.commit()
    # The GTF task's own payload is what the browser actually polls for (see
    # api.py's chat()) -- mirror the safe, user-displayable message there too
    # so a client never needs to also fetch the AIStudioTask row just to
    # learn why a request failed.
    get_context().update_task(payload={"error": message}, immediate=True)


@task(name=AI_STUDIO_CHAT_TASK, scope=TaskScope.PRIVATE)
def execute_ai_studio_chat(
    ai_studio_task_id: str,
    provider_id: str,
    model: str | None,
    messages: list[dict[str, Any]],
    effort: str | None,
) -> None:
    """Run the final, already-context-resolved provider call for one chat."""
    ai_studio_task = db.session.get(AIStudioTask, ai_studio_task_id)
    if not ai_studio_task:
        logger.warning(
            "AI Studio task %s vanished before execution", ai_studio_task_id
        )
        return

    ai_studio_task.status = "running"
    ai_studio_task.started_on = _utcnow()
    db.session.commit()

    ctx = get_context()

    # Cooperative cancellation only: the provider call below is a single
    # blocking urlopen with no interruption point, so an abort here cannot
    # kill an in-flight HTTP request the way engine-level query cancellation
    # can (superset.tasks.async_queries._capture_query_cancellation). What
    # this buys instead: the browser stops waiting/polling as soon as it sees
    # ABORTED, and the row is marked so a stray late completion is never
    # confused with a real answer.
    @ctx.on_abort
    def _handle_abort() -> None:
        ai_studio_task.status = "cancelled"
        ai_studio_task.completed_on = _utcnow()
        db.session.commit()

    try:
        result: dict[str, Any] = ProviderRegistry.chat(
            provider_id, model, messages, effort=effort
        )
    except AIStudioError as exc:
        _fail(ai_studio_task, str(exc))
        return
    except Exception:  # noqa: BLE001 - never leak an internal trace to the caller
        logger.exception(
            "Unhandled AI Studio chat failure for task %s", ai_studio_task_id
        )
        _fail(ai_studio_task, "AI Studio could not complete this request.")
        return

    ai_studio_task.status = "completed"
    # Small audit trail only (usage, not the full message) -- the message
    # itself lives in the GTF task's payload below, which is what the
    # browser actually reads back.
    ai_studio_task.result_json = json.dumps({"usage": result.get("usage")})
    ai_studio_task.completed_on = _utcnow()
    db.session.commit()
    ctx.update_task(payload=result, immediate=True)
