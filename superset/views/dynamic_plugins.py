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
from typing import Any, Optional

from flask import g, jsonify, make_response, Response
from flask_appbuilder import ModelView
from flask_appbuilder.baseviews import expose_api
from flask_appbuilder.hooks import before_request
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_babel import lazy_gettext as _

from superset import db, is_feature_enabled
from superset.constants import MODEL_API_RW_METHOD_PERMISSION_MAP
from superset.models.dynamic_plugins import DynamicPlugin


class DynamicPluginsView(ModelView):
    """Dynamic plugin crud views -- To be replaced by fancy react UI"""

    route_base = "/dynamic-plugins"
    datamodel = SQLAInterface(DynamicPlugin)
    class_permission_name = "DynamicPlugin"

    method_permission_name = MODEL_API_RW_METHOD_PERMISSION_MAP

    add_columns = ["name", "key", "bundle_url"]
    edit_columns = add_columns
    show_columns = add_columns + ["id"]
    list_columns = show_columns

    label_columns = {"name": "Name", "key": "Key", "bundle_url": "Bundle URL"}

    description_columns = {
        "name": _("A human-friendly name"),
        "key": _(
            "Used internally to identify the plugin. "
            "Should be set to the package name from the pluginʼs package.json"
        ),
        "bundle_url": _(
            "A full URL pointing to the location "
            "of the built plugin (could be hosted on a CDN for example)"
        ),
    }

    list_title = _("Custom Plugins")
    show_title = _("Custom Plugin")
    add_title = _("Add a Plugin")
    edit_title = _("Edit Plugin")

    @before_request
    def ensure_dynamic_plugins_enabled(self) -> Optional[Response]:
        if not is_feature_enabled("DYNAMIC_PLUGINS"):
            return make_response("Not found", 404)
        return None

    # ------------------------------------------------------------------
    # HSC customization: implement the endpoint the frontend has always
    # expected but that neither this fork nor upstream Superset provided.
    #
    # superset-frontend/src/components/DynamicPlugins/index.tsx does
    #     makeApi<{}, { result: Plugin[] }>({method: 'GET',
    #                                       endpoint: '/dynamic-plugins/api/read'})
    # and reads `result`. That route existed nowhere: FAB only generates
    # `/api/<name>` for methods decorated with `@expose_api`, and this view had
    # none, so `GET /dynamic-plugins/api/read` was a hard 404 while the flag was
    # ON. The provider then never cleared its `loading` state
    # (`loading: isFeatureEnabled(FeatureFlag.DynamicPlugins)`), so charts waited
    # on it forever and every dashboard showed a permanent spinner.
    #
    # Auth note: this endpoint must NEVER answer with an error status. The
    # frontend treats the response as essential plugin metadata and does not
    # clear its `loading` state when the request fails, so ANY non-2xx here
    # (403 included) reproduces the very stall this endpoint was added to fix —
    # including on public/embedded dashboards viewed anonymously. Instead,
    # anonymous callers get a 200 with an empty list: the provider resolves
    # cleanly and no plugin bundle URLs are disclosed. Only authenticated users
    # see the real registry. It still 404s when DYNAMIC_PLUGINS is off, via the
    # before_request hook above (which is safe: with the flag off the frontend
    # never issues this request at all).
    # ------------------------------------------------------------------
    @expose_api(name="read", description="Read all registered dynamic plugins")
    def api_read(self) -> Response:
        user = getattr(g, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return jsonify({"result": [], "count": 0})

        plugins: list[DynamicPlugin] = (
            db.session.query(DynamicPlugin).order_by(DynamicPlugin.id).all()
        )
        result: list[dict[str, Any]] = [
            {
                "id": plugin.id,
                "name": plugin.name,
                "key": plugin.key,
                "bundle_url": plugin.bundle_url,
            }
            for plugin in plugins
        ]
        return jsonify({"result": result, "count": len(result)})
