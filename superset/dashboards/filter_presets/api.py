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

from flask import request, Response
from flask_appbuilder.api import expose, protect, safe
from marshmallow import ValidationError

from superset.commands.dashboard.exceptions import (
    DashboardAccessDeniedError,
    DashboardNotFoundError,
)
from superset.constants import MODEL_API_RW_METHOD_PERMISSION_MAP
from superset.dashboards.filter_presets.commands.create import CreateFilterPresetCommand
from superset.dashboards.filter_presets.commands.delete import DeleteFilterPresetCommand
from superset.dashboards.filter_presets.commands.get import GetFilterPresetCommand
from superset.dashboards.filter_presets.commands.list import ListFilterPresetsCommand
from superset.dashboards.filter_presets.commands.update import UpdateFilterPresetCommand
from superset.dashboards.filter_presets.exceptions import (
    FilterPresetAccessDeniedError,
    FilterPresetCreateFailedError,
    FilterPresetDeleteFailedError,
    FilterPresetInvalidError,
    FilterPresetNotFoundError,
    FilterPresetUpdateFailedError,
)
from superset.dashboards.filter_presets.schemas import (
    DashboardFilterPresetPostSchema,
    DashboardFilterPresetPutSchema,
    DashboardFilterPresetResponseSchema,
)
from superset.extensions import event_logger
from superset.views.base_api import BaseSupersetApi, requires_json

logger = logging.getLogger(__name__)


