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
