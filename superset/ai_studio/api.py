"""Thin Flask blueprint for the AI Studio in-product experience."""
from __future__ import annotations

import json
import time
from typing import Any

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_login import current_user
from flask_appbuilder.security.sqla.models import User
from superset_core.tasks.types import TaskOptions

from superset import db, security_manager
from superset.ai_studio import attachments
from superset.ai_studio.mcp_invoker import MCPToolInvoker
from superset.ai_studio.models import (
    AIStudioChangeSet,
    AIStudioCheckpoint,
    AIStudioTask,
)
from superset.ai_studio.services import (
    AdminProviderService,
    AIStudioError,
    ChangeStagingService,
    ContextBuilder,
    MCPRegistry,
    ProviderRegistry,
    change_to_dict,
)
from superset.ai_studio.tasks import execute_ai_studio_chat

blueprint = Blueprint("ai_studio", __name__, url_prefix="/api/v1/ai-studio")

# Tool round trips run synchronously in this web request (see
# mcp_invoker.MCPToolInvoker's docstring for why they cannot run inside the
# async GTF task), so both bounds keep that blocking window small and
# predictable regardless of how chatty the model gets.
MAX_TOOL_ROUNDS = 3
TOOL_ROUND_TRIP_BUDGET_SECONDS = 30


def _enabled() -> None:
    if not current_app.config.get("AI_STUDIO_ENABLED", False):
        raise AIStudioError("AI Studio is disabled by an administrator.")


def _user():
    if not current_user.is_authenticated:
        raise AIStudioError("Authentication is required.")
    return current_user


@blueprint.errorhandler(AIStudioError)
def _handle_error(error: AIStudioError):
    return jsonify({"message": str(error)}), 403


@blueprint.get("/bootstrap")
def bootstrap():
    _enabled(); _user()
    return jsonify(
        {
            "safe_mode": current_app.config.get("AI_STUDIO_SAFE_MODE", True),
            "providers": ProviderRegistry.public(),
            "tools": MCPRegistry.public_tools(),
            "mcp_enabled": bool(current_app.config.get("MCP_RBAC_ENABLED", False)),
            "is_admin": security_manager.is_admin(),
        }
    )


@blueprint.get("/context/dashboard/<int:dashboard_id>")
def dashboard_context(dashboard_id: int):
    _enabled()
    return jsonify(ContextBuilder.dashboard(_user(), dashboard_id))


@blueprint.get("/context/sql_lab")
def sql_lab_context():
    _enabled(); user = _user()
    database_id = request.args.get("database_id", type=int)
    if database_id is None:
        raise AIStudioError("A database is required to build SQL Lab context.")
    return jsonify(
        ContextBuilder.sql_lab(
            user,
            database_id,
            schema=request.args.get("schema") or None,
            table=request.args.get("table") or None,
        )
    )


