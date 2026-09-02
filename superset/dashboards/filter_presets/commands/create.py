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
from datetime import datetime
import logging
from typing import Any
from uuid import uuid4

from superset import db
from superset.daos.key_value import KeyValueDAO
from superset.dashboards.filter_presets.commands.base import BaseFilterPresetCommand
from superset.dashboards.filter_presets.exceptions import (
    FilterPresetAccessDeniedError,
    FilterPresetCreateFailedError,
    FilterPresetInvalidError,
)
from superset.dashboards.filter_presets.types import DashboardFilterPresetPayload
from superset.utils.decorators import transaction

logger = logging.getLogger(__name__)


class CreateFilterPresetCommand(BaseFilterPresetCommand):
    def __init__(self, dashboard_id: str, data: dict[str, Any]):
        self.dashboard_id = dashboard_id
        self.data = data

    @transaction()
    def run(self) -> DashboardFilterPresetPayload:
        dashboard = self.get_dashboard(self.dashboard_id)
        name = (self.data.get("name") or "").strip()
        if not name:
            raise FilterPresetInvalidError("Preset name cannot be empty.")

        is_shared = bool(self.data.get("is_shared", False))
        if is_shared and not self.can_edit_dashboard(dashboard):
            raise FilterPresetAccessDeniedError(
                "You need dashboard edit permission to create a Shared preset."
            )

        data_mask = self.data.get("data_mask")
        if not isinstance(data_mask, dict):
            raise FilterPresetInvalidError("Invalid data_mask state provided.")

        preset_uuid = uuid4()
        preset_id = str(preset_uuid)
        user_summary = self.get_user_summary()
        now_iso = datetime.now().isoformat()
        description = self.data.get("description")
        description_clean = description.strip() if isinstance(description, str) else None

        payload: DashboardFilterPresetPayload = {
            "id": preset_id,
            "dashboard_id": str(dashboard.id),
            "name": name,
            "description": description_clean,
            "is_shared": is_shared,
            "filter_config_checksum": self.data.get("filter_config_checksum"),
            "filter_summary": self.data.get("filter_summary") or {},
            "data_mask": data_mask,
            "created_by": user_summary,
            "created_on": now_iso,
            "changed_on": now_iso,
            "is_owner": True,
        }

        try:
            KeyValueDAO.create_entry(
                resource=self.resource_name,  # type: ignore[arg-type]
                key=preset_uuid,
                value=payload,
                codec=self.codec,
            )
            db.session.flush()
            return payload
        except Exception as ex:
            logger.exception("Failed to create filter preset entry: %s", ex)
            raise FilterPresetCreateFailedError(str(ex)) from ex

    def validate(self) -> None:
        pass
