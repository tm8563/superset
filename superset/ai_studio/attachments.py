"""Chat attachment upload, validation, storage, and resolution.

Images and documents a user attaches to an AI Studio chat message. Upload is
independent of any specific chat request (upload-on-select, not
upload-on-send): the browser holds attachment ids in local compose-box
state and passes them to a later ``POST /chat`` call, the same way
dashboard_id is a plain client-supplied identifier re-resolved and
RBAC-checked server-side rather than a foreign key (see api.py's chat()).

Everything here runs synchronously in the web request, not the async GTF
task -- the same reasoning that already applies to dashboard/SQL-Lab context
and MCP tool calls in api.py: RBAC and file access need the real request
user, which the Celery worker process does not have.
"""
from __future__ import annotations

import base64
import logging
import os
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from flask import current_app
from flask_appbuilder.security.sqla.models import User
from werkzeug.datastructures import FileStorage

from superset import db
from superset.extensions import celery_app
from superset.utils.core import check_is_safe_zip
from superset.utils.file import sanitize_title

from superset.ai_studio.models import AIStudioAttachment
from superset.ai_studio.services import AIStudioError

logger = logging.getLogger(__name__)

_IMAGE_CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}
_DOCUMENT_CONTENT_TYPES = {
    "txt": "text/plain",
    "md": "text/markdown",
    "csv": "text/csv",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_CHUNK_SIZE = 65536


def _allowed_image_extensions() -> frozenset[str]:
    return frozenset(
        current_app.config.get(
            "AI_STUDIO_ATTACHMENT_ALLOWED_IMAGE_EXTENSIONS",
            frozenset(_IMAGE_CONTENT_TYPES),
        )
    )


def _allowed_document_extensions() -> frozenset[str]:
    return frozenset(
        current_app.config.get(
            "AI_STUDIO_ATTACHMENT_ALLOWED_DOCUMENT_EXTENSIONS",
            frozenset(_DOCUMENT_CONTENT_TYPES),
        )
    )


def _attachment_dir() -> str:
    directory = current_app.config.get(
        "AI_STUDIO_ATTACHMENT_DIR", "/app/superset_home/ai_studio_attachments"
    )
    os.makedirs(directory, exist_ok=True)
    return directory


def _max_bytes() -> int:
    return int(current_app.config.get("AI_STUDIO_ATTACHMENT_MAX_BYTES", 10 * 1024 * 1024))


def _max_extracted_chars() -> int:
    return int(current_app.config.get("AI_STUDIO_ATTACHMENT_MAX_EXTRACTED_CHARS", 40_000))


def _classify(extension: str) -> tuple[str, str]:
    """Returns (kind, content_type) for an allow-listed extension, or raises."""
    if extension in _allowed_image_extensions() and extension in _IMAGE_CONTENT_TYPES:
        return "image", _IMAGE_CONTENT_TYPES[extension]
    if extension in _allowed_document_extensions() and extension in _DOCUMENT_CONTENT_TYPES:
        return "document", _DOCUMENT_CONTENT_TYPES[extension]
    raise AIStudioError(f"Files of type .{extension} are not supported.")


def _write_stream_capped(file: FileStorage, dest_path: str) -> int:
    """Writes file.stream to dest_path in bounded chunks, never trusting a
    client-supplied Content-Length -- aborts and removes the partial file
    the instant the real byte count crosses the cap."""
    max_bytes = _max_bytes()
    written = 0
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = file.stream.read(_CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise AIStudioError(
                        f"Attachments must be {max_bytes // (1024 * 1024)}MB or smaller."
                    )
                out.write(chunk)
    except Exception:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise
    return written


def _validate_image(path: str) -> None:
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(path) as img:
            img.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise AIStudioError("This file is not a valid image.") from exc


def _extract_pdf_text(path: str) -> str:
    import pypdf

    try:
        reader = pypdf.PdfReader(path)
        if reader.is_encrypted:
            raise AIStudioError("Encrypted PDFs are not supported.")
        if not reader.pages:
            raise AIStudioError("This PDF has no readable pages.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except AIStudioError:
        raise
    except Exception as exc:
        raise AIStudioError("This file is not a valid PDF.") from exc
    return text


def _extract_docx_text(path: str) -> str:
    import docx

    # .docx is itself a zip container -- reuse Superset's existing zip-bomb
    # guard (already used for columnar/.zip dataset uploads) before handing
    # it to python-docx.
    try:
        with zipfile.ZipFile(path) as zf:
            check_is_safe_zip(zf)
    except AIStudioError:
        raise
    except Exception as exc:
        raise AIStudioError("This file is not a valid Word document.") from exc
    try:
        document = docx.Document(path)
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:
        raise AIStudioError("This file is not a valid Word document.") from exc
    return text


def _extract_plain_text(path: str) -> str:
    try:
        with open(path, "rb") as handle:
            return handle.read().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AIStudioError("This file could not be read as text (not UTF-8).") from exc


def _extract_text(path: str, extension: str) -> str:
    if extension == "pdf":
        text = _extract_pdf_text(path)
    elif extension == "docx":
        text = _extract_docx_text(path)
    else:
        text = _extract_plain_text(path)
    max_chars = _max_extracted_chars()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"
    return text


def save_attachment(user: User, file: FileStorage) -> AIStudioAttachment:
    """Validates and persists one uploaded attachment. Raises AIStudioError
    on any extension, size, or content validation failure -- never leaves a
    partially-written file behind."""
    if not file.filename:
        raise AIStudioError("A file is required.")
    extension = os.path.splitext(file.filename)[1].lstrip(".").lower()
    kind, content_type = _classify(extension)

    storage_filename = f"{uuid4().hex}.{extension}"
    dest_path = os.path.join(_attachment_dir(), storage_filename)
    size_bytes = _write_stream_capped(file, dest_path)
    if size_bytes == 0:
        os.remove(dest_path)
        raise AIStudioError("The uploaded file is empty.")

    extracted_text: str | None = None
    try:
        if kind == "image":
            _validate_image(dest_path)
        else:
            extracted_text = _extract_text(dest_path, extension)
    except Exception:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise

    attachment = AIStudioAttachment(
        user_id=user.id,
        kind=kind,
        extension=extension,
        content_type=content_type,
        original_filename=sanitize_title(file.filename)[:255],
        storage_filename=storage_filename,
        size_bytes=size_bytes,
        extracted_text=extracted_text,
    )
    db.session.add(attachment)
    db.session.commit()
    return attachment


def _get_owned(user: User, attachment_id: str) -> AIStudioAttachment:
    """Identical failure whether the id is missing or owned by someone
    else, so a probe can't distinguish 'doesn't exist' from 'not yours'."""
    attachment = db.session.get(AIStudioAttachment, attachment_id)
    if not attachment or attachment.user_id != user.id:
        raise AIStudioError("Attachment not found.")
    return attachment


def resolve_attachments_for_chat(
    user: User, attachment_ids: list[str], provider_capabilities: list[str]
) -> tuple[list[dict[str, Any]], str | None]:
    """Returns (image_content_parts, document_text) for a chat request.
    image_content_parts is an OpenAI-style list of {"type": "image_url", ...}
    parts; document_text is a single string to inject as its own system
    message, or None if no documents were attached.
    """
    if not attachment_ids:
        return [], None
    max_per_message = int(
        current_app.config.get("AI_STUDIO_ATTACHMENT_MAX_PER_MESSAGE", 5)
    )
    if len(attachment_ids) > max_per_message:
        raise AIStudioError(f"Attach at most {max_per_message} files to a message.")

    image_parts: list[dict[str, Any]] = []
    document_sections: list[str] = []
    for attachment_id in attachment_ids:
        attachment = _get_owned(user, attachment_id)
        if attachment.kind == "image":
            if "vision" not in provider_capabilities:
                raise AIStudioError(
                    "The selected provider does not support image attachments. "
                    "Choose a vision-capable model."
                )
            path = os.path.join(_attachment_dir(), attachment.storage_filename)
            with open(path, "rb") as handle:
                encoded = base64.b64encode(handle.read()).decode("ascii")
            image_parts.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{attachment.content_type};base64,{encoded}"
                    },
                }
            )
        else:
            document_sections.append(
                f"--- {attachment.original_filename} ---\n{attachment.extracted_text or ''}"
            )
    document_text = "\n\n".join(document_sections) if document_sections else None
    return image_parts, document_text


