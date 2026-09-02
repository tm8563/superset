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
from enum import Enum
from typing import Any, Optional, TypedDict


class FilterPresetResource(str, Enum):
    DASHBOARD_FILTER_PRESET = "dashboard_filter_preset"


DASHBOARD_FILTER_PRESET_RESOURCE = FilterPresetResource.DASHBOARD_FILTER_PRESET


class UserSummary(TypedDict, total=False):
    id: int
    first_name: str
    last_name: str
    username: str


class DashboardFilterPresetPayload(TypedDict, total=False):
    id: str
    dashboard_id: str
    name: str
    description: Optional[str]
    is_shared: bool
    filter_config_checksum: Optional[str]
    filter_summary: Optional[dict[str, Any]]
    data_mask: dict[str, Any]
    created_by: Optional[UserSummary]
    created_on: Optional[str]
    changed_on: Optional[str]
    is_owner: Optional[bool]
