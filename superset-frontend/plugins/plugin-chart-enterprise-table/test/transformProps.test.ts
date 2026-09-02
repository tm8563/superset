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

import { ChartProps } from '@superset-ui/core';
import { supersetTheme } from '@apache-superset/core/theme';
import { transformProps } from '../src/transformProps';
import { EnterpriseTableFormData } from '../src/types';

test('transforms chart props into component props correctly with snake_case formData and calculates min/max for cell bars', () => {
  const formData: EnterpriseTableFormData = {
    datasource: '28__table',
    viz_type: 'enterprise_table',
    groupby: ['region'],
    metrics: ['sum_sales'],
    page_size: 50,
    include_search: true,
    enable_column_sort: true,
    enable_column_resize: true,
    enable_column_reorder: true,
    enable_column_filters: true,
    enable_column_pinning: true,
    enable_saved_layouts: true,
    enable_cell_bars: true,
    enable_value_coloring: true,
    enable_hyperlinks: true,
    enable_export_excel: true,
    enable_virtualization: false,
    virtual_row_height: 32,
    layout_storage_key: 'custom_table_key',
  };

  const chartProps = new ChartProps({
    theme: supersetTheme,
    formData,
    width: 800,
    height: 600,
    queriesData: [
      {
        colnames: ['region', 'sum_sales'],
        coltypes: [1, 0],
        data: [
          { region: 'North America', sum_sales: 100000 },
          { region: 'EMEA', sum_sales: 250000 },
          { region: 'APAC', sum_sales: 50000 },
        ],
      },
    ],
  });

  const transformed = transformProps(chartProps);
  expect(transformed.width).toBe(800);
  expect(transformed.height).toBe(600);
  expect(transformed.pageSize).toBe(50);
  expect(transformed.includeSearch).toBe(true);
  expect(transformed.enableColumnSort).toBe(true);
  expect(transformed.enableColumnResize).toBe(true);
  expect(transformed.enableColumnReorder).toBe(true);
  expect(transformed.enableColumnFilters).toBe(true);
  expect(transformed.enableColumnPinning).toBe(true);
  expect(transformed.enableSavedLayouts).toBe(true);
  expect(transformed.enableCellBars).toBe(true);
  expect(transformed.enableValueColoring).toBe(true);
  expect(transformed.enableHyperlinks).toBe(true);
  expect(transformed.enableExportExcel).toBe(true);
  expect(transformed.enableVirtualization).toBe(false);
  expect(transformed.virtualRowHeight).toBe(32);
  expect(transformed.layoutStorageKey).toBe('custom_table_key');
  expect(transformed.data).toHaveLength(3);
  expect(transformed.columns).toEqual([
    {
      key: 'region',
      label: 'region',
      isMetric: false,
      dataType: 'string',
      minValue: undefined,
      maxValue: undefined,
    },
    {
      key: 'sum_sales',
      label: 'sum_sales',
      isMetric: true,
      dataType: 'number',
      minValue: 50000,
      maxValue: 250000,
    },
  ]);
});
