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
  DataRecordValue,
  QueryFormData,
  QueryFormColumn,
  QueryFormMetric,
  JsonObject,
} from '@superset-ui/core';

export type SortDirection = 'asc' | 'desc';

export interface ColumnSortItem {
  key: string;
  direction: SortDirection;
}

export type FilterOperator =
  | 'contains'
  | 'equals'
  | 'startsWith'
  | 'greaterThan'
  | 'lessThan'
  | 'between';

export interface ColumnFilter {
  key: string;
  operator: FilterOperator;
  value: string;
  secondaryValue?: string;
}

export type ColumnPinType = 'left' | 'right' | 'none';

export interface SavedTableLayout {
  version: number;
  columnOrder: string[];
  columnWidths: Record<string, number>;
  columnPinning: Record<string, ColumnPinType>;
  hiddenColumns?: string[];
  pageSize?: number;
  sortConfig?: ColumnSortItem[];
}

export interface ConditionalFormattingRule {
  column: string;
  operator: FilterOperator;
  targetValue: number | string;
  secondaryValue?: number | string;
  color?: string;
  backgroundColor?: string;
}

// ============================================================================
// TABLE CALCULATIONS TYPES (TABLEAU PARITY)
// ============================================================================

export type TableCalculationType =
  | 'none'
  | 'percent_of_total'
  | 'rank'
  | 'running_total'
  | 'difference_from'
  | 'percent_difference_from'
  | 'moving_average'
  | 'percentile';

export type PercentOfTotalBasis = 'column' | 'row' | 'grand_total';
export type RankMode = 'standard' | 'dense';
export type RankDirection = 'asc' | 'desc';
export type DifferenceFromBasis = 'previous' | 'first';

export interface TableCalculationConfig {
  column: string;
  type: TableCalculationType;
  basis?: PercentOfTotalBasis | DifferenceFromBasis;
  rankMode?: RankMode;
  rankDirection?: RankDirection;
  windowSize?: number;
  outputColumnName?: string;
}

// ============================================================================
// HIGHLIGHT TABLE / HEAT MAP TYPES
// ============================================================================

export type HeatMapColorMode = 'none' | 'sequential' | 'diverging';
export type HeatMapScope = 'per_column' | 'per_table';

export interface HeatMapConfig {
  colorMode: HeatMapColorMode;
  palette?: string;
  scope: HeatMapScope;
  midpoint?: number;
}

export interface EnterpriseTableFormData extends QueryFormData {
  groupby?: QueryFormColumn[];
  metrics?: QueryFormMetric[];
  row_limit?: number;
  include_search?: boolean;
  page_size?: number;
  enable_column_sort?: boolean;
  enable_column_resize?: boolean;
  enable_column_reorder?: boolean;
  enable_column_filters?: boolean;
  enable_column_pinning?: boolean;
  enable_saved_layouts?: boolean;
  enable_cell_bars?: boolean;
  enable_value_coloring?: boolean;
  enable_hyperlinks?: boolean;
  enable_export_excel?: boolean;
  enable_virtualization?: boolean;
  virtual_row_height?: number;
  layout_storage_key?: string;
  table_timestamp_format?: string;
  table_calculations?: TableCalculationConfig[];
  heatmap_color_mode?: HeatMapColorMode;
  heatmap_palette?: string;
  heatmap_scope?: HeatMapScope;
  heatmap_midpoint?: number;
}

export interface EnterpriseTableColumn {
  key: string;
  label: string;
  isMetric?: boolean;
  dataType?: 'string' | 'number' | 'boolean' | 'date';
  formatter?: (value: DataRecordValue) => string;
  minValue?: number;
  maxValue?: number;
  isCalculated?: boolean;
  calculationType?: TableCalculationType;
  sourceColumn?: string;
}

export interface EnterpriseTableTransformedProps {
  data: DataRecord[];
  columns: EnterpriseTableColumn[];
  width: number;
  height: number;
  isLoading?: boolean;
  errorMessage?: string;
  pageSize: number;
  includeSearch: boolean;
  enableColumnSort: boolean;
  enableColumnResize: boolean;
  enableColumnReorder: boolean;
  enableColumnFilters: boolean;
  enableColumnPinning: boolean;
  enableSavedLayouts: boolean;
  enableCellBars: boolean;
  enableValueColoring: boolean;
  enableHyperlinks: boolean;
  enableExportExcel: boolean;
  enableVirtualization: boolean;
  virtualRowHeight: number;
  layoutStorageKey: string;
  rawFormData: JsonObject;
  tableCalculations?: TableCalculationConfig[];
  heatMapConfig?: HeatMapConfig;
}

export type EnterpriseTableProps = ChartProps & {
  formData: EnterpriseTableFormData;
};
