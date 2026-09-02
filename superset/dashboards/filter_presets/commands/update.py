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
from uuid import UUID

from superset import db, security_manager
from superset.daos.key_value import KeyValueDAO
from superset.dashboards.filter_presets.commands.base import BaseFilterPresetCommand
from superset.dashboards.filter_presets.exceptions import (
    FilterPresetAccessDeniedError,
    FilterPresetInvalidError,
    FilterPresetNotFoundError,
    FilterPresetUpdateFailedError,
)
from superset.dashboards.filter_presets.types import DashboardFilterPresetPayload
from superset.utils.core import get_user_id
from superset.utils.decorators import transaction

logger = logging.getLogger(__name__)


class UpdateFilterPresetCommand(BaseFilterPresetCommand):
    def __init__(self, dashboard_id: str, preset_id: str, data: dict[str, Any]):
        self.dashboard_id = dashboard_id
        self.preset_id = preset_id
        self.data = data

    @transaction()
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

        if str(payload.get("dashboard_id")) != str(dashboard.id) and str(
            payload.get("dashboard_id")
        ) != str(dashboard.uuid):
            raise FilterPresetNotFoundError()

        current_user_id = get_user_id()
        is_owner = (
            entry.created_by_fk is not None and entry.created_by_fk == current_user_id
        )
        can_edit = self.can_edit_dashboard(dashboard)
        is_admin = security_manager.is_admin()
        was_shared = bool(payload.get("is_shared", False))
        is_shared = bool(self.data.get("is_shared", was_shared))

        # Permission check:
        # If modifying a shared preset or changing scope to shared -> must have dashboard edit permission
        # If modifying personal preset -> owner or editor or admin
        if was_shared or is_shared:
            if not can_edit and not is_admin:
                raise FilterPresetAccessDeniedError(
                    "You need dashboard edit permission to update a Shared preset."
                )
        else:
            if not is_owner and not can_edit and not is_admin:
                raise FilterPresetAccessDeniedError(
                    "You do not have permission to update this personal preset."
                )

        if "name" in self.data:
            name = (self.data["name"] or "").strip()
            if not name:
                raise FilterPresetInvalidError("Preset name cannot be empty.")
            payload["name"] = name

        if "description" in self.data:
            desc = self.data["description"]
            payload["description"] = desc.strip() if isinstance(desc, str) else None

        if "is_shared" in self.data:
            payload["is_shared"] = is_shared

        if "filter_config_checksum" in self.data:
            payload["filter_config_checksum"] = self.data["filter_config_checksum"]

        if "filter_summary" in self.data:
            payload["filter_summary"] = self.data["filter_summary"]

        if "data_mask" in self.data:
            data_mask = self.data["data_mask"]
            if not isinstance(data_mask, dict):
                raise FilterPresetInvalidError("Invalid data_mask state provided.")
            payload["data_mask"] = data_mask

        payload["changed_on"] = datetime.now().isoformat()
        payload["is_owner"] = is_owner

        try:
            KeyValueDAO.update_entry(
                resource=self.resource_name,  # type: ignore[arg-type]
                key=preset_uuid,
                value=payload,
                codec=self.codec,
            )
            db.session.flush()
            return payload
        except Exception as ex:
            logger.exception("Failed to update filter preset entry: %s", ex)
            raise FilterPresetUpdateFailedError(str(ex)) from ex

    def validate(self) -> None:
        pass
