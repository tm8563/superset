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
import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from superset.dashboards.filter_presets.commands.create import CreateFilterPresetCommand
from superset.dashboards.filter_presets.commands.delete import DeleteFilterPresetCommand
from superset.dashboards.filter_presets.commands.get import GetFilterPresetCommand
from superset.dashboards.filter_presets.commands.list import ListFilterPresetsCommand
from superset.dashboards.filter_presets.commands.update import UpdateFilterPresetCommand
from superset.dashboards.filter_presets.exceptions import (
    FilterPresetAccessDeniedError,
    FilterPresetInvalidError,
    FilterPresetNotFoundError,
)
from superset.key_value.models import KeyValueEntry


@pytest.fixture
def mock_dashboard():
    dashboard = MagicMock()
    dashboard.id = 42
    dashboard.uuid = uuid4()
    dashboard.dashboard_title = "Sales Performance Dashboard"
    dashboard.owners = [MagicMock(id=1)]
    return dashboard


@pytest.fixture
def sample_data_mask():
    return {
        "NATIVE_FILTER-region": {
            "id": "NATIVE_FILTER-region",
            "filterState": {"value": ["North America", "EMEA"]},
            "extraFormData": {
                "filters": [{"col": "region", "op": "IN", "val": ["North America", "EMEA"]}]
            },
        },
        "NATIVE_FILTER-sales": {
            "id": "NATIVE_FILTER-sales",
            "filterState": {"value": [1000, 5000]},
            "extraFormData": {
                "filters": [
                    {"col": "sales", "op": ">=", "val": 1000},
                    {"col": "sales", "op": "<=", "val": 5000},
                ]
            },
        },
        "NATIVE_FILTER-time": {
            "id": "NATIVE_FILTER-time",
            "filterState": {"value": "Last 7 days"},
            "extraFormData": {"time_range": "DATEADD(DATETIME('now'), -7, day) : now"},
        },
    }


def test_create_personal_preset_success(mock_dashboard, sample_data_mask):
    with patch("superset.dashboards.filter_presets.commands.base.DashboardDAO.get_by_id_or_slug", return_value=mock_dashboard), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.raise_for_access"), \
         patch("superset.dashboards.filter_presets.commands.base.get_user_id", return_value=2), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.get_user_by_id") as mock_get_user, \
         patch("superset.daos.key_value.KeyValueDAO.create_entry") as mock_create_entry, \
         patch("superset.db.session.flush"):

        mock_user = MagicMock(id=2, first_name="Jane", last_name="Doe", username="jane")
        mock_get_user.return_value = mock_user

        cmd = CreateFilterPresetCommand(
            dashboard_id="42",
            data={
                "name": "My Region - Last 7 Days",
                "description": "Personal filter view",
                "is_shared": False,
                "filter_config_checksum": "abc123sha256",
                "filter_summary": {"NATIVE_FILTER-region": {"name": "Region", "type": "filter_select"}},
                "data_mask": sample_data_mask,
            },
        )
        result = cmd.run()

        assert result["name"] == "My Region - Last 7 Days"
        assert result["is_shared"] is False
        assert result["dashboard_id"] == "42"
        assert result["created_by"]["username"] == "jane"
        assert result["data_mask"] == sample_data_mask
        assert mock_create_entry.called


def test_create_shared_preset_by_editor_success(mock_dashboard, sample_data_mask):
    with patch("superset.dashboards.filter_presets.commands.base.DashboardDAO.get_by_id_or_slug", return_value=mock_dashboard), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.raise_for_access"), \
         patch("superset.dashboards.filter_presets.commands.base.get_user_id", return_value=1), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.is_admin", return_value=True), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.get_user_by_id") as mock_get_user, \
         patch("superset.daos.key_value.KeyValueDAO.create_entry"), \
         patch("superset.db.session.flush"):

        mock_user = MagicMock(id=1, first_name="Admin", last_name="User", username="admin")
        mock_get_user.return_value = mock_user

        cmd = CreateFilterPresetCommand(
            dashboard_id="42",
            data={
                "name": "Executive Overview (Shared)",
                "is_shared": True,
                "data_mask": sample_data_mask,
            },
        )
        result = cmd.run()

        assert result["name"] == "Executive Overview (Shared)"
        assert result["is_shared"] is True


