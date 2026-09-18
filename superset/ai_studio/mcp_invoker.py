"""Server-enforced, allow-listed invocation of MCP tools from AI Studio chat.

Only read-only tools an operator has explicitly named in
``AI_STUDIO_MCP_TOOL_ALLOWLIST`` may ever be called, and only under the real
requesting user's identity -- never a service account or a client-supplied
identity. See ``api.py``'s ``chat()`` for why every call through this module
happens synchronously inside the original web request, not inside
``ai_studio/tasks.py``'s async GTF task.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from flask import current_app
from flask_appbuilder.security.sqla.models import User

from superset import security_manager
from superset.utils.core import override_user

logger = logging.getLogger(__name__)


class MCPToolInvoker:
    """Wraps the fork's own in-process MCP client (``fastmcp.Client``) so a
    tool call goes through FastMCP's real auth/RBAC/logging middleware chain
    -- the same path ``mcp.local_provider`` enforces for any other caller --
    rather than calling a tool function directly and reimplementing that
    enforcement.

    Must be used from within a real Flask request context.
    ``superset.mcp_service.auth._setup_user_context()`` explicitly clears
    ``g.user`` whenever ``has_request_context()`` is False, precisely to stop
    a stale identity leaking into a headless worker call -- so unlike
    ``superset.utils.core.override_user``'s use elsewhere in this codebase
    for Celery tasks, it only resolves correctly here because AI Studio's
    tool round trips run synchronously in the original web request, before
    the final answer is handed off to the async GTF task.
    """

    @staticmethod
    def allowlist() -> frozenset[str]:
        return frozenset(current_app.config.get("AI_STUDIO_MCP_TOOL_ALLOWLIST", ()))

    @classmethod
    def is_allowed(cls, tool_name: str) -> bool:
        return tool_name in cls.allowlist()

    @classmethod
    def tool_schemas(cls) -> list[dict[str, Any]]:
        """OpenAI-style ``tools=[...]`` schemas for allow-listed tools this
        session can actually see, cross-checked against Superset RBAC (the
        same check ``MCPRegistry.public_tools()`` already applies for the
        read-only "MCP Tools" tab). Never advertises a tool the allow-list
        names but the live registration doesn't expose, or a write-shaped
        tool a config mistake allow-listed -- read-only is this increment's
        whole invariant, enforced here rather than only in code review.
        """
        allowed = cls.allowlist()
        if not allowed:
            return []
        try:
            from superset.mcp_service.app import mcp
        except ImportError:
            return []
        schemas: list[dict[str, Any]] = []
        for key, component in mcp.local_provider._components.items():
            if not key.startswith("tool:"):
                continue
            fn = getattr(component, "fn", None)
            name = getattr(component, "name", None)
            if not fn or not name or name not in allowed:
                continue
            method = getattr(fn, "_method_permission_name", "read")
            if method != "read":
                logger.warning(
                    "AI Studio allow-list names non-read-only tool %s; ignoring it.",
                    name,
                )
                continue
            view = getattr(fn, "_class_permission_name", None)
            if not (view and security_manager.can_access(f"can_{method}", view)):
                continue
            parameters = getattr(component, "parameters", None) or {
                "type": "object",
                "properties": {},
            }
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": getattr(component, "description", "") or "",
                        "parameters": parameters,
                    },
                }
            )
        return schemas

    @classmethod
    def call(
        cls, user: User, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute one allow-listed tool call under ``user``'s real identity.

        Returns ``{"ok": True, "result": ...}`` or ``{"ok": False, "error":
        ...}`` -- always a safe, model-displayable dict, never a raw
        exception or stack trace.
        """
        if not cls.is_allowed(tool_name):
            return {
                "ok": False,
                "error": "This tool is not permitted in this context.",
            }
        try:
            return asyncio.run(cls._call_async(user, tool_name, arguments))
        except Exception:  # noqa: BLE001 - never leak an internal trace to the model
            logger.exception("AI Studio MCP tool call failed: %s", tool_name)
            return {"ok": False, "error": "The tool call could not be completed."}

    @staticmethod
    async def _call_async(
        user: User, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        from fastmcp import Client
        from fastmcp.exceptions import ToolError

        from superset.mcp_service.app import mcp

        with override_user(user):
            try:
                async with Client(mcp) as client:
                    result = await client.call_tool(tool_name, arguments)
            except ToolError as exc:
                # ToolError is this fork's own safe, client-displayable tool
                # error (schema validation, an RBAC denial, a caught domain
                # exception) -- relaying it is the intended contract, unlike
                # an unexpected exception (caught by the outer handler).
                return {"ok": False, "error": str(exc)}

        structured = getattr(result, "structured_content", None)
        if isinstance(structured, dict):
            return {"ok": True, "result": structured}
        content = getattr(result, "content", None) or []
        if content and hasattr(content[0], "text"):
            try:
                return {"ok": True, "result": json.loads(content[0].text)}
            except (TypeError, ValueError):
                return {"ok": True, "result": content[0].text}
        return {"ok": True, "result": None}
