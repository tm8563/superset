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
from uuid import UUID

from superset import security_manager
from superset.daos.key_value import KeyValueDAO
from superset.dashboards.filter_presets.commands.base import BaseFilterPresetCommand
from superset.dashboards.filter_presets.exceptions import (
    FilterPresetAccessDeniedError,
    FilterPresetNotFoundError,
)
from superset.dashboards.filter_presets.types import DashboardFilterPresetPayload
from superset.utils.core import get_user_id

logger = logging.getLogger(__name__)


class GetFilterPresetCommand(BaseFilterPresetCommand):
    def __init__(self, dashboard_id: str, preset_id: str):
        self.dashboard_id = dashboard_id
        self.preset_id = preset_id

    def run(self) -> DashboardFilterPresetPayload:
        dashboard = self.get_dashboard(self.dashboard_id)
        try:
            preset_uuid = UUID(self.preset_id)
        except (ValueError, TypeError) as ex:
            raise FilterPresetNotFoundError("Invalid preset identifier format.") from ex

        entry = KeyValueDAO.get_entry(
            resource=self.resource_name,  # type: ignore[arg-type]
            key=preset_uuid,
        )
        if not entry:
            raise FilterPresetNotFoundError()

        try:
            payload: DashboardFilterPresetPayload = self.codec.decode(entry.value)
        except Exception as ex:
            logger.exception("Failed to decode filter preset payload: %s", ex)
            raise FilterPresetNotFoundError() from ex

        # Verify dashboard association
        if str(payload.get("dashboard_id")) != str(dashboard.id) and str(
            payload.get("dashboard_id")
        ) != str(dashboard.uuid):
            raise FilterPresetNotFoundError()

        # Check visibility
        is_shared = bool(payload.get("is_shared", False))
        current_user_id = get_user_id()
        is_owner = (
            entry.created_by_fk is not None and entry.created_by_fk == current_user_id
        )

        if not is_shared and not is_owner and not security_manager.is_admin():
            raise FilterPresetAccessDeniedError("You do not have permission to view this personal preset.")

        payload["is_owner"] = is_owner
        return payload

    def validate(self) -> None:
        pass