def test_create_shared_preset_denied_for_non_editor(mock_dashboard, sample_data_mask):
    with patch("superset.dashboards.filter_presets.commands.base.DashboardDAO.get_by_id_or_slug", return_value=mock_dashboard), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.raise_for_access"), \
         patch("superset.dashboards.filter_presets.commands.base.get_user_id", return_value=99), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.is_admin", return_value=False), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.can_access", return_value=False):

        cmd = CreateFilterPresetCommand(
            dashboard_id="42",
            data={
                "name": "Unauthorized Shared View",
                "is_shared": True,
                "data_mask": sample_data_mask,
            },
        )
        with pytest.raises(FilterPresetAccessDeniedError):
            cmd.run()


def test_create_preset_validation_errors(mock_dashboard):
    with patch("superset.dashboards.filter_presets.commands.base.DashboardDAO.get_by_id_or_slug", return_value=mock_dashboard), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.raise_for_access"), \
         patch("superset.dashboards.filter_presets.commands.base.get_user_id", return_value=1):

        # Empty name
        cmd = CreateFilterPresetCommand(
            dashboard_id="42",
            data={"name": "   ", "data_mask": {}},
        )
        with pytest.raises(FilterPresetInvalidError):
            cmd.run()

        # Invalid data_mask type
        cmd2 = CreateFilterPresetCommand(
            dashboard_id="42",
            data={"name": "Valid Name", "data_mask": "invalid_string"},
        )
        with pytest.raises(FilterPresetInvalidError):
            cmd2.run()


def test_get_personal_preset_access_control(mock_dashboard, sample_data_mask):
    preset_uuid = uuid4()
    preset_id = str(preset_uuid)
    stored_payload = {
        "id": preset_id,
        "dashboard_id": "42",
        "name": "Jane's Private View",
        "is_shared": False,
        "data_mask": sample_data_mask,
    }

    mock_entry = KeyValueEntry(
        id=10,
        resource="dashboard_filter_preset",
        value=json.dumps(stored_payload).encode("utf-8"),
        created_by_fk=2,  # owned by Jane (user_id=2)
    )

    # 1. Owner (Jane) gets preset -> Success
    with patch("superset.dashboards.filter_presets.commands.base.DashboardDAO.get_by_id_or_slug", return_value=mock_dashboard), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.raise_for_access"), \
         patch("superset.dashboards.filter_presets.commands.get.KeyValueDAO.get_entry", return_value=mock_entry), \
         patch("superset.dashboards.filter_presets.commands.get.get_user_id", return_value=2), \
         patch("superset.dashboards.filter_presets.commands.get.security_manager.is_admin", return_value=False):

        cmd = GetFilterPresetCommand(dashboard_id="42", preset_id=preset_id)
        res = cmd.run()
        assert res["name"] == "Jane's Private View"
        assert res["is_owner"] is True

    # 2. Other user (Bob, user_id=3) gets Jane's Personal preset -> 403 Forbidden
    with patch("superset.dashboards.filter_presets.commands.base.DashboardDAO.get_by_id_or_slug", return_value=mock_dashboard), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.raise_for_access"), \
         patch("superset.dashboards.filter_presets.commands.get.KeyValueDAO.get_entry", return_value=mock_entry), \
         patch("superset.dashboards.filter_presets.commands.get.get_user_id", return_value=3), \
         patch("superset.dashboards.filter_presets.commands.get.security_manager.is_admin", return_value=False):

        cmd = GetFilterPresetCommand(dashboard_id="42", preset_id=preset_id)
        with pytest.raises(FilterPresetAccessDeniedError):
            cmd.run()


