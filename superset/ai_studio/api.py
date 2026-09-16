"""Thin Flask blueprint for the AI Studio in-product experience."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user

from superset import db
from superset.ai_studio.models import (
    AIStudioChangeSet,
    AIStudioCheckpoint,
    AIStudioTask,
)
from superset.ai_studio.services import (
    AIStudioError,
    ChangeStagingService,
    ContextBuilder,
    MCPRegistry,
    ProviderRegistry,
    change_to_dict,
)

blueprint = Blueprint("ai_studio", __name__, url_prefix="/api/v1/ai-studio")


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
    return jsonify({"safe_mode": current_app.config.get("AI_STUDIO_SAFE_MODE", True), "providers": ProviderRegistry.public(), "tools": MCPRegistry.public_tools(), "mcp_enabled": bool(current_app.config.get("MCP_RBAC_ENABLED", False))})


@blueprint.get("/context/dashboard/<int:dashboard_id>")
def dashboard_context(dashboard_id: int):
    _enabled()
    return jsonify(ContextBuilder.dashboard(_user(), dashboard_id))


@blueprint.post("/chat")
def chat():
    _enabled(); user = _user()
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])
    if not isinstance(messages, list) or not messages:
        raise AIStudioError("At least one message is required.")
    # Context is always rebuilt on the server from a Superset identifier. The
    # browser may request a dashboard context but never supplies trusted
    # dashboard metadata (or data) to the provider directly.
    task = AIStudioTask(
        user_id=user.id,
        dashboard_id=data.get("dashboard_id"),
        title=str(messages[-1].get("content", "AI Studio request"))[:512],
        status="running",
        provider=str(data.get("provider", "")),
        model=data.get("model"),
        request_json=json.dumps({"message_count": len(messages)}),
        started_on=datetime.now(timezone.utc),
    )
    db.session.add(task)
    db.session.commit()
    try:
        contextual_messages = list(messages)
        if data.get("dashboard_id") is not None:
            try:
                dashboard_id = int(data["dashboard_id"])
            except (TypeError, ValueError) as exc:
                raise AIStudioError("The dashboard context identifier is invalid.") from exc
            context = ContextBuilder.dashboard(user, dashboard_id)
            contextual_messages.insert(
                0,
                {
                    "role": "system",
                    "content": "You are assisting inside Apache Superset. Use this bounded, current-user-authorized workspace context. Do not claim a mutation occurred; explain proposed changes for review.\n" + json.dumps(context),
                },
            )
        result = ProviderRegistry.chat(
            str(data.get("provider", "")),
            data.get("model"),
            contextual_messages,
            effort=data.get("effort"),
        )
        task.status = "completed"
        task.result_json = json.dumps({"usage": result.get("usage")})
        task.completed_on = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify({**result, "task_id": str(task.id)})
    except AIStudioError as exc:
        task.status = "failed"
        task.error_message = str(exc)
        task.completed_on = datetime.now(timezone.utc)
        db.session.commit()
        raise


@blueprint.get("/tasks")
def tasks():
    _enabled(); user = _user()
    rows = db.session.query(AIStudioTask).filter_by(user_id=user.id).order_by(AIStudioTask.created_on.desc()).limit(100).all()
    return jsonify({"result": [{"id": str(row.id), "title": row.title, "status": row.status, "provider": row.provider, "model": row.model, "created_on": row.created_on.isoformat(), "error": row.error_message} for row in rows]})


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


def register_ai_studio(app) -> None:
    """Called by the deployment config's supported FLASK_APP_MUTATOR hook."""
    if "ai_studio" not in app.blueprints:
        app.register_blueprint(blueprint)
