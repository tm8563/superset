"""Authorization, context, provider, and staged-change services for AI Studio."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app
from flask_appbuilder.security.sqla.models import User

from superset import db, security_manager
from superset.commands.chart.update import UpdateChartCommand
from superset.commands.dashboard.update import UpdateDashboardCommand
from superset.exceptions import SupersetSecurityException
from superset.models.dashboard import Dashboard
from superset.models.slice import Slice
from superset.ai_studio.models import AIStudioChangeSet, AIStudioCheckpoint


class AIStudioError(Exception):
    """Safe, user-displayable AI Studio error."""


class PermissionDenied(AIStudioError):
    pass


def _json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _serialize_dashboard(dashboard: Dashboard) -> dict[str, Any]:
    return {
        "id": dashboard.id,
        "title": dashboard.dashboard_title,
        "slug": dashboard.slug,
        "position_json": dashboard.position_json or "{}",
        "json_metadata": dashboard.json_metadata or "{}",
        "css": dashboard.css or "",
    }


def _serialize_chart(chart: Slice) -> dict[str, Any]:
    return {
        "id": chart.id,
        "slice_name": chart.slice_name,
        "viz_type": chart.viz_type,
        "params": chart.params or "{}",
        "description": chart.description or "",
    }


class ContextBuilder:
    """Builds a deliberately bounded context after checking Superset RBAC."""

    @staticmethod
    def dashboard(user: User, dashboard_id: int) -> dict[str, Any]:
        dashboard = db.session.get(Dashboard, dashboard_id)
        if not dashboard or not security_manager.can_access_dashboard(dashboard):
            raise PermissionDenied("You do not have access to this dashboard.")

        charts = []
        for chart in dashboard.slices:
            if security_manager.can_access_chart(chart):
                charts.append(
                    {
                        "id": chart.id,
                        "title": chart.slice_name,
                        "viz_type": chart.viz_type,
                        "dataset_id": chart.datasource_id,
                    }
                )
        metadata = _json(dashboard.json_metadata, {})
        return {
            "dashboard": {
                "id": dashboard.id,
                "title": dashboard.dashboard_title,
                "slug": dashboard.slug,
                "chart_count": len(charts),
                "native_filters": metadata.get("native_filter_configuration", []),
            },
            "charts": charts,
            "permissions": {
                "dashboard_read": True,
                "dashboard_write": bool(
                    security_manager.can_access("can_write", "Dashboard")
                ),
            },
        }


class ProviderRegistry:
    """Config-only provider registry; browser clients never receive secrets."""

    @staticmethod
    def public() -> list[dict[str, Any]]:
        configured = current_app.config.get("AI_STUDIO_PROVIDERS", [])
        providers = []
        for provider in configured:
            if not isinstance(provider, dict) or not provider.get("id"):
                continue
            providers.append(
                {
                    "id": provider["id"],
                    "label": provider.get("label", provider["id"]),
                    "models": provider.get("models", []),
                    "default_model": provider.get("default_model"),
                    "capabilities": provider.get("capabilities", ["chat"]),
                    # Only the tier names are public; effort_param (how to pass
                    # the chosen tier to the upstream API) is a server-side
                    # request-shaping detail, not something the browser needs.
                    "effort_levels": provider.get("effort_levels", []),
                    "configured": bool(provider.get("api_key_env") and os.getenv(provider["api_key_env"])),
                }
            )
        return providers

    @staticmethod
    def chat(
        provider_id: str,
        model: str | None,
        messages: list[dict[str, str]],
        effort: str | None = None,
    ) -> dict[str, Any]:
        provider = next((p for p in current_app.config.get("AI_STUDIO_PROVIDERS", []) if p.get("id") == provider_id), None)
        if not provider:
            raise AIStudioError("The requested AI provider is not enabled by an administrator.")
        key = os.getenv(provider.get("api_key_env", ""))
        if not key:
            raise AIStudioError("This provider is not configured on the server.")
        endpoint = provider.get("base_url", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        request_body: dict[str, Any] = {"model": model or provider.get("default_model"), "messages": messages, "stream": False}
        effort_param = provider.get("effort_param")
        # Re-validate against the provider's own declared levels server-side;
        # never forward a client-supplied tier the operator hasn't opted into.
        if effort and effort_param and effort in provider.get("effort_levels", []):
            request_body[effort_param] = effort
        payload = json.dumps(request_body).encode()
        request = Request(endpoint, data=payload, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=45) as response:  # nosec B310: admin-configured endpoint
                body = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError) as exc:
            raise AIStudioError("The provider could not complete this request. Check its connection and retry.") from exc
        choices = body.get("choices", [])
        if not choices:
            raise AIStudioError("The provider returned no response.")
        return {"content": choices[0].get("message", {}).get("content", ""), "usage": body.get("usage"), "provider": provider_id, "model": model or provider.get("default_model")}


class MCPRegistry:
    """Read the live MCP registration rather than maintaining a shadow list."""

    @staticmethod
    def public_tools() -> list[dict[str, Any]]:
        if not current_app.config.get("MCP_RBAC_ENABLED", False):
            return []
        try:
            # The fork's MCP app registers its decorated tools in this live
            # component provider. Import is request-lazy so normal Superset
            # page loads do not pay the FastMCP import cost.
            from superset.mcp_service.app import mcp
        except ImportError:
            return []
        result = []
        for key, component in mcp.local_provider._components.items():
            if not key.startswith("tool:"):
                continue
            fn = getattr(component, "fn", None)
            name = getattr(component, "name", None)
            if not fn or not name:
                continue
            view = getattr(fn, "_class_permission_name", None)
            method = getattr(fn, "_method_permission_name", "read")
            can_use = bool(view and security_manager.can_access(f"can_{method}", view))
            result.append(
                {
                    "name": name,
                    "group": (view or "System"),
                    "permission": f"can_{method} on {view or 'System'}",
                    "can_use": can_use,
                }
            )
        return sorted(result, key=lambda item: (item["group"], item["name"]))


class ChangeStagingService:
    """Creates/apply/restores explicit, immutable-before-snapshot change sets."""

    @staticmethod
    def _resource(user: User, resource_type: str, resource_id: str) -> tuple[Any, dict[str, Any]]:
        if not resource_id.isdigit():
            raise AIStudioError("The proposed resource identifier is invalid.")
        if resource_type == "dashboard":
            resource = db.session.get(Dashboard, int(resource_id))
            if not resource or not security_manager.can_access_dashboard(resource):
                raise PermissionDenied("You do not have access to this dashboard.")
            try:
                security_manager.raise_for_editorship(resource)
            except SupersetSecurityException as exc:
                raise PermissionDenied("You do not have permission to edit this dashboard.") from exc
            return resource, _serialize_dashboard(resource)
        if resource_type == "chart":
            resource = db.session.get(Slice, int(resource_id))
            if not resource or not security_manager.can_access_chart(resource):
                raise PermissionDenied("You do not have access to this chart.")
            try:
                security_manager.raise_for_editorship(resource)
            except SupersetSecurityException as exc:
                raise PermissionDenied("You do not have permission to edit this chart.") from exc
            return resource, _serialize_chart(resource)
        raise AIStudioError("Only dashboard and chart changes can be applied by AI Studio currently.")

    @classmethod
    def stage(cls, user: User, payload: dict[str, Any]) -> AIStudioChangeSet:
        resource_type = str(payload.get("resource_type", ""))
        resource_id = str(payload.get("resource_id", ""))
        _, before = cls._resource(user, resource_type, resource_id)
        after = payload.get("after")
        if not isinstance(after, dict) or not after:
            raise AIStudioError("A proposed after-state is required.")
        change = AIStudioChangeSet(
            user_id=user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            title=str(payload.get("title") or f"Update {resource_type}"),
            before_json=json.dumps(before),
            after_json=json.dumps(after),
            rationale=str(payload.get("rationale") or ""),
        )
        db.session.add(change)
        db.session.commit()
        return change

    @classmethod
    def apply(cls, user: User, change: AIStudioChangeSet) -> AIStudioCheckpoint:
        if change.status != "pending":
            raise AIStudioError("Only pending changes can be applied.")
        _, current = cls._resource(user, change.resource_type, change.resource_id)
        checkpoint = AIStudioCheckpoint(change_set_id=change.id, user_id=user.id, resource_type=change.resource_type, resource_id=change.resource_id, snapshot_json=json.dumps(current))
        after = _json(change.after_json, {})
        if change.resource_type == "dashboard":
            allowed = {k: v for k, v in after.items() if k in {"dashboard_title", "slug", "position_json", "json_metadata", "css", "published"}}
            UpdateDashboardCommand(int(change.resource_id), allowed).run()
        else:
            allowed = {k: v for k, v in after.items() if k in {"slice_name", "description", "viz_type", "params"}}
            UpdateChartCommand(int(change.resource_id), allowed).run()
        change.status = "applied"
        change.applied_on = datetime.now(timezone.utc)
        db.session.add(checkpoint)
        db.session.commit()
        return checkpoint

    @classmethod
    def restore(cls, user: User, checkpoint: AIStudioCheckpoint) -> None:
        cls._resource(user, checkpoint.resource_type, checkpoint.resource_id)
        snapshot = _json(checkpoint.snapshot_json, {})
        if checkpoint.resource_type == "dashboard":
            allowed = {k: v for k, v in snapshot.items() if k in {"dashboard_title", "slug", "position_json", "json_metadata", "css", "published"}}
            UpdateDashboardCommand(int(checkpoint.resource_id), allowed).run()
        else:
            allowed = {k: v for k, v in snapshot.items() if k in {"slice_name", "description", "viz_type", "params"}}
            UpdateChartCommand(int(checkpoint.resource_id), allowed).run()
        checkpoint.restored_on = datetime.now(timezone.utc)
        db.session.commit()


def change_to_dict(change: AIStudioChangeSet) -> dict[str, Any]:
    return {"id": str(change.id), "resource_type": change.resource_type, "resource_id": change.resource_id, "title": change.title, "status": change.status, "before": _json(change.before_json, {}), "after": _json(change.after_json, {}), "rationale": change.rationale, "created_on": change.created_on.isoformat()}
