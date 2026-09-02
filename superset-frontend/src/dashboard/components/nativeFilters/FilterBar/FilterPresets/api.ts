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
import { SupersetClient } from '@superset-ui/core';
import { logging } from '@apache-superset/core/utils';
import {
  CreateFilterPresetPayload,
  DashboardFilterPreset,
  UpdateFilterPresetPayload,
} from './types';

export const fetchFilterPresets = async (
  dashboardId: string | number,
): Promise<DashboardFilterPreset[]> => {
  try {
    const response = await SupersetClient.get({
      endpoint: `/api/v1/dashboard/${dashboardId}/filter_preset`,
    });
    return (response.json?.result as DashboardFilterPreset[]) || [];
  } catch (err) {
    logging.error('Failed to fetch dashboard filter presets:', err);
    throw err;
  }
};

export const createFilterPreset = async (
  dashboardId: string | number,
  payload: CreateFilterPresetPayload,
): Promise<DashboardFilterPreset> => {
  try {
    const response = await SupersetClient.post({
      endpoint: `/api/v1/dashboard/${dashboardId}/filter_preset`,
      jsonPayload: payload,
    });
    return response.json?.result as DashboardFilterPreset;
  } catch (err) {
    logging.error('Failed to create filter preset:', err);
    throw err;
  }
};

export const updateFilterPreset = async (
  dashboardId: string | number,
  presetId: string,
  payload: UpdateFilterPresetPayload,
): Promise<DashboardFilterPreset> => {
  try {
    const response = await SupersetClient.put({
      endpoint: `/api/v1/dashboard/${dashboardId}/filter_preset/${presetId}`,
      jsonPayload: payload,
    });
    return response.json?.result as DashboardFilterPreset;
  } catch (err) {
    logging.error('Failed to update filter preset:', err);
    throw err;
  }
};

export const deleteFilterPreset = async (
  dashboardId: string | number,
  presetId: string,
): Promise<boolean> => {
  try {
    await SupersetClient.delete({
      endpoint: `/api/v1/dashboard/${dashboardId}/filter_preset/${presetId}`,
    });
    return true;
  } catch (err) {
    logging.error('Failed to delete filter preset:', err);
    throw err;
  }
};
