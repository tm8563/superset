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

from superset import db, security_manager
from superset.daos.key_value import KeyValueDAO
from superset.dashboards.filter_presets.commands.base import BaseFilterPresetCommand
from superset.dashboards.filter_presets.exceptions import (
    FilterPresetAccessDeniedError,
    FilterPresetDeleteFailedError,
    FilterPresetNotFoundError,
)
from superset.dashboards.filter_presets.types import DashboardFilterPresetPayload
from superset.utils.core import get_user_id
from superset.utils.decorators import transaction

logger = logging.getLogger(__name__)


class DeleteFilterPresetCommand(BaseFilterPresetCommand):
    def __init__(self, dashboard_id: str, preset_id: str):
        self.dashboard_id = dashboard_id
        self.preset_id = preset_id

    @transaction()
    def run(self) -> bool:
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
        is_shared = bool(payload.get("is_shared", False))

        # Permission rules:
        # Shared preset deletion requires dashboard edit permission or admin
        # Personal preset deletion allowed for owner, dashboard editor, or admin
        if is_shared:
            if not can_edit and not is_admin:
                raise FilterPresetAccessDeniedError(
                    "You need dashboard edit permission to delete a Shared preset."
                )
        else:
            if not is_owner and not can_edit and not is_admin:
                raise FilterPresetAccessDeniedError(
                    "You do not have permission to delete this personal preset."
                )

        try:
            deleted = KeyValueDAO.delete_entry(
                resource=self.resource_name,  # type: ignore[arg-type]
                key=preset_uuid,
            )
            db.session.flush()
            return deleted
        except Exception as ex:
            logger.exception("Failed to delete filter preset entry: %s", ex)
            raise FilterPresetDeleteFailedError(str(ex)) from ex

    def validate(self) -> None:
        pass
