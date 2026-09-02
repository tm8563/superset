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
from marshmallow import fields, Schema, validate


class UserSummarySchema(Schema):
    id = fields.Integer(required=True)
    first_name = fields.String(allow_none=True)
    last_name = fields.String(allow_none=True)
    username = fields.String(allow_none=True)


class DashboardFilterPresetPostSchema(Schema):
    name = fields.String(
        required=True,
        validate=[validate.Length(min=1, max=250)],
        metadata={"description": "Human-readable name for the filter preset"},
    )
    description = fields.String(
        allow_none=True,
        validate=[validate.Length(max=1000)],
        metadata={"description": "Optional description of what this preset filters"},
    )
    is_shared = fields.Boolean(
        load_default=False,
        metadata={"description": "Whether this preset is shared with all dashboard viewers"},
    )
    filter_config_checksum = fields.String(
        allow_none=True,
        validate=[validate.Length(max=128)],
        metadata={"description": "SHA256 checksum of dashboard filter configuration at save time"},
    )
    filter_summary = fields.Dict(
        allow_none=True,
        metadata={"description": "Snapshot summary of filter names and columns"},
    )
    data_mask = fields.Dict(
        required=True,
        metadata={"description": "Serialized dataMask state dictionary"},
    )


class DashboardFilterPresetPutSchema(Schema):
    name = fields.String(
        allow_none=True,
        validate=[validate.Length(min=1, max=250)],
        metadata={"description": "Updated name for the filter preset"},
    )
    description = fields.String(
        allow_none=True,
        validate=[validate.Length(max=1000)],
        metadata={"description": "Updated description"},
    )
    is_shared = fields.Boolean(
        allow_none=True,
        metadata={"description": "Updated sharing scope"},
    )
    filter_config_checksum = fields.String(
        allow_none=True,
        validate=[validate.Length(max=128)],
        metadata={"description": "Updated checksum"},
    )
    filter_summary = fields.Dict(
        allow_none=True,
        metadata={"description": "Updated filter summary"},
    )
    data_mask = fields.Dict(
        allow_none=True,
        metadata={"description": "Updated dataMask state"},
    )


class DashboardFilterPresetResponseSchema(Schema):
    id = fields.String(required=True)
    dashboard_id = fields.String(required=True)
    name = fields.String(required=True)
    description = fields.String(allow_none=True)
    is_shared = fields.Boolean(required=True)
    filter_config_checksum = fields.String(allow_none=True)
    filter_summary = fields.Dict(allow_none=True)
    data_mask = fields.Dict(required=True)
    created_by = fields.Nested(UserSummarySchema, allow_none=True)
    created_on = fields.String(allow_none=True)
    changed_on = fields.String(allow_none=True)
    is_owner = fields.Boolean(allow_none=True)