class DashboardFilterPresetRestApi(BaseSupersetApi):
    post_schema = DashboardFilterPresetPostSchema()
    put_schema = DashboardFilterPresetPutSchema()
    response_schema = DashboardFilterPresetResponseSchema()
    method_permission_name = MODEL_API_RW_METHOD_PERMISSION_MAP
    allow_browser_login = True
    class_permission_name = "DashboardFilterPresetRestApi"
    resource_name = "dashboard"
    openapi_spec_tag = "Dashboard Filter Presets"
    openapi_spec_component_schemas = (
        DashboardFilterPresetPostSchema,
        DashboardFilterPresetPutSchema,
        DashboardFilterPresetResponseSchema,
    )

    @expose("/<pk>/filter_preset", methods=("POST",))
    @protect()
    @safe
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.post",
        log_to_statsd=False,
    )
    @requires_json
    def post(self, pk: str) -> Response:
        """Create a new dashboard filter preset.
        ---
        post:
          summary: Create a new dashboard filter preset
          parameters:
          - in: path
            schema:
              type: string
            name: pk
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/DashboardFilterPresetPostSchema'
          responses:
            201:
              description: Filter preset created successfully
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      result:
                        $ref: '#/components/schemas/DashboardFilterPresetResponseSchema'
            400:
              $ref: '#/components/responses/400'
            403:
              $ref: '#/components/responses/403'
            404:
              $ref: '#/components/responses/404'
            500:
              $ref: '#/components/responses/500'
        """
        try:
            data = self.post_schema.load(request.json)
            preset = CreateFilterPresetCommand(dashboard_id=pk, data=data).run()
            return self.response(201, result=preset)
        except ValidationError as ex:
            return self.response(400, message=ex.messages)
        except FilterPresetInvalidError as ex:
            return self.response(400, message=str(ex))
        except (DashboardAccessDeniedError, FilterPresetAccessDeniedError) as ex:
            return self.response(403, message=str(ex))
        except DashboardNotFoundError as ex:
            return self.response(404, message=str(ex))
        except FilterPresetCreateFailedError as ex:
            return self.response(500, message=str(ex))

    @expose("/<pk>/filter_preset", methods=("GET",))
    @protect()
    @safe
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.get_list",
        log_to_statsd=False,
    )
    def get_list(self, pk: str) -> Response:
        """List all filter presets for a dashboard visible to the current user.
        ---
        get:
          summary: List filter presets for a dashboard
          parameters:
          - in: path
            schema:
              type: string
            name: pk
          responses:
            200:
              description: List of filter presets
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      result:
                        type: array
                        items:
                          $ref: '#/components/schemas/DashboardFilterPresetResponseSchema'
                      count:
                        type: integer
            403:
              $ref: '#/components/responses/403'
            404:
              $ref: '#/components/responses/404'
            500:
              $ref: '#/components/responses/500'
        """
        try:
            presets = ListFilterPresetsCommand(dashboard_id=pk).run()
            return self.response(200, result=presets, count=len(presets))
        except DashboardAccessDeniedError as ex:
            return self.response(403, message=str(ex))
        except DashboardNotFoundError as ex:
            return self.response(404, message=str(ex))

    @expose("/<pk>/filter_preset/<string:preset_id>", methods=("GET",))
    @protect()
    @safe
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.get",
        log_to_statsd=False,
    )
    def get(self, pk: str, preset_id: str) -> Response:
        """Get a single filter preset by ID.
        ---
        get:
          summary: Get a filter preset by ID
          parameters:
          - in: path
            schema:
              type: string
            name: pk
          - in: path
            schema:
              type: string
            name: preset_id
          responses:
            200:
              description: The filter preset
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      result:
                        $ref: '#/components/schemas/DashboardFilterPresetResponseSchema'
            403:
              $ref: '#/components/responses/403'
            404:
              $ref: '#/components/responses/404'
            500:
              $ref: '#/components/responses/500'
        """
        try:
            preset = GetFilterPresetCommand(dashboard_id=pk, preset_id=preset_id).run()
            return self.response(200, result=preset)
        except (DashboardAccessDeniedError, FilterPresetAccessDeniedError) as ex:
            return self.response(403, message=str(ex))
        except (DashboardNotFoundError, FilterPresetNotFoundError) as ex:
            return self.response(404, message=str(ex))

    @expose("/<pk>/filter_preset/<string:preset_id>", methods=("PUT",))
    @protect()
    @safe
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.put",
        log_to_statsd=False,
    )
    @requires_json
    def put(self, pk: str, preset_id: str) -> Response:
        """Update a filter preset.
        ---
        put:
          summary: Update a filter preset
          parameters:
          - in: path
            schema:
              type: string
            name: pk
          - in: path
            schema:
              type: string
            name: preset_id
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/DashboardFilterPresetPutSchema'
          responses:
            200:
              description: Filter preset updated
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      result:
                        $ref: '#/components/schemas/DashboardFilterPresetResponseSchema'
            400:
              $ref: '#/components/responses/400'
            403:
              $ref: '#/components/responses/403'
            404:
              $ref: '#/components/responses/404'
            500:
              $ref: '#/components/responses/500'
        """
        try:
            data = self.put_schema.load(request.json)
            preset = UpdateFilterPresetCommand(
                dashboard_id=pk, preset_id=preset_id, data=data
            ).run()
            return self.response(200, result=preset)
        except ValidationError as ex:
            return self.response(400, message=ex.messages)
        except FilterPresetInvalidError as ex:
            return self.response(400, message=str(ex))
        except (DashboardAccessDeniedError, FilterPresetAccessDeniedError) as ex:
            return self.response(403, message=str(ex))
        except (DashboardNotFoundError, FilterPresetNotFoundError) as ex:
            return self.response(404, message=str(ex))
        except FilterPresetUpdateFailedError as ex:
            return self.response(500, message=str(ex))

    @expose("/<pk>/filter_preset/<string:preset_id>", methods=("DELETE",))
    @protect()
    @safe
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.delete",
        log_to_statsd=False,
    )
    def delete(self, pk: str, preset_id: str) -> Response:
        """Delete a filter preset.
        ---
        delete:
          summary: Delete a filter preset
          parameters:
          - in: path
            schema:
              type: string
            name: pk
          - in: path
            schema:
              type: string
            name: preset_id
          responses:
            200:
              description: Filter preset deleted
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
            403:
              $ref: '#/components/responses/403'
            404:
              $ref: '#/components/responses/404'
            500:
              $ref: '#/components/responses/500'
        """
        try:
            DeleteFilterPresetCommand(dashboard_id=pk, preset_id=preset_id).run()
            return self.response(200, message="OK")
        except (DashboardAccessDeniedError, FilterPresetAccessDeniedError) as ex:
            return self.response(403, message=str(ex))
        except (DashboardNotFoundError, FilterPresetNotFoundError) as ex:
            return self.response(404, message=str(ex))
        except FilterPresetDeleteFailedError as ex:
            return self.response(500, message=str(ex))
