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

// HSC customization tests: the pivot's row highlight merges filters applied
// from elsewhere on the dashboard, while its own click selection stays
// separate (docs/00-runbook.md §5ab and its follow-up).

import { ChartProps, QueryFormData } from '@superset-ui/core';
import { supersetTheme } from '@apache-superset/core/theme';
import transformProps from '../../src/plugin/transformProps';
import { MetricsLayoutEnum } from '../../src/types';

const baseFormData = {
  groupbyRows: ['name'],
  groupbyColumns: [],
  metrics: ['sum__num'],
  tableRenderer: 'Table With Subtotal',
  colOrder: 'key_a_to_z',
  rowOrder: 'key_a_to_z',
  metricsLayout: MetricsLayoutEnum.COLUMNS,
  viz_type: 'pivot_table_v2',
  datasource: '',
  conditionalFormatting: [],
  dateFormat: '',
  legacy_order_by: 'sum__num',
  order_desc: true,
  valueFormat: 'SMART_NUMBER',
};

const buildChartProps = (
  selectedFilters: Record<string, unknown[]> | undefined,
  extraFilters: { col: unknown; op: string; val?: unknown }[] | undefined,
) =>
  new ChartProps<QueryFormData>({
    formData: {
      ...baseFormData,
      ...(extraFilters ? { extra_form_data: { filters: extraFilters } } : {}),
    } as unknown as QueryFormData,
    width: 800,
    height: 600,
    queriesData: [
      {
        data: [
          { name: 'Hulk', sum__num: 1 },
          { name: 'Thor', sum__num: 2 },
        ],
        colnames: ['name', 'sum__num'],
        coltypes: [1, 0],
      },
    ],
    hooks: { setDataMask: jest.fn() },
    filterState: { selectedFilters },
    datasource: { verboseMap: {}, columnFormats: {} },
    theme: supersetTheme,
  });

test('highlightFilters merges dashboard IN/== filters with own selection', () => {
  const result = transformProps(
    buildChartProps({ name: ['Hulk'] }, [
      { col: 'name', op: 'IN', val: ['Thor', 'Hulk'] },
      { col: 'group_name', op: '==', val: 'BPO' },
    ]),
  ) as ReturnType<typeof transformProps>;

  expect(result.highlightFilters).toEqual({
    name: ['Hulk', 'Thor'],
    group_name: ['BPO'],
  });
});

test('selectedFilters stays the chart own selection only', () => {
  const result = transformProps(
    buildChartProps({ name: ['Hulk'] }, [
      { col: 'group_name', op: 'IN', val: ['BPO'] },
    ]),
  ) as ReturnType<typeof transformProps>;

  expect(result.selectedFilters).toEqual({ name: ['Hulk'] });
});

test('highlightFilters skips non-value clauses and adhoc column objects', () => {
  const result = transformProps(
    buildChartProps(undefined, [
      { col: 'month', op: 'IS NULL' },
      { col: 'ts', op: 'TEMPORAL_RANGE', val: '2026-01-01 : 2026-02-01' },
      { col: { label: 'Month', sqlExpression: 'x' }, op: 'IN', val: ['a'] },
      { col: 'name', op: 'IN', val: [] },
    ]),
  ) as ReturnType<typeof transformProps>;

  expect(result.highlightFilters).toEqual({});
});

test('merging never mutates the dashboard filterState arrays', () => {
  const own = { name: ['Hulk'] };
  transformProps(
    buildChartProps(own, [{ col: 'name', op: 'IN', val: ['Thor'] }]),
  );
  expect(own.name).toEqual(['Hulk']);
});