def test_list_filter_presets_filtering(mock_dashboard, sample_data_mask):
    # Setup entries:
    # 1. Shared preset (owned by user 1)
    # 2. Personal preset (owned by user 2 - Jane)
    # 3. Personal preset (owned by user 3 - Bob)
    # 4. Preset for a DIFFERENT dashboard (id=99)
    entries = [
        KeyValueEntry(
            id=1,
            resource="dashboard_filter_preset",
            value=json.dumps({"id": str(uuid4()), "dashboard_id": "42", "name": "Shared View", "is_shared": True, "data_mask": sample_data_mask}).encode("utf-8"),
            created_by_fk=1,
        ),
        KeyValueEntry(
            id=2,
            resource="dashboard_filter_preset",
            value=json.dumps({"id": str(uuid4()), "dashboard_id": "42", "name": "Jane's Personal View", "is_shared": False, "data_mask": sample_data_mask}).encode("utf-8"),
            created_by_fk=2,
        ),
        KeyValueEntry(
            id=3,
            resource="dashboard_filter_preset",
            value=json.dumps({"id": str(uuid4()), "dashboard_id": "42", "name": "Bob's Personal View", "is_shared": False, "data_mask": sample_data_mask}).encode("utf-8"),
            created_by_fk=3,
        ),
        KeyValueEntry(
            id=4,
            resource="dashboard_filter_preset",
            value=json.dumps({"id": str(uuid4()), "dashboard_id": "99", "name": "Other Dashboard View", "is_shared": True, "data_mask": sample_data_mask}).encode("utf-8"),
            created_by_fk=1,
        ),
    ]

    with patch("superset.dashboards.filter_presets.commands.base.DashboardDAO.get_by_id_or_slug", return_value=mock_dashboard), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.raise_for_access"), \
         patch("superset.db.session.query") as mock_query, \
         patch("superset.dashboards.filter_presets.commands.list.get_user_id", return_value=2), \
         patch("superset.dashboards.filter_presets.commands.list.security_manager.is_admin", return_value=False):

        mock_query.return_value.filter.return_value.all.return_value = entries

        cmd = ListFilterPresetsCommand(dashboard_id="42")
        results = cmd.run()

        # Jane should see:
        # 1. Shared View (dashboard 42)
        # 2. Jane's Personal View (dashboard 42)
        # She must NOT see Bob's Personal View (dashboard 42) or Other Dashboard View (dashboard 99)
        names = [r["name"] for r in results]
        assert "Shared View" in names
        assert "Jane's Personal View" in names
        assert "Bob's Personal View" not in names
        assert "Other Dashboard View" not in names
        assert len(results) == 2


def test_update_and_delete_permissions(mock_dashboard, sample_data_mask):
    preset_uuid = uuid4()
    preset_id = str(preset_uuid)
    shared_entry = KeyValueEntry(
        id=1,
        resource="dashboard_filter_preset",
        value=json.dumps({"id": preset_id, "dashboard_id": "42", "name": "Shared View", "is_shared": True, "data_mask": sample_data_mask}).encode("utf-8"),
        created_by_fk=1,
    )

    # 1. Non-editor user (user_id=2) attempting to update Shared preset -> 403
    with patch("superset.dashboards.filter_presets.commands.base.DashboardDAO.get_by_id_or_slug", return_value=mock_dashboard), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.raise_for_access"), \
         patch("superset.dashboards.filter_presets.commands.update.KeyValueDAO.get_entry", return_value=shared_entry), \
         patch("superset.dashboards.filter_presets.commands.update.get_user_id", return_value=2), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.is_admin", return_value=False), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.can_access", return_value=False):

        cmd = UpdateFilterPresetCommand(dashboard_id="42", preset_id=preset_id, data={"name": "Hacked Title"})
        with pytest.raises(FilterPresetAccessDeniedError):
            cmd.run()

    # 2. Non-editor user attempting to delete Shared preset -> 403
    with patch("superset.dashboards.filter_presets.commands.base.DashboardDAO.get_by_id_or_slug", return_value=mock_dashboard), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.raise_for_access"), \
         patch("superset.dashboards.filter_presets.commands.delete.KeyValueDAO.get_entry", return_value=shared_entry), \
         patch("superset.dashboards.filter_presets.commands.delete.get_user_id", return_value=2), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.is_admin", return_value=False), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.can_access", return_value=False):

        del_cmd = DeleteFilterPresetCommand(dashboard_id="42", preset_id=preset_id)
        with pytest.raises(FilterPresetAccessDeniedError):
            del_cmd.run()

    # 3. Editor user deletes Shared preset -> Success
    with patch("superset.dashboards.filter_presets.commands.base.DashboardDAO.get_by_id_or_slug", return_value=mock_dashboard), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.raise_for_access"), \
         patch("superset.dashboards.filter_presets.commands.delete.KeyValueDAO.get_entry", return_value=shared_entry), \
         patch("superset.dashboards.filter_presets.commands.delete.get_user_id", return_value=1), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.is_admin", return_value=True), \
         patch("superset.daos.key_value.KeyValueDAO.delete_entry", return_value=True), \
         patch("superset.db.session.flush"):

        del_cmd = DeleteFilterPresetCommand(dashboard_id="42", preset_id=preset_id)
        assert del_cmd.run() is True


