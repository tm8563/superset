/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import { DataMaskStateWithId } from '@superset-ui/core';

export interface UserSummary {
  id: number;
  first_name: string;
  last_name: string;
  username: string;
}

export interface FilterSummaryItem {
  name: string;
  type: string;
  column?: string;
}

export interface DashboardFilterPreset {
  id: string;
  dashboard_id: string;
  name: string;
  description?: string | null;
  is_shared: boolean;
  filter_config_checksum?: string | null;
  filter_summary?: Record<string, FilterSummaryItem>;
  data_mask: DataMaskStateWithId;
  created_by?: UserSummary | null;
  created_on?: string;
  changed_on?: string;
  is_owner?: boolean;
}

export interface CreateFilterPresetPayload {
  name: string;
  description?: string | null;
  is_shared: boolean;
  filter_config_checksum?: string | null;
  filter_summary?: Record<string, FilterSummaryItem>;
  data_mask: DataMaskStateWithId;
}

export interface UpdateFilterPresetPayload {
  name?: string;
  description?: string | null;
  is_shared?: boolean;
  filter_config_checksum?: string | null;
  filter_summary?: Record<string, FilterSummaryItem>;
  data_mask?: DataMaskStateWithId;
}

export interface FilterDriftDetail {
  hasDrift: boolean;
  removedFilterIds: string[];
  modifiedFilterIds: string[];
  addedFilterIds: string[];
  compatibleFilterIds: string[];
  removedFilterNames: string[];
}
