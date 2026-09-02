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
import {
  ChartCustomization,
  ChartCustomizationDivider,
  DataMaskStateWithId,
  Divider,
  Filter,
} from '@superset-ui/core';
import {
  DashboardFilterPreset,
  FilterDriftDetail,
  FilterSummaryItem,
} from './types';

type AnyFilterItem =
  | Filter
  | Divider
  | ChartCustomization
  | ChartCustomizationDivider;

function getItemType(item: AnyFilterItem): string {
  if ('filterType' in item && typeof item.filterType === 'string') {
    return item.filterType;
  }
  if ('type' in item && typeof item.type === 'string') {
    return item.type;
  }
  return 'divider';
}

function getItemColumn(item: AnyFilterItem): string | null {
  if (
    'targets' in item &&
    Array.isArray(item.targets) &&
    item.targets[0]?.column?.name
  ) {
    return String(item.targets[0].column.name);
  }
  if (
    'controlValues' in item &&
    item.controlValues &&
    'column' in item.controlValues &&
    item.controlValues.column
  ) {
    return String(item.controlValues.column);
  }
  return null;
}

/**
 * Computes a fast, deterministic hex checksum for a string.
 */
export function simpleStringHash(str: string): string {
  let hash1 = 5381;
  let hash2 = 52711;

  for (let i = 0; i < str.length; i += 1) {
    const char = str.charCodeAt(i);
    hash1 = (hash1 * 33) ^ char;
    hash2 = (hash2 * 33) ^ char;
  }

  const hex1 = (hash1 >>> 0).toString(16).padStart(8, '0');
  const hex2 = (hash2 >>> 0).toString(16).padStart(8, '0');
  return `${hex1}${hex2}`;
}

/**
 * Extracts a normalized representation of active dashboard filters for checksum calculation.
 */
export function computeFilterConfigChecksum(
  filters: Record<string, AnyFilterItem>,
): string {
  const sortedKeys = Object.keys(filters).sort();
  const normalizedItems = sortedKeys.map(key => {
    const item = filters[key];
    const filterType = getItemType(item);
    const name = item.name || '';
    const column = getItemColumn(item);
    const targetCount =
      'targets' in item && Array.isArray(item.targets)
        ? item.targets.length
        : 0;

    return {
      id: key,
      name,
      filterType,
      column,
      targetCount,
    };
  });

  return simpleStringHash(JSON.stringify(normalizedItems));
}

/**
 * Generates a human-readable snapshot summary of filters for storage in presets.
 */
export function generateFilterSummary(
  filters: Record<string, AnyFilterItem>,
): Record<string, FilterSummaryItem> {
  const summary: Record<string, FilterSummaryItem> = {};

  Object.entries(filters).forEach(([id, item]) => {
    const type = getItemType(item);
    const column = getItemColumn(item);

    summary[id] = {
      name: item.name || id,
      type,
      column: column || undefined,
    };
  });

  return summary;
}

/**
 * Detects if a preset has drifted from the live dashboard filter configuration.
 */
export function detectFilterDrift(
  preset: DashboardFilterPreset,
  currentFilters: Record<string, AnyFilterItem>,
): FilterDriftDetail {
  const liveChecksum = computeFilterConfigChecksum(currentFilters);
  const storedChecksum = preset.filter_config_checksum;

  if (storedChecksum && liveChecksum === storedChecksum) {
    return {
      hasDrift: false,
      removedFilterIds: [],
      modifiedFilterIds: [],
      addedFilterIds: [],
      compatibleFilterIds: Object.keys(preset.data_mask),
      removedFilterNames: [],
    };
  }

  const presetMask = preset.data_mask || {};
  const presetSummary = preset.filter_summary || {};
  const presetFilterIds = Object.keys(presetMask);
  const currentFilterIds = new Set(Object.keys(currentFilters));

  const removedFilterIds: string[] = [];
  const removedFilterNames: string[] = [];
  const modifiedFilterIds: string[] = [];
  const compatibleFilterIds: string[] = [];

  presetFilterIds.forEach(id => {
    if (!currentFilterIds.has(id)) {
      removedFilterIds.push(id);
      const savedName = presetSummary[id]?.name || id;
      removedFilterNames.push(savedName);
    } else {
      const currentItem = currentFilters[id];
      const savedItem = presetSummary[id];
      const currentType = getItemType(currentItem);
      const currentColumn = getItemColumn(currentItem);

      if (
        savedItem &&
        ((savedItem.type && savedItem.type !== currentType) ||
          (savedItem.column && savedItem.column !== currentColumn))
      ) {
        modifiedFilterIds.push(id);
      } else {
        compatibleFilterIds.push(id);
      }
    }
  });

  const addedFilterIds = Object.keys(currentFilters).filter(
    id => !presetMask[id],
  );

  const hasDrift =
    removedFilterIds.length > 0 ||
    modifiedFilterIds.length > 0 ||
    (storedChecksum !== null &&
      storedChecksum !== undefined &&
      liveChecksum !== storedChecksum);

  return {
    hasDrift,
    removedFilterIds,
    modifiedFilterIds,
    addedFilterIds,
    compatibleFilterIds,
    removedFilterNames,
  };
}

/**
 * Sanitizes a preset's dataMask by stripping out filters that no longer exist in currentFilters.
 */
export function sanitizePresetDataMask(
  presetDataMask: DataMaskStateWithId,
  currentFilters: Record<string, AnyFilterItem>,
): DataMaskStateWithId {
  const sanitized: DataMaskStateWithId = {};
  const currentFilterIds = new Set(Object.keys(currentFilters));

  Object.entries(presetDataMask).forEach(([id, mask]) => {
    if (currentFilterIds.has(id)) {
      sanitized[id] = { ...mask };
    }
  });

  return sanitized;
}
