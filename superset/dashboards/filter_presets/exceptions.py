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
from superset.exceptions import SupersetErrorException, SupersetException


class FilterPresetError(SupersetException):
    """Base exception for filter preset errors."""


class FilterPresetNotFoundError(FilterPresetError):
    """Raised when a filter preset cannot be found."""
    status = 404
    message = "Filter preset not found."


class FilterPresetAccessDeniedError(FilterPresetError):
    """Raised when access to a filter preset is denied."""
    status = 403
    message = "Access denied for filter preset."


class FilterPresetInvalidError(FilterPresetError):
    """Raised when filter preset data is invalid."""
    status = 400
    message = "Invalid filter preset payload."


class FilterPresetCreateFailedError(FilterPresetError):
    """Raised when creating a filter preset fails."""
    status = 500
    message = "Failed to create filter preset."


class FilterPresetUpdateFailedError(FilterPresetError):
    """Raised when updating a filter preset fails."""
    status = 500
    message = "Failed to update filter preset."


class FilterPresetDeleteFailedError(FilterPresetError):
    """Raised when deleting a filter preset fails."""
    status = 500
    message = "Failed to delete filter preset."
