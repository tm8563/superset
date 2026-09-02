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
import logging
from typing import Any

from superset import db, security_manager
from superset.dashboards.filter_presets.commands.base import BaseFilterPresetCommand
from superset.dashboards.filter_presets.types import DashboardFilterPresetPayload
from superset.key_value.models import KeyValueEntry
from superset.utils.core import get_user_id

logger = logging.getLogger(__name__)


class ListFilterPresetsCommand(BaseFilterPresetCommand):
    def __init__(self, dashboard_id: str):
        self.dashboard_id = dashboard_id

    def run(self) -> list[DashboardFilterPresetPayload]:
        dashboard = self.get_dashboard(self.dashboard_id)
        current_user_id = get_user_id()
        is_admin = security_manager.is_admin()

        entries = (
            db.session.query(KeyValueEntry)
            .filter(KeyValueEntry.resource == self.resource_name.value)
            .all()
        )

        presets: list[DashboardFilterPresetPayload] = []
        target_dash_id = str(dashboard.id)
        target_dash_uuid = str(dashboard.uuid)

        for entry in entries:
            try:
                payload: dict[str, Any] = self.codec.decode(entry.value)
            except Exception as ex:
                logger.warning("Skipping corrupted filter preset entry id=%s: %s", entry.id, ex)
                continue

            entry_dash_id = str(payload.get("dashboard_id", ""))
            if entry_dash_id not in (target_dash_id, target_dash_uuid):
                continue

            is_shared = bool(payload.get("is_shared", False))
            is_owner = (
                entry.created_by_fk is not None
                and current_user_id is not None
                and entry.created_by_fk == current_user_id
            )

            # Visiblity rule: shared presets are visible to all dashboard viewers;
            # personal presets are visible only to the owner or admins.
            if is_shared or is_owner or is_admin:
                payload["is_owner"] = is_owner
                presets.append(payload)  # type: ignore[arg-type]

        # Sort presets: Shared first, then by created_on descending
        presets.sort(
            key=lambda p: (
                not p.get("is_shared", False),
                p.get("created_on", "") or "",
            ),
            reverse=False,
        )

        return presets

    def validate(self) -> None:
        pass