def get_attachment_for_download(user: User, attachment_id: str) -> tuple[str, str, str]:
    attachment = _get_owned(user, attachment_id)
    path = os.path.join(_attachment_dir(), attachment.storage_filename)
    if not os.path.exists(path):
        raise AIStudioError("Attachment not found.")
    return path, attachment.content_type, attachment.original_filename


def delete_attachment(user: User, attachment_id: str) -> None:
    attachment = _get_owned(user, attachment_id)
    path = os.path.join(_attachment_dir(), attachment.storage_filename)
    db.session.delete(attachment)
    db.session.commit()
    if os.path.exists(path):
        os.remove(path)


def _purge_old_attachments_impl(retention_days: int | None = None) -> dict[str, int]:
    days = retention_days
    if days is None:
        days = int(current_app.config.get("AI_STUDIO_ATTACHMENT_RETENTION_DAYS", 30))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.session.query(AIStudioAttachment)
        .filter(AIStudioAttachment.created_on < cutoff)
        .all()
    )
    removed = 0
    for row in rows:
        path = os.path.join(_attachment_dir(), row.storage_filename)
        try:
            db.session.delete(row)
            db.session.commit()
            if os.path.exists(path):
                os.remove(path)
            removed += 1
        except Exception:  # noqa: BLE001 - one bad row should not stop the sweep
            db.session.rollback()
            logger.exception("Failed to purge AI Studio attachment %s", row.id)
    return {"removed": removed}


@celery_app.task(name="ai_studio.prune_old_attachments")
def prune_old_attachments() -> dict[str, int]:
    """Beat entry point -- runs regardless of AI_STUDIO_ENABLED, since disk
    cleanup shouldn't depend on whether the feature is currently toggled on."""
    return _purge_old_attachments_impl()
