"""Persistent, minimal audit state for AI Studio.

Superset objects remain the source of truth. These records store only the
conversation/task lifecycle and reversible proposed mutations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from flask_appbuilder import Model
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy_utils import UUIDType

from superset.extensions import encrypted_field_factory


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AIStudioTask(Model):
    __tablename__ = "ai_studio_task"

    id = Column(UUIDType(binary=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("ab_user.id"), nullable=False, index=True)
    dashboard_id = Column(Integer, nullable=True, index=True)
    title = Column(String(512), nullable=False)
    status = Column(String(32), nullable=False, default="queued", index=True)
    provider = Column(String(128), nullable=True)
    model = Column(String(256), nullable=True)
    request_json = Column(Text, nullable=False, default="{}")
    result_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    cancel_requested = Column(Boolean, nullable=False, default=False)
    # Audit trail for any MCP tool calls resolved during this chat's
    # synchronous tool round-trip phase (see api.py's chat(),
    # mcp_invoker.py): a list of {tool, argument_keys, status, latency_ms}
    # -- tool name and argument *keys* only, never argument or result
    # values, matching the existing before_json/after_json convention of
    # keeping this table's rows small and not a second copy of sensitive data.
    tool_calls_json = Column(Text, nullable=True)
    # The Global Task Framework (GTF) task actually executing this request --
    # GTF owns status/progress/cancellation once submitted (see
    # ai_studio/tasks.py); this row stays the AI-Studio-specific business
    # record (provider, model, dashboard context). Nullable: rows created
    # before GTF integration, or a task that failed before submission, have
    # none.
    gtf_task_uuid = Column(UUIDType(binary=True), nullable=True, index=True)
    # Audit-only list of AIStudioAttachment ids used by this task (see
    # attachments.py) -- no FK, since attachments are uploaded independently
    # of any specific chat request (upload-on-select) and referenced by id
    # in whichever chat() call the browser sends next, the same way
    # dashboard_id is a plain client-supplied identifier re-resolved and
    # RBAC-checked server-side rather than a foreign key.
    attachment_ids_json = Column(Text, nullable=True)
    created_on = Column(DateTime, nullable=False, default=utcnow)
    started_on = Column(DateTime, nullable=True)
    completed_on = Column(DateTime, nullable=True)


class AIStudioChangeSet(Model):
    __tablename__ = "ai_studio_change_set"

    id = Column(UUIDType(binary=True), primary_key=True, default=uuid4)
    task_id = Column(UUIDType(binary=True), ForeignKey("ai_studio_task.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("ab_user.id"), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(128), nullable=False)
    title = Column(String(512), nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)
    before_json = Column(Text, nullable=False)
    after_json = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)
    created_on = Column(DateTime, nullable=False, default=utcnow)
    applied_on = Column(DateTime, nullable=True)
    rejected_on = Column(DateTime, nullable=True)


class AIStudioCheckpoint(Model):
    __tablename__ = "ai_studio_checkpoint"

    id = Column(UUIDType(binary=True), primary_key=True, default=uuid4)
    change_set_id = Column(UUIDType(binary=True), ForeignKey("ai_studio_change_set.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("ab_user.id"), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(128), nullable=False)
    snapshot_json = Column(Text, nullable=False)
    restored_on = Column(DateTime, nullable=True)
    created_on = Column(DateTime, nullable=False, default=utcnow)


class AIStudioAttachment(Model):
    """An uploaded chat attachment (image or document). See attachments.py
    for validation, storage, and resolution into provider-ready message
    content. storage_filename (never original_filename) is the only thing
    ever used to build a real filesystem path -- original_filename is
    display-only and may contain anything the client sent.
    """

    __tablename__ = "ai_studio_attachment"

    id = Column(UUIDType(binary=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("ab_user.id"), nullable=False, index=True)
    kind = Column(String(16), nullable=False)
    extension = Column(String(16), nullable=False)
    content_type = Column(String(128), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_filename = Column(String(64), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    # Documents only (kind == "document"); already truncated at upload time
    # to AI_STUDIO_ATTACHMENT_MAX_EXTRACTED_CHARS. Null for images.
    extracted_text = Column(Text, nullable=True)
    created_on = Column(DateTime, nullable=False, default=utcnow, index=True)


class AIStudioProvider(Model):
    """An admin-managed AI provider. Replaces the old AI_STUDIO_PROVIDERS
    deployment-config list as the primary source of truth: providers are
    added, edited, enabled/disabled, and removed by an Admin through the
    product UI rather than by editing environment variables and rebuilding.

    api_key is stored via Superset's own encrypted_field_factory (the same
    mechanism Database.password/encrypted_extra use), never as plaintext,
    and is never serialized back to the browser once set — see
    AdminProviderService in services.py.
    """

    __tablename__ = "ai_studio_provider"

    id = Column(UUIDType(binary=True), primary_key=True, default=uuid4)
    label = Column(String(128), nullable=False)
    base_url = Column(String(512), nullable=False)
    api_key = Column(encrypted_field_factory.create(String(1024)), nullable=True)
    default_model = Column(String(256), nullable=True)
    # Small, bounded lists (models/capabilities/effort tiers) — a JSON text
    # column matches the existing before_json/after_json/request_json
    # convention in this module rather than introducing child tables for
    # what is operator-entered, admin-scale data.
    models_json = Column(Text, nullable=False, default="[]")
    capabilities_json = Column(Text, nullable=False, default='["chat"]')
    effort_levels_json = Column(Text, nullable=False, default="[]")
    effort_param = Column(String(64), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    created_by_fk = Column(Integer, ForeignKey("ab_user.id"), nullable=True)
    created_on = Column(DateTime, nullable=False, default=utcnow)
    changed_by_fk = Column(Integer, ForeignKey("ab_user.id"), nullable=True)
    changed_on = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
