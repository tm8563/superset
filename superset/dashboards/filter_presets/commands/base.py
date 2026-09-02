# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from abc import ABC
from typing import Any, Optional

from superset import db, security_manager
from superset.commands.base import BaseCommand
from superset.commands.dashboard.exceptions import (
    DashboardAccessDeniedError,
    DashboardNotFoundError,
)
from superset.daos.dashboard import DashboardDAO
from superset.dashboards.filter_presets.types import (
    DASHBOARD_FILTER_PRESET_RESOURCE,
    UserSummary,
)
from superset.key_value.types import JsonKeyValueCodec
from superset.models.dashboard import Dashboard
from superset.utils.core import get_user_id


class BaseFilterPresetCommand(BaseCommand, ABC):
    resource_name = DASHBOARD_FILTER_PRESET_RESOURCE
    codec = JsonKeyValueCodec()

    def get_dashboard(self, dashboard_id_or_slug: str) -> Dashboard:
        """Fetch and authorize dashboard access."""
        dashboard = DashboardDAO.get_by_id_or_slug(dashboard_id_or_slug)
        if not dashboard:
            raise DashboardNotFoundError()
        try:
            security_manager.raise_for_access(dashboard=dashboard)
        except Exception as ex:
            raise DashboardAccessDeniedError() from ex
        return dashboard

    def can_edit_dashboard(self, dashboard: Dashboard) -> bool:
        """Check whether current user can edit the dashboard (for Shared presets)."""
        return security_manager.is_admin() or security_manager.can_access(
            "can_write", "Dashboard"
        ) or (
            hasattr(dashboard, "owners")
            and any(owner.id == get_user_id() for owner in (dashboard.owners or []))
        )

    def get_user_summary(self, user_id: Optional[int] = None) -> Optional[UserSummary]:
        """Fetch user summary dictionary."""
        uid = user_id or get_user_id()
        if not uid:
            return None
        user = security_manager.get_user_by_id(uid)
        if not user:
            return None
        return {
            "id": user.id,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "username": user.username or "",
        }
