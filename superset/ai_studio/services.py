"""Authorization, context, provider, and staged-change services for AI Studio."""
from __future__ import annotations

import json
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
from superset.models.core import Database
from superset.models.dashboard import Dashboard
from superset.models.slice import Slice
from superset.sql.parse import Table
from superset.ai_studio.models import (
    AIStudioChangeSet,
    AIStudioCheckpoint,
    AIStudioProvider,
)


class AIStudioError(Exception):
    """Safe, user-displayable AI Studio error."""


class PermissionDenied(AIStudioError):
    pass


class AdminOnlyError(PermissionDenied):
    """Raised when a non-admin calls an admin-only AI Studio endpoint."""


def _json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _require_admin() -> None:
    if not security_manager.is_admin():
        raise AdminOnlyError("Only an administrator can manage AI providers.")


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

    @staticmethod
    def sql_lab(
        user: User,
        database_id: int,
        schema: str | None = None,
        table: str | None = None,
    ) -> dict[str, Any]:
        """Bounded SQL Lab context: the connected database's identity plus,
        when a table is given, its column metadata -- never row data. The
        table/schema themselves come from the browser's own current tab
        (there is no server-side "SQL Lab session" resource with an id to
        re-resolve the way a dashboard has one), but the database access
        check and the column introspection are both done here, server-side,
        under the real request user -- the same trust split ``dashboard()``
        applies to a client-supplied dashboard id.
        """
        database = db.session.get(Database, database_id)
        if not database or not security_manager.can_access_database(database):
            raise PermissionDenied("You do not have access to this database.")

        columns: list[dict[str, Any]] = []
        if table:
            try:
                columns = [
                    {"name": col.get("column_name"), "type": str(col.get("type") or "")}
                    for col in database.get_columns(
                        Table(table=table, schema=schema)
                    )
                ]
            except Exception:  # noqa: BLE001 - introspection can fail for many
                # engine-specific reasons (missing table, transient
                # connection error); the chat should still proceed with
                # whatever context it does have rather than 500.
                columns = []

        return {
            "database": {
                "id": database.id,
                "name": database.database_name,
                "backend": database.backend,
            },
            "schema": schema,
            "table": table,
            "columns": columns,
            "permissions": {"database_read": True},
        }


def _provider_public_dict(provider: AIStudioProvider) -> dict[str, Any]:
    return {
        "id": str(provider.id),
        "label": provider.label,
        "models": _json(provider.models_json, []),
        "default_model": provider.default_model,
        "capabilities": _json(provider.capabilities_json, ["chat"]),
        # Only the tier names are public; effort_param (how to pass the
        # chosen tier to the upstream API) is a server-side request-shaping
        # detail, not something the browser needs.
        "effort_levels": _json(provider.effort_levels_json, []),
        "configured": bool(provider.api_key),
    }


def _provider_admin_dict(provider: AIStudioProvider) -> dict[str, Any]:
    return {
        **_provider_public_dict(provider),
        "base_url": provider.base_url,
        "has_api_key": bool(provider.api_key),
        "effort_param": provider.effort_param,
        "enabled": provider.enabled,
        "created_on": provider.created_on.isoformat() if provider.created_on else None,
        "changed_on": provider.changed_on.isoformat() if provider.changed_on else None,
    }


class ProviderRegistry:
    """Admin-managed, DB-backed provider registry; browser clients never
    receive secrets. Providers are added/edited/enabled through
    AdminProviderService (Admin-only), not deployment configuration.
    """

    @staticmethod
    def public() -> list[dict[str, Any]]:
        rows = (
            db.session.query(AIStudioProvider)
            .filter(AIStudioProvider.enabled.is_(True))
            .order_by(AIStudioProvider.label)
            .all()
        )
        return [_provider_public_dict(row) for row in rows]

    @staticmethod
    def _resolve_provider(provider_id: str) -> AIStudioProvider:
        provider = db.session.get(AIStudioProvider, provider_id)
        if not provider or not provider.enabled:
            raise AIStudioError("The requested AI provider is not enabled by an administrator.")
        return provider

    @staticmethod
    def capabilities(provider_id: str) -> list[str]:
        """Public accessor for a provider's declared capability tags (e.g.
        "vision") -- lets callers outside this module (attachments.py,
        api.py) make capability-gated decisions without reaching into
        _resolve_provider/_json directly.
        """
        provider = ProviderRegistry._resolve_provider(provider_id)
        return _json(provider.capabilities_json, ["chat"])

    @staticmethod
    def _post_chat_completion(
        provider: AIStudioProvider,
        model: str | None,
        messages: list[dict[str, Any]],
        *,
        effort: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """One raw OpenAI-compatible ``/chat/completions`` call.

        Returns the first choice's ``message`` dict (may carry ``content``
        and/or ``tool_calls``) plus ``usage`` merged in -- shared by both
        ``chat()`` (a finished, tool-free answer) and ``chat_step()`` (one
        turn of a tool-calling round trip, which may not be finished yet).
        """
        endpoint = provider.base_url.rstrip("/") + "/chat/completions"
        request_body: dict[str, Any] = {
            "model": model or provider.default_model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            request_body["tools"] = tools
        effort_levels = _json(provider.effort_levels_json, [])
        # Re-validate against the provider's own declared levels server-side;
        # never forward a client-supplied tier the operator hasn't opted into.
        if effort and provider.effort_param and effort in effort_levels:
            request_body[provider.effort_param] = effort
        payload = json.dumps(request_body).encode()
        # Not every OpenAI-compatible endpoint requires a key (e.g. a local,
        # unauthenticated Ollama server) -- only attach one if the admin set
        # one, rather than refusing to try the request at all.
        headers = {"Content-Type": "application/json"}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"
        request = Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=45) as response:  # nosec B310: admin-configured endpoint
                body = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError) as exc:
            raise AIStudioError("The provider could not complete this request. Check its connection and retry.") from exc
        choices = body.get("choices", [])
        if not choices:
            raise AIStudioError("The provider returned no response.")
        message = dict(choices[0].get("message", {}))
        message["usage"] = body.get("usage")
        return message

    @staticmethod
    def chat(
        provider_id: str,
        model: str | None,
        messages: list[dict[str, str]],
        effort: str | None = None,
    ) -> dict[str, Any]:
        provider = ProviderRegistry._resolve_provider(provider_id)
        message = ProviderRegistry._post_chat_completion(provider, model, messages, effort=effort)
        return {
            "content": message.get("content", ""),
            "usage": message.get("usage"),
            "provider": provider_id,
            "model": model or provider.default_model,
        }

    @staticmethod
    def chat_step(
        provider_id: str,
        model: str | None,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        effort: str | None = None,
    ) -> dict[str, Any]:
        """One turn of a tool-calling round trip (api.py's synchronous
        tool-resolution phase, before the final answer goes to the async GTF
        task) -- returns the raw ``message`` (``content`` and/or
        ``tool_calls``), not the finished shape ``chat()`` returns, since the
        caller here may still have more rounds ahead of it.
        """
        provider = ProviderRegistry._resolve_provider(provider_id)
        return ProviderRegistry._post_chat_completion(
            provider, model, messages, effort=effort, tools=tools
        )