def _run_tool_round_trips(
    user: User,
    provider_id: str,
    model: str | None,
    messages: list[dict[str, Any]],
    effort: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Synchronously resolve up to ``MAX_TOOL_ROUNDS`` of MCP tool calls.

    Runs in the original web request -- see ``mcp_invoker.MCPToolInvoker``'s
    docstring for why this cannot happen inside the async GTF task. Never
    raises: a provider or tool failure just stops the loop early, and the
    final async generation step still runs on whatever was resolved so far.
    Returns ``(augmented_messages, tool_call_audit)``.
    """
    tools = MCPToolInvoker.tool_schemas()
    if not tools:
        return messages, []
    audit: list[dict[str, Any]] = []
    deadline = time.monotonic() + TOOL_ROUND_TRIP_BUDGET_SECONDS
    current = list(messages)
    for _ in range(MAX_TOOL_ROUNDS):
        if time.monotonic() >= deadline:
            break
        try:
            step = ProviderRegistry.chat_step(provider_id, model, current, tools, effort=effort)
        except AIStudioError:
            break
        tool_calls = step.get("tool_calls") or []
        if not tool_calls:
            break
        current.append(
            {
                "role": "assistant",
                "content": step.get("content"),
                "tool_calls": tool_calls,
            }
        )
        for call in tool_calls:
            fn = call.get("function", {}) or {}
            name = str(fn.get("name", ""))
            try:
                arguments = json.loads(fn.get("arguments") or "{}")
                if not isinstance(arguments, dict):
                    arguments = {}
            except (TypeError, ValueError):
                arguments = {}
            started = time.monotonic()
            result = MCPToolInvoker.call(user, name, arguments)
            audit.append(
                {
                    "tool": name,
                    "argument_keys": sorted(arguments.keys()),
                    "status": "ok" if result.get("ok") else "error",
                    "latency_ms": int((time.monotonic() - started) * 1000),
                }
            )
            current.append(
                {
                    "role": "tool",
                    "tool_call_id": str(call.get("id", "")),
                    "content": json.dumps(
                        result.get("result")
                        if result.get("ok")
                        else {"error": result.get("error")}
                    ),
                }
            )
    return current, audit


@blueprint.post("/chat")
def chat():
    """Resolve context and tool calls, then submit the final answer as a
    pollable async task.

    Context injection and any MCP tool round trips (``_run_tool_round_trips``
    above) run synchronously here, in the real request -- both need this
    request's actual authenticated user to resolve Superset RBAC correctly.
    Only the last, potentially slow provider call that produces the visible
    answer is deferred to the Global Task Framework (see ai_studio/tasks.py),
    so this route still returns quickly for the common case (no tools
    allow-listed, or the model didn't ask for one). The browser polls
    ``GET /api/v1/task/<gtf_task_uuid>`` (or ``/status_changes``) for that
    task's status, and reads the finished ``{content, usage}`` back from its
    ``payload`` once terminal -- this route's own response only ever carries
    the two task identifiers, never the chat result itself.
    """
    _enabled(); user = _user()
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])
    if not isinstance(messages, list) or not messages:
        raise AIStudioError("At least one message is required.")

    provider_id = str(data.get("provider", ""))
    model = data.get("model")
    effort = data.get("effort")

    contextual_messages = list(messages)

    # Attachments are resolved before dashboard/SQL-Lab context below and
    # before _run_tool_round_trips further down, so both context-building
    # and any tool-calling reasoning see attached content too, not just the
    # final answer step. Needs provider_id resolved first (above) to know
    # whether the provider supports image input.
    raw_attachment_ids = data.get("attachment_ids")
    attachment_ids = (
        [str(item) for item in raw_attachment_ids]
        if isinstance(raw_attachment_ids, list)
        else []
    )
    if attachment_ids:
        provider_capabilities = ProviderRegistry.capabilities(provider_id)
        image_parts, document_text = attachments.resolve_attachments_for_chat(
            user, attachment_ids, provider_capabilities
        )
        if document_text:
            contextual_messages.insert(
                0,
                {
                    "role": "system",
                    "content": (
                        "The user attached the following document(s). Use "
                        "their content to answer, and say clearly if the "
                        "answer isn't in them.\n" + document_text
                    ),
                },
            )
        if image_parts:
            # Only the last (current) message gains image content -- every
            # earlier message and the whole no-attachment path stay plain
            # strings exactly as today. Prepending dashboard/SQL context
            # below with insert(0, ...) never touches this last-index
            # rewrite, so operation order between the two doesn't matter.
            last_message = dict(contextual_messages[-1])
            last_message["content"] = [
                {"type": "text", "text": last_message.get("content", "")},
                *image_parts,
            ]
            contextual_messages[-1] = last_message

    dashboard_id = None
    if data.get("dashboard_id") is not None:
        try:
            dashboard_id = int(data["dashboard_id"])
        except (TypeError, ValueError) as exc:
            raise AIStudioError("The dashboard context identifier is invalid.") from exc
        # Context is always rebuilt on the server from a Superset identifier.
        # The browser may request a dashboard context but never supplies
        # trusted dashboard metadata (or data) to the provider directly.
        context = ContextBuilder.dashboard(user, dashboard_id)
        contextual_messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    "You are assisting inside Apache Superset. Use this "
                    "bounded, current-user-authorized workspace context. "
                    "Do not claim a mutation occurred; explain proposed "
                    "changes for review.\n" + json.dumps(context)
                ),
            },
        )

    sql_context = data.get("sql_context")
    if isinstance(sql_context, dict) and sql_context.get("database_id") is not None:
        try:
            sql_database_id = int(sql_context["database_id"])
        except (TypeError, ValueError) as exc:
            raise AIStudioError("The SQL Lab database identifier is invalid.") from exc
        # As with dashboard_id above, the database/schema/table are
        # re-resolved and access-checked server-side. The one piece that
        # can't be re-resolved from a trusted id -- the draft SQL text
        # itself, an unsaved client-only buffer -- is forwarded verbatim,
        # same trust level as the chat message text it sits next to.
        context = ContextBuilder.sql_lab(
            user,
            sql_database_id,
            schema=sql_context.get("schema") or None,
            table=sql_context.get("table") or None,
        )
        draft_sql = str(sql_context.get("sql") or "")[:4000]
        contextual_messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    "You are assisting inside Apache Superset SQL Lab. Use "
                    "this bounded, current-user-authorized workspace "
                    "context. The draft SQL is the user's own unsaved "
                    "editor buffer, not a source of truth about the "
                    "schema -- prefer the column list when they disagree. "
                    "Do not claim a query ran or a mutation occurred; "
                    "explain proposed changes for review.\n"
                    + json.dumps(context)
                    + "\nCurrent editor draft SQL:\n"
                    + draft_sql
                ),
            },
        )

    contextual_messages, tool_calls_audit = _run_tool_round_trips(
        user, provider_id, model, contextual_messages, effort
    )

    ai_studio_task = AIStudioTask(
        user_id=user.id,
        dashboard_id=dashboard_id,
        title=str(messages[-1].get("content", "AI Studio request"))[:512],
        status="queued",
        provider=provider_id,
        model=model,
        request_json=json.dumps({"message_count": len(messages)}),
        tool_calls_json=json.dumps(tool_calls_audit) if tool_calls_audit else None,
        attachment_ids_json=json.dumps(attachment_ids) if attachment_ids else None,
    )
    db.session.add(ai_studio_task)
    db.session.commit()

    gtf_task = execute_ai_studio_chat.schedule(
        str(ai_studio_task.id),
        provider_id,
        model,
        contextual_messages,
        effort,
        options=TaskOptions(timeout=60),
    )
    ai_studio_task.gtf_task_uuid = gtf_task.uuid
    db.session.commit()
    return (
        jsonify({"task_id": str(ai_studio_task.id), "gtf_task_uuid": str(gtf_task.uuid)}),
        202,
    )


@blueprint.post("/attachments")
def upload_attachment():
    _enabled(); user = _user()
    file = request.files.get("file")
    if not file:
        raise AIStudioError("A file is required.")
    attachment = attachments.save_attachment(user, file)
    return (
        jsonify(
            {
                "id": str(attachment.id),
                "kind": attachment.kind,
                "original_filename": attachment.original_filename,
                "content_type": attachment.content_type,
                "size_bytes": attachment.size_bytes,
            }
        ),
        201,
    )


@blueprint.get("/attachments/<attachment_id>/download")
def download_attachment(attachment_id: str):
    _enabled(); user = _user()
    path, content_type, download_name = attachments.get_attachment_for_download(
        user, attachment_id
    )
    return send_file(
        path,
        mimetype=content_type,
        as_attachment=True,
        download_name=download_name,
        max_age=0,
    )


@blueprint.delete("/attachments/<attachment_id>")
def delete_attachment(attachment_id: str):
    _enabled(); user = _user()
    attachments.delete_attachment(user, attachment_id)
    return jsonify({"status": "deleted"})


@blueprint.get("/tasks")
def tasks():
    _enabled(); user = _user()
    rows = db.session.query(AIStudioTask).filter_by(user_id=user.id).order_by(AIStudioTask.created_on.desc()).limit(100).all()
    return jsonify(
        {
            "result": [
                {
                    "id": str(row.id),
                    "title": row.title,
                    "status": row.status,
                    "provider": row.provider,
                    "model": row.model,
                    "created_on": row.created_on.isoformat(),
                    "error": row.error_message,
                    "gtf_task_uuid": str(row.gtf_task_uuid) if row.gtf_task_uuid else None,
                    "tool_calls": json.loads(row.tool_calls_json)
                    if row.tool_calls_json
                    else [],
                }
                for row in rows
            ]
        }
    )


@blueprint.get("/changes")
def changes():
    _enabled(); user = _user()
    rows = db.session.query(AIStudioChangeSet).filter_by(user_id=user.id).order_by(AIStudioChangeSet.created_on.desc()).limit(100).all()
    return jsonify({"result": [change_to_dict(row) for row in rows]})


@blueprint.post("/changes")
def stage_change():
    _enabled(); user = _user()
    change = ChangeStagingService.stage(user, request.get_json(silent=True) or {})
    return jsonify(change_to_dict(change)), 201


@blueprint.post("/changes/<change_id>/apply")
def apply_change(change_id: str):
    _enabled(); user = _user()
    change = db.session.get(AIStudioChangeSet, change_id)
    if not change or change.user_id != user.id:
        raise AIStudioError("Change set not found.")
    checkpoint = ChangeStagingService.apply(user, change)
    return jsonify({"change": change_to_dict(change), "checkpoint_id": str(checkpoint.id)})


@blueprint.post("/changes/<change_id>/reject")
def reject_change(change_id: str):
    _enabled(); user = _user()
    change = db.session.get(AIStudioChangeSet, change_id)
    if not change or change.user_id != user.id:
        raise AIStudioError("Change set not found.")
    if change.status != "pending":
        raise AIStudioError("Only pending changes can be rejected.")
    change.status = "rejected"
    db.session.commit()
    return jsonify(change_to_dict(change))


@blueprint.post("/checkpoints/<checkpoint_id>/restore")
def restore_checkpoint(checkpoint_id: str):
    _enabled(); user = _user()
    checkpoint = db.session.get(AIStudioCheckpoint, checkpoint_id)
    if not checkpoint or checkpoint.user_id != user.id:
        raise AIStudioError("Checkpoint not found.")
    ChangeStagingService.restore(user, checkpoint)
    return jsonify({"status": "restored"})


@blueprint.get("/admin/providers")
def list_providers():
    _enabled(); _user()
    return jsonify({"result": AdminProviderService.list_all()})


@blueprint.post("/admin/providers")
def create_provider():
    _enabled(); user = _user()
    provider = AdminProviderService.create(user, request.get_json(silent=True) or {})
    return jsonify(provider), 201


@blueprint.put("/admin/providers/<provider_id>")
def update_provider(provider_id: str):
    _enabled(); user = _user()
    provider = AdminProviderService.update(user, provider_id, request.get_json(silent=True) or {})
    return jsonify(provider)


@blueprint.delete("/admin/providers/<provider_id>")
def delete_provider(provider_id: str):
    _enabled(); _user()
    AdminProviderService.delete(provider_id)
    return jsonify({"status": "deleted"})


def register_ai_studio(app) -> None:
    """Called by the deployment config's supported FLASK_APP_MUTATOR hook."""
    if "ai_studio" not in app.blueprints:
        app.register_blueprint(blueprint)
