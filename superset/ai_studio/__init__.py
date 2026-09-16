"""Superset AI Studio integration.

This package deliberately sits beside (rather than inside) the MCP service.
MCP remains the externally consumable, RBAC-aware tool plane; AI Studio is the
in-product orchestration and review plane.
"""

def register_ai_studio(app):
    # Lazy import prevents SQLAlchemy model registration from importing Flask
    # routes while Superset is still importing its model registry.
    from superset.ai_studio.api import register_ai_studio as _register

    _register(app)


__all__ = ["register_ai_studio"]