class AdminProviderService:
    """Admin-only CRUD for DB-stored AI providers. api_key is write-only:
    accepted on create/update, encrypted at rest (AIStudioProvider.api_key
    is an EncryptedType column, the same mechanism Database.password uses),
    and never included in any response — callers only ever see
    has_api_key/configured.
    """

    @staticmethod
    def list_all() -> list[dict[str, Any]]:
        _require_admin()
        rows = db.session.query(AIStudioProvider).order_by(AIStudioProvider.label).all()
        return [_provider_admin_dict(row) for row in rows]

    @staticmethod
    def get(provider_id: str) -> dict[str, Any]:
        _require_admin()
        provider = db.session.get(AIStudioProvider, provider_id)
        if not provider:
            raise AIStudioError("Provider not found.")
        return _provider_admin_dict(provider)

    @staticmethod
    def create(user: User, payload: dict[str, Any]) -> dict[str, Any]:
        _require_admin()
        label = str(payload.get("label") or "").strip()
        base_url = str(payload.get("base_url") or "").strip()
        if not label or not base_url:
            raise AIStudioError("A label and base URL are required.")
        provider = AIStudioProvider(
            label=label,
            base_url=base_url,
            default_model=(str(payload["default_model"]).strip() if payload.get("default_model") else None),
            models_json=json.dumps(_string_list(payload.get("models"))),
            capabilities_json=json.dumps(_string_list(payload.get("capabilities")) or ["chat"]),
            effort_levels_json=json.dumps(_string_list(payload.get("effort_levels"))),
            effort_param=(str(payload["effort_param"]).strip() if payload.get("effort_param") else None),
            enabled=bool(payload.get("enabled", True)),
            created_by_fk=user.id,
            changed_by_fk=user.id,
        )
        api_key = payload.get("api_key")
        if api_key:
            provider.api_key = str(api_key)
        db.session.add(provider)
        db.session.commit()
        return _provider_admin_dict(provider)

    @staticmethod
    def update(user: User, provider_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        _require_admin()
        provider = db.session.get(AIStudioProvider, provider_id)
        if not provider:
            raise AIStudioError("Provider not found.")
        if "label" in payload:
            label = str(payload.get("label") or "").strip()
            if not label:
                raise AIStudioError("Label cannot be empty.")
            provider.label = label
        if "base_url" in payload:
            base_url = str(payload.get("base_url") or "").strip()
            if not base_url:
                raise AIStudioError("Base URL cannot be empty.")
            provider.base_url = base_url
        if "default_model" in payload:
            provider.default_model = str(payload["default_model"]).strip() if payload.get("default_model") else None
        if "models" in payload:
            provider.models_json = json.dumps(_string_list(payload.get("models")))
        if "capabilities" in payload:
            provider.capabilities_json = json.dumps(_string_list(payload.get("capabilities")) or ["chat"])
        if "effort_levels" in payload:
            provider.effort_levels_json = json.dumps(_string_list(payload.get("effort_levels")))
        if "effort_param" in payload:
            provider.effort_param = str(payload["effort_param"]).strip() if payload.get("effort_param") else None
        if "enabled" in payload:
            provider.enabled = bool(payload.get("enabled"))
        # Write-only: only touch the stored secret if a real replacement was
        # actually submitted. There is no mask-sentinel round-trip to worry
        # about since the real key is never sent back in the first place.
        api_key = payload.get("api_key")
        if api_key:
            provider.api_key = str(api_key)
        provider.changed_by_fk = user.id
        provider.changed_on = datetime.now(timezone.utc)
        db.session.commit()
        return _provider_admin_dict(provider)

    @staticmethod
    def delete(provider_id: str) -> None:
        _require_admin()
        provider = db.session.get(AIStudioProvider, provider_id)
        if not provider:
            raise AIStudioError("Provider not found.")
        db.session.delete(provider)
        db.session.commit()


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