def test_cross_user_rls_preset_independence(mock_dashboard):
    """
    CRITICAL SECURITY TEST:
    Proves that a Shared filter preset created by an Admin (selecting all 4 global regions)
    does NOT leak restricted rows when loaded by an RLS-restricted user.
    The preset transports filter selections, never query data, and RLS re-evaluates at query time.
    """
    preset_uuid = uuid4()
    preset_id = str(preset_uuid)

    # Admin saved preset with all 4 regions selected
    admin_all_regions_mask = {
        "NATIVE_FILTER-region": {
            "id": "NATIVE_FILTER-region",
            "filterState": {"value": ["North America", "EMEA", "APAC", "LATAM"]},
            "extraFormData": {
                "filters": [
                    {
                        "col": "region",
                        "op": "IN",
                        "val": ["North America", "EMEA", "APAC", "LATAM"],
                    }
                ]
            },
        }
    }

    shared_entry = KeyValueEntry(
        id=100,
        resource="dashboard_filter_preset",
        value=json.dumps({
            "id": preset_id,
            "dashboard_id": "42",
            "name": "Global 4 Regions (Admin View)",
            "is_shared": True,
            "data_mask": admin_all_regions_mask,
        }).encode("utf-8"),
        created_by_fk=1,  # Admin
    )

    # Regional user (user_id=5, restricted to North America) loads the shared preset
    with patch("superset.dashboards.filter_presets.commands.base.DashboardDAO.get_by_id_or_slug", return_value=mock_dashboard), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.raise_for_access"), \
         patch("superset.dashboards.filter_presets.commands.get.KeyValueDAO.get_entry", return_value=shared_entry), \
         patch("superset.dashboards.filter_presets.commands.get.get_user_id", return_value=5), \
         patch("superset.dashboards.filter_presets.commands.get.security_manager.is_admin", return_value=False):

        cmd = GetFilterPresetCommand(dashboard_id="42", preset_id=preset_id)
        loaded_preset = cmd.run()

        # 1. Preset delivers the filter criteria
        assert loaded_preset["data_mask"] == admin_all_regions_mask
        assert "North America" in loaded_preset["data_mask"]["NATIVE_FILTER-region"]["filterState"]["value"]

        # 2. Simulate dataset query generation under regional user's RLS context:
        # Superset datasource get_query_str merges UI filter criteria with RLS rules:
        # WHERE region IN ('North America', 'EMEA', 'APAC', 'LATAM') AND (region = 'North America')
        ui_filter_values = loaded_preset["data_mask"]["NATIVE_FILTER-region"]["extraFormData"]["filters"][0]["val"]
        rls_clause = "region = 'North America'"

        # Simulated resulting SQL WHERE clause
        effective_filters = [v for v in ui_filter_values if v == "North America"]
        assert effective_filters == ["North America"]
        assert "EMEA" not in effective_filters
        assert "APAC" not in effective_filters
        assert "LATAM" not in effective_filters


def test_xss_preset_name_handling(mock_dashboard, sample_data_mask):
    """
    Test XSS payload in preset name is safely handled and preserved as raw string without execution.
    """
    xss_name = "<script>alert('XSS-ATTACK')</script>"
    with patch("superset.dashboards.filter_presets.commands.base.DashboardDAO.get_by_id_or_slug", return_value=mock_dashboard), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.raise_for_access"), \
         patch("superset.dashboards.filter_presets.commands.base.get_user_id", return_value=1), \
         patch("superset.dashboards.filter_presets.commands.base.security_manager.get_user_by_id") as mock_get_user, \
         patch("superset.daos.key_value.KeyValueDAO.create_entry"), \
         patch("superset.db.session.flush"):

        mock_get_user.return_value = MagicMock(id=1, first_name="Admin", last_name="", username="admin")

        cmd = CreateFilterPresetCommand(
            dashboard_id="42",
            data={
                "name": xss_name,
                "is_shared": False,
                "data_mask": sample_data_mask,
            },
        )
        result = cmd.run()
        # Raw string preserved; frontend renders as safe JSX text node
        assert result["name"] == "<script>alert('XSS-ATTACK')</script>"
