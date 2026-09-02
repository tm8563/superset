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
  ChartProps,
  DataRecord,
  getColumnLabel,
  getMetricLabel,
} from '@superset-ui/core';
import {
  EnterpriseTableColumn,
  EnterpriseTableFormData,
  EnterpriseTableTransformedProps,
  HeatMapConfig,
} from './types';

export function transformProps(chartProps: ChartProps): EnterpriseTableTransformedProps {
  const { width, height, formData, rawFormData, queriesData } = chartProps;
  const typedFormData = (rawFormData ?? formData) as EnterpriseTableFormData;

  const data: DataRecord[] = (queriesData[0]?.data as DataRecord[]) ?? [];
  const colnames: string[] = queriesData[0]?.colnames ?? [];

  const metricLabels = new Set(
    (typedFormData.metrics ?? []).map(m => getMetricLabel(m)),
  );

  const columns: EnterpriseTableColumn[] = colnames.map(colName => {
    const isMetric = metricLabels.has(colName);
    let isNumeric = isMetric;
    let minVal: number | undefined;
    let maxVal: number | undefined;

    // Determine type and calculate min/max for cell bars
    for (let i = 0; i < data.length; i += 1) {
      const val = data[i][colName];
      if (val !== null && val !== undefined) {
        if (typeof val === 'number') {
          isNumeric = true;
          if (minVal === undefined || val < minVal) minVal = val;
          if (maxVal === undefined || val > maxVal) maxVal = val;
        }
      }
    }

    return {
      key: colName,
      label: getColumnLabel(colName),
      isMetric,
      dataType: isNumeric ? 'number' : 'string',
      minValue: minVal,
      maxValue: maxVal,
    };
  });

  const chartId = (chartProps as unknown as { sliceId?: number })?.sliceId ?? 0;
  const layoutStorageKey =
    typedFormData.layout_storage_key || `superset_enterprise_table_layout_${chartId}`;

  const heatMapConfig: HeatMapConfig = {
    colorMode: typedFormData.heatmap_color_mode || 'none',
    palette: typedFormData.heatmap_palette,
    scope: typedFormData.heatmap_scope || 'per_column',
    midpoint: typedFormData.heatmap_midpoint ?? 0,
  };

  return {
    data,
    columns,
    width,
    height,
    pageSize: typedFormData.page_size ?? 20,
    includeSearch: typedFormData.include_search !== false,
    enableColumnSort: typedFormData.enable_column_sort !== false,
    enableColumnResize: typedFormData.enable_column_resize !== false,
    enableColumnReorder: typedFormData.enable_column_reorder !== false,
    enableColumnFilters: typedFormData.enable_column_filters !== false,
    enableColumnPinning: typedFormData.enable_column_pinning !== false,
    enableSavedLayouts: typedFormData.enable_saved_layouts !== false,
    enableCellBars: typedFormData.enable_cell_bars !== false,
    enableValueColoring: typedFormData.enable_value_coloring !== false,
    enableHyperlinks: typedFormData.enable_hyperlinks !== false,
    enableExportExcel: typedFormData.enable_export_excel !== false,
    enableVirtualization: Boolean(typedFormData.enable_virtualization),
    virtualRowHeight: typedFormData.virtual_row_height || 32,
    layoutStorageKey,
    rawFormData: typedFormData,
    tableCalculations: typedFormData.table_calculations || [],
    heatMapConfig,
  };
}

export default transformProps;
