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

import React, {
  useMemo,
  useState,
  useCallback,
  useEffect,
  useRef,
  ChangeEvent,
  MouseEvent as ReactMouseEvent,
  DragEvent as ReactDragEvent,
  UIEvent as ReactUIEvent,
} from 'react';
import { SupersetTheme, styled } from '@apache-superset/core/theme';
import { t } from '@apache-superset/core/translation';
import { DataRecord } from '@superset-ui/core';
import {
  EnterpriseTableTransformedProps,
  ColumnSortItem,
  ColumnFilter,
  FilterOperator,
  ColumnPinType,
  SavedTableLayout,
  EnterpriseTableColumn,
  HeatMapConfig,
} from './types';
import { applyTableCalculations } from './tableCalculations';
import { computeHeatMapColor } from './colorScales';

// ============================================================================
// STYLED COMPONENTS
// ============================================================================

const Container = styled.div<{ width: number; height: number; theme?: SupersetTheme }>`
  width: ${({ width }: { width: number }) => width}px;
  height: ${({ height }: { height: number }) => height}px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: ${({ theme }: { theme: SupersetTheme }) => theme.colorText};
  background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorBgContainer};
  border: 1px solid ${({ theme }: { theme: SupersetTheme }) => theme.colorBorderSecondary};
  border-radius: ${({ theme }: { theme: SupersetTheme }) => theme.borderRadius}px;
  box-sizing: border-box;
`;

const HeaderBar = styled.div<{ theme?: SupersetTheme }>`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorFillAlter};
  border-bottom: 1px solid ${({ theme }: { theme: SupersetTheme }) => theme.colorBorderSecondary};
  gap: 12px;
  flex-shrink: 0;
  flex-wrap: wrap;
`;

const TitleContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
`;

const Title = styled.span`
  font-weight: 600;
  font-size: 13px;
`;

const Badge = styled.span<{ theme?: SupersetTheme }>`
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorPrimaryBg};
  color: ${({ theme }: { theme: SupersetTheme }) => theme.colorPrimary};
  font-weight: 500;
`;

const ControlsGroup = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
`;

const SearchInput = styled.input<{ theme?: SupersetTheme }>`
  padding: 4px 8px;
  border: 1px solid ${({ theme }: { theme: SupersetTheme }) => theme.colorBorder};
  border-radius: 4px;
  font-size: 12px;
  outline: none;
  width: 170px;
  background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorBgContainer};
  color: ${({ theme }: { theme: SupersetTheme }) => theme.colorText};
  &:focus {
    border-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorPrimary};
  }
`;

const ActionButton = styled.button<{ active?: boolean; theme?: SupersetTheme }>`
  padding: 4px 8px;
  font-size: 11px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid
    ${({ active, theme }: { active?: boolean; theme: SupersetTheme }) =>
      active ? theme.colorPrimary : theme.colorBorder};
  background-color: ${({ active, theme }: { active?: boolean; theme: SupersetTheme }) =>
    active ? theme.colorPrimaryBg : theme.colorBgContainer};
  color: ${({ active, theme }: { active?: boolean; theme: SupersetTheme }) =>
    active ? theme.colorPrimary : theme.colorText};
  display: inline-flex;
  align-items: center;
  gap: 4px;
  &:hover {
    border-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorPrimary};
  }
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const TableWrapper = styled.div`
  flex: 1;
  overflow: auto;
  position: relative;
`;

const StyledTable = styled.table`
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
`;

const TableHead = styled.thead<{ theme?: SupersetTheme }>`
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorBgContainer};
`;

interface HeaderCellProps {
  width?: number;
  isMetric?: boolean;
  pinType?: ColumnPinType;
  pinLeftOffset?: number;
  pinRightOffset?: number;
  isDragging?: boolean;
  isDragOver?: boolean;
  theme?: SupersetTheme;
}

const HeaderCell = styled.th<HeaderCellProps>`
  position: ${({ pinType }: HeaderCellProps) => (pinType && pinType !== 'none' ? 'sticky' : 'relative')};
  ${({ pinType, pinLeftOffset }: HeaderCellProps) =>
    pinType === 'left' ? `left: ${pinLeftOffset ?? 0}px;` : ''}
  ${({ pinType, pinRightOffset }: HeaderCellProps) =>
    pinType === 'right' ? `right: ${pinRightOffset ?? 0}px;` : ''}
  z-index: ${({ pinType }: HeaderCellProps) => (pinType && pinType !== 'none' ? 11 : 10)};
  padding: 8px 10px;
  font-weight: 600;
  text-align: ${({ isMetric }: HeaderCellProps) => (isMetric ? 'right' : 'left')};
  background-color: ${({ isDragOver, pinType, theme }: HeaderCellProps) =>
    isDragOver
      ? theme?.colorPrimaryBg || '#e6f7ff'
      : pinType && pinType !== 'none'
      ? theme?.colorFillAlter || '#fafafa'
      : theme?.colorFillAlter || '#fafafa'};
  opacity: ${({ isDragging }: HeaderCellProps) => (isDragging ? 0.4 : 1)};
  border-bottom: 2px solid ${({ theme }: HeaderCellProps) => theme?.colorBorderSecondary};
  ${({ pinType, theme }: HeaderCellProps) =>
    pinType === 'left'
      ? `border-right: 2px solid ${theme?.colorPrimaryBorder || '#bbb'};`
      : pinType === 'right'
      ? `border-left: 2px solid ${theme?.colorPrimaryBorder || '#bbb'};`
      : ''}
  user-select: none;
  white-space: nowrap;
  width: ${({ width }: HeaderCellProps) => (width ? `${width}px` : 'auto')};
  min-width: 60px;
  box-sizing: border-box;
`;

const HeaderContent = styled.div<{ isMetric?: boolean }>`
  display: flex;
  align-items: center;
  justify-content: ${({ isMetric }: { isMetric?: boolean }) =>
    isMetric ? 'flex-end' : 'flex-start'};
  gap: 6px;
`;

const HeaderLabel = styled.span`
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  &:hover {
    color: ${({ theme }: { theme?: SupersetTheme }) => theme?.colorPrimary};
  }
`;

const CalculatedBadge = styled.span<{ theme?: SupersetTheme }>`
  font-size: 10px;
  font-weight: 700;
  font-style: normal;
  padding: 1px 4px;
  border-radius: 3px;
  background-color: ${({ theme }: { theme?: SupersetTheme }) => theme?.colorPrimaryBg || '#e6f7ff'};
  color: ${({ theme }: { theme?: SupersetTheme }) => theme?.colorPrimary || '#1890ff'};
  margin-right: 4px;
  display: inline-block;
  line-height: 1.2;
`;

const SortIndicator = styled.span<{ theme?: SupersetTheme }>`
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 10px;
  font-weight: 700;
  color: ${({ theme }: { theme: SupersetTheme }) => theme.colorPrimary};
`;

const SortPriority = styled.span`
  font-size: 9px;
  opacity: 0.85;
`;

const ResizeHandle = styled.div<{ theme?: SupersetTheme }>`
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 6px;
  cursor: col-resize;
  z-index: 8;
  &:hover {
    background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorPrimary};
  }
`;

const HeaderIcons = styled.div`
  display: flex;
  align-items: center;
  gap: 2px;
`;

const IconButton = styled.button<{ active?: boolean; theme?: SupersetTheme }>`
  background: none;
  border: none;
  padding: 2px;
  font-size: 11px;
  cursor: pointer;
  border-radius: 2px;
  line-height: 1;
  color: ${({ active, theme }: { active?: boolean; theme: SupersetTheme }) =>
    active ? theme.colorPrimary : theme.colorTextSecondary};
  &:hover {
    color: ${({ theme }: { theme: SupersetTheme }) => theme.colorPrimary};
    background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorFillTertiary};
  }
  &:disabled {
    opacity: 0.3;
    cursor: default;
  }
`;

const FilterPopover = styled.div<{ isMetric?: boolean; theme?: SupersetTheme }>`
  position: absolute;
  top: 100%;
  ${({ isMetric }: { isMetric?: boolean }) => (isMetric ? 'right: 4px;' : 'left: 4px;')}
  z-index: 12;
  background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorBgElevated};
  border: 1px solid ${({ theme }: { theme: SupersetTheme }) => theme.colorBorderSecondary};
  border-radius: 6px;
  padding: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 180px;
  font-weight: normal;
  text-align: left;
`;

const FilterSelect = styled.select<{ theme?: SupersetTheme }>`
  padding: 3px 6px;
  font-size: 11px;
  border-radius: 4px;
  border: 1px solid ${({ theme }: { theme: SupersetTheme }) => theme.colorBorder};
  background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorBgContainer};
  color: ${({ theme }: { theme: SupersetTheme }) => theme.colorText};
`;

const FilterInput = styled.input<{ theme?: SupersetTheme }>`
  padding: 3px 6px;
  font-size: 11px;
  border-radius: 4px;
  border: 1px solid ${({ theme }: { theme: SupersetTheme }) => theme.colorBorder};
  background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorBgContainer};
  color: ${({ theme }: { theme: SupersetTheme }) => theme.colorText};
  width: 100%;
  box-sizing: border-box;
`;

const FilterActions = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  margin-top: 4px;
`;

const TableRow = styled.tr<{ theme?: SupersetTheme; height?: number }>`
  height: ${({ height }: { height?: number }) => (height ? `${height}px` : 'auto')};
  &:nth-of-type(even) {
    background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorFillAlter};
  }
  &:hover {
    background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorFillTertiary};
  }
`;

interface CellProps {
  width?: number;
  isMetric?: boolean;
  pinType?: ColumnPinType;
  pinLeftOffset?: number;
  pinRightOffset?: number;
  isPositive?: boolean;
  isNegative?: boolean;
  barPercent?: number;
  heatMapBg?: string;
  heatMapTextColor?: string;
  theme?: SupersetTheme;
}

const Cell = styled.td<CellProps>`
  position: ${({ pinType }: CellProps) => (pinType && pinType !== 'none' ? 'sticky' : 'relative')};
  ${({ pinType, pinLeftOffset }: CellProps) =>
    pinType === 'left' ? `left: ${pinLeftOffset ?? 0}px;` : ''}
  ${({ pinType, pinRightOffset }: CellProps) =>
    pinType === 'right' ? `right: ${pinRightOffset ?? 0}px;` : ''}
  z-index: ${({ pinType }: CellProps) => (pinType && pinType !== 'none' ? 2 : 1)};
  padding: 6px 10px;
  border-bottom: 1px solid ${({ theme }: CellProps) => theme?.colorBorderSecondary};
  ${({ pinType, theme }: CellProps) =>
    pinType === 'left'
      ? `border-right: 2px solid ${theme?.colorPrimaryBorder || '#bbb'};`
      : pinType === 'right'
      ? `border-left: 2px solid ${theme?.colorPrimaryBorder || '#bbb'};`
      : ''}
  background-color: ${({ pinType, heatMapBg, theme }: CellProps) =>
    heatMapBg
      ? heatMapBg
      : pinType && pinType !== 'none'
      ? theme?.colorBgContainer
      : 'inherit'};
  text-align: ${({ isMetric }: CellProps) => (isMetric ? 'right' : 'left')};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: ${({ width }: CellProps) => (width ? `${width}px` : 'auto')};
  min-width: 60px;
  box-sizing: border-box;
  color: ${({ heatMapTextColor, isPositive, isNegative }: CellProps) =>
    heatMapTextColor
      ? heatMapTextColor
      : isPositive
      ? '#137333'
      : isNegative
      ? '#c5221f'
      : 'inherit'};
  font-weight: ${({ heatMapBg, isPositive, isNegative }: CellProps) =>
    heatMapBg ? 500 : isPositive || isNegative ? 500 : 'normal'};
  ${({ barPercent, heatMapBg }: CellProps) =>
    !heatMapBg && typeof barPercent === 'number' && barPercent > 0
      ? `background: linear-gradient(to right, rgba(24, 144, 255, 0.18) ${barPercent}%, transparent ${barPercent}%);`
      : ''}
`;

const SafeLink = styled.a<{ theme?: SupersetTheme }>`
  color: ${({ theme }: { theme: SupersetTheme }) => theme.colorPrimary};
  text-decoration: underline;
  &:hover {
    opacity: 0.8;
  }
`;

const PaginationFooter = styled.div<{ theme?: SupersetTheme }>`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorFillAlter};
  border-top: 1px solid ${({ theme }: { theme: SupersetTheme }) => theme.colorBorderSecondary};
  font-size: 12px;
  flex-shrink: 0;
  gap: 12px;
  flex-wrap: wrap;
`;

const PaginationInfo = styled.span<{ theme?: SupersetTheme }>`
  color: ${({ theme }: { theme: SupersetTheme }) => theme.colorTextSecondary};
  font-size: 11px;
`;

const PaginationControls = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
`;

const PageSizeSelect = styled.select<{ theme?: SupersetTheme }>`
  padding: 2px 6px;
  font-size: 11px;
  border-radius: 4px;
  border: 1px solid ${({ theme }: { theme: SupersetTheme }) => theme.colorBorder};
  background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorBgContainer};
  color: ${({ theme }: { theme: SupersetTheme }) => theme.colorText};
`;

const EmptyState = styled.div<{ theme?: SupersetTheme }>`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: ${({ theme }: { theme: SupersetTheme }) => theme.colorTextTertiary};
  font-size: 13px;
`;

const ErrorBanner = styled.div<{ theme?: SupersetTheme }>`
  padding: 10px 14px;
  background-color: ${({ theme }: { theme: SupersetTheme }) => theme.colorErrorBg};
  color: ${({ theme }: { theme: SupersetTheme }) => theme.colorError};
  border-bottom: 1px solid ${({ theme }: { theme: SupersetTheme }) => theme.colorErrorBorder};
  font-size: 12px;
`;

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Validates URL string strictly against allowed web protocols (http, https, mailto).
 * Rejects javascript:, data:, and vbscript: URLs to prevent XSS.
 */
export function isSafeUrl(urlStr: string): boolean {
  if (!urlStr || typeof urlStr !== 'string') return false;
  const trimmed = urlStr.trim();
  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' || parsed.protocol === 'mailto:';
  } catch {
    // Relative or protocol-less URLs starting with / or safe prefixes
    if (trimmed.startsWith('/') || trimmed.startsWith('#')) return true;
    return /^https?:\/\//i.test(trimmed) || /^mailto:/i.test(trimmed);
  }
}

/**
 * Helper to escape special XML characters (&, <, >, ", ').
 */
export function escapeXml(str: unknown): string {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

/**
 * Exports data records to standard CSV with UTF-8 BOM.
 */
export function exportToCsv(data: DataRecord[], columns: EnterpriseTableColumn[], filename = 'export.csv'): void {
  if (!data || data.length === 0) return;
  const headers = columns.map(c => `"${c.label.replace(/"/g, '""')}"`).join(',');
  const rows = data.map(row =>
    columns
      .map(c => {
        const val = row[c.key];
        if (val === null || val === undefined) return '""';
        return `"${String(val).replace(/"/g, '""')}"`;
      })
      .join(','),
  );
  const csvContent = `\uFEFF${headers}\r\n${rows.join('\r\n')}`;
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Exports data records to XML Spreadsheet 2003 format (native Excel .xlsx/.xml support)
 * preserving continuous heat map cell background colors via ss:Interior styles.
 */
export function exportToExcel(
  data: DataRecord[],
  columns: EnterpriseTableColumn[],
  filename = 'export.xls',
  heatMapConfig?: HeatMapConfig,
): void {
  if (!data || data.length === 0) return;

  // Pre-calculate global min/max if per_table scope
  let tableMin = Infinity;
  let tableMax = -Infinity;
  if (heatMapConfig && heatMapConfig.colorMode !== 'none' && heatMapConfig.scope === 'per_table') {
    columns.forEach(col => {
      if (col.isMetric || col.dataType === 'number') {
        if (col.minValue !== undefined && col.minValue < tableMin) tableMin = col.minValue;
        if (col.maxValue !== undefined && col.maxValue > tableMax) tableMax = col.maxValue;
      }
    });
  }

  // Styles map to store unique cell styles: styleId -> { bgHex, textColor }
  const stylesMap = new Map<string, { bgHex: string; textColor: string }>();

  // Helper to get style ID for a cell
  const getCellStyleId = (col: EnterpriseTableColumn, val: unknown): string | null => {
    if (!heatMapConfig || heatMapConfig.colorMode === 'none') return null;
    if (typeof val !== 'number' || Number.isNaN(val)) return null;

    const min = heatMapConfig.scope === 'per_table' ? tableMin : col.minValue ?? 0;
    const max = heatMapConfig.scope === 'per_table' ? tableMax : col.maxValue ?? 0;
    const colorInfo = computeHeatMapColor(val, min, max, heatMapConfig);
    if (!colorInfo) return null;

    const cleanHex = colorInfo.backgroundColor.replace('#', '').toUpperCase();
    const styleId = `s_${cleanHex}`;
    if (!stylesMap.has(styleId)) {
      stylesMap.set(styleId, {
        bgHex: colorInfo.backgroundColor,
        textColor: colorInfo.textColor,
      });
    }
    return styleId;
  };

  const headerCells = columns
    .map(c => `<Cell><Data ss:Type="String">${escapeXml(c.label)}</Data></Cell>`)
    .join('');

  const dataRows = data
    .map(row => {
      const cells = columns
        .map(c => {
          const val = row[c.key];
          if (val === null || val === undefined) {
            return '<Cell><Data ss:Type="String"></Data></Cell>';
          }
          const isNum = typeof val === 'number';
          const styleId = getCellStyleId(c, val);
          const styleAttr = styleId ? ` ss:StyleID="${styleId}"` : '';
          return `<Cell${styleAttr}><Data ss:Type="${isNum ? 'Number' : 'String'}">${isNum ? val : escapeXml(val)}</Data></Cell>`;
        })
        .join('');
      return `<Row>${cells}</Row>`;
    })
    .join('');

  let stylesXml = `<Style ss:ID="Default" ss:Name="Normal">
   <Alignment ss:Vertical="Bottom"/>
   <Borders/>
   <Font ss:FontName="Calibri" ss:Size="11" ss:Color="#000000"/>
   <Interior/>
   <NumberFormat/>
   <Protection/>
  </Style>`;

  stylesMap.forEach((style, styleId) => {
    stylesXml += `
  <Style ss:ID="${styleId}">
   <Interior ss:Color="${style.bgHex}" ss:Pattern="Solid"/>
   <Font ss:Color="${style.textColor}"/>
  </Style>`;
  });

  const xml = `<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Styles>
  ${stylesXml}
 </Styles>
 <Worksheet ss:Name="Sheet1">
  <Table>
   <Row>${headerCells}</Row>
   ${dataRows}
  </Table>
 </Worksheet>
</Workbook>`;

  const blob = new Blob([xml], { type: 'application/vnd.ms-excel' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export const EnterpriseTableChart: React.FC<EnterpriseTableTransformedProps> = ({
  data,
  columns,
  width,
  height,
  isLoading = false,
  errorMessage,
  pageSize: initialPageSize = 20,
  includeSearch = true,
  enableColumnSort = true,
  enableColumnResize = true,
  enableColumnReorder = true,
  enableColumnFilters = true,
  enableColumnPinning = true,
  enableSavedLayouts = true,
  enableCellBars = true,
  enableValueColoring = true,
  enableHyperlinks = true,
  enableExportExcel = true,
  enableVirtualization = false,
  virtualRowHeight = 32,
  layoutStorageKey,
  tableCalculations = [],
  heatMapConfig,
}) => {
  // --- 1. Quick Table Calculations Evaluation ---
  const { data: dataWithCalculations, calculatedColumns } = useMemo(() => {
    return applyTableCalculations(data, columns, tableCalculations);
  }, [data, columns, tableCalculations]);

  const effectiveColumns = useMemo(() => {
    return [...columns, ...calculatedColumns];
  }, [columns, calculatedColumns]);

  // Global min/max across all numeric columns for table-wide heat map scope
  const { tableMin, tableMax } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    effectiveColumns.forEach(col => {
      if (col.isMetric || col.dataType === 'number') {
        if (col.minValue !== undefined && col.minValue < min) min = col.minValue;
        if (col.maxValue !== undefined && col.maxValue > max) max = col.maxValue;
      }
    });
    return {
      tableMin: min === Infinity ? 0 : min,
      tableMax: max === -Infinity ? 0 : max,
    };
  }, [effectiveColumns]);

  // --- 2. State ---
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sortConfig, setSortConfig] = useState<ColumnSortItem[]>([]);
  const [columnOrder, setColumnOrder] = useState<string[]>([]);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const [columnPinning, setColumnPinning] = useState<Record<string, ColumnPinType>>({});
  const [columnFilters, setColumnFilters] = useState<Record<string, ColumnFilter>>({});
  const [activeFilterPopover, setActiveFilterPopover] = useState<string | null>(null);
  const [activePinPopover, setActivePinPopover] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(initialPageSize);
  const [layoutSavedMessage, setLayoutSavedMessage] = useState<string | null>(null);

  // Drag and Drop state
  const [draggedColKey, setDraggedColKey] = useState<string | null>(null);
  const [dragOverColKey, setDragOverColKey] = useState<string | null>(null);

  // Virtualization scroll state
  const [scrollTop, setScrollTop] = useState<number>(0);
  const tableWrapperRef = useRef<HTMLDivElement | null>(null);

  // Active resize cleanup ref for unmount safety
  const activeResizeCleanupRef = useRef<(() => void) | null>(null);

  // --- 3. Layout Persistence (localStorage) ---
  useEffect(() => {
    if (!enableSavedLayouts || !layoutStorageKey) return;
    try {
      const stored = localStorage.getItem(layoutStorageKey);
      if (stored) {
        const layout = JSON.parse(stored) as SavedTableLayout;
        if (layout.version === 1) {
          if (Array.isArray(layout.columnOrder)) setColumnOrder(layout.columnOrder);
          if (layout.columnWidths) setColumnWidths(layout.columnWidths);
          if (layout.columnPinning) setColumnPinning(layout.columnPinning);
          if (layout.pageSize) setPageSize(layout.pageSize);
          if (layout.sortConfig) setSortConfig(layout.sortConfig);
        }
      }
    } catch {
      // Ignore storage read errors
    }
  }, [enableSavedLayouts, layoutStorageKey]);

  const handleSaveLayout = useCallback(() => {
    if (!layoutStorageKey) return;
    const layout: SavedTableLayout = {
      version: 1,
      columnOrder,
      columnWidths,
      columnPinning,
      pageSize,
      sortConfig,
    };
    try {
      localStorage.setItem(layoutStorageKey, JSON.stringify(layout));
      setLayoutSavedMessage(t('Layout saved!'));
      setTimeout(() => setLayoutSavedMessage(null), 2500);
    } catch {
      // Ignore write errors
    }
  }, [layoutStorageKey, columnOrder, columnWidths, columnPinning, pageSize, sortConfig]);

  const handleResetLayout = useCallback(() => {
    if (layoutStorageKey) {
      try {
        localStorage.removeItem(layoutStorageKey);
      } catch {
        // Ignore
      }
    }
    setColumnOrder(effectiveColumns.map(c => c.key));
    setColumnWidths({});
    setColumnPinning({});
    setSortConfig([]);
    setPageSize(initialPageSize);
    setLayoutSavedMessage(t('Layout reset!'));
    setTimeout(() => setLayoutSavedMessage(null), 2500);
  }, [effectiveColumns, initialPageSize, layoutStorageKey]);

  // Synchronize column order when incoming columns change
  useEffect(() => {
    const colKeys = effectiveColumns.map(c => c.key);
    setColumnOrder(prev => {
      if (prev.length === 0 || !colKeys.every(k => prev.includes(k))) {
        return colKeys;
      }
      return prev;
    });
  }, [effectiveColumns]);

  // Cleanup active resize event listeners if component unmounts mid-drag
  useEffect(() => {
    return () => {
      if (activeResizeCleanupRef.current) {
        activeResizeCleanupRef.current();
        activeResizeCleanupRef.current = null;
      }
    };
  }, []);

  // --- 4. Pinned and Ordered Column Hierarchy ---
  const orderedColumns = useMemo(() => {
    const colMap = new Map(effectiveColumns.map(c => [c.key, c]));
    const baseOrder = columnOrder.length > 0 ? columnOrder : effectiveColumns.map(c => c.key);

    const leftPinned: EnterpriseTableColumn[] = [];
    const unpinned: EnterpriseTableColumn[] = [];
    const rightPinned: EnterpriseTableColumn[] = [];

    baseOrder.forEach(k => {
      const col = colMap.get(k);
      if (!col) return;
      const pin = columnPinning[k] || 'none';
      if (pin === 'left') leftPinned.push(col);
      else if (pin === 'right') rightPinned.push(col);
      else unpinned.push(col);
    });

    // Add any remaining unmapped columns
    effectiveColumns.forEach(col => {
      if (
        !leftPinned.some(c => c.key === col.key) &&
        !unpinned.some(c => c.key === col.key) &&
        !rightPinned.some(c => c.key === col.key)
      ) {
        unpinned.push(col);
      }
    });

    return [...leftPinned, ...unpinned, ...rightPinned];
  }, [effectiveColumns, columnOrder, columnPinning]);

  // Calculate sticky left and right pixel offsets for pinned columns
  const { leftOffsets, rightOffsets } = useMemo(() => {
    const lOffsets: Record<string, number> = {};
    const rOffsets: Record<string, number> = {};

    let currentLeft = 0;
    orderedColumns.forEach(col => {
      if (columnPinning[col.key] === 'left') {
        lOffsets[col.key] = currentLeft;
        currentLeft += columnWidths[col.key] || 120;
      }
    });

    let currentRight = 0;
    for (let i = orderedColumns.length - 1; i >= 0; i -= 1) {
      const col = orderedColumns[i];
      if (columnPinning[col.key] === 'right') {
        rOffsets[col.key] = currentRight;
        currentRight += columnWidths[col.key] || 120;
      }
    }

    return { leftOffsets: lOffsets, rightOffsets: rOffsets };
  }, [orderedColumns, columnPinning, columnWidths]);

  // --- 5. Filtering & Searching ---
  const filteredData = useMemo(() => {
    return dataWithCalculations.filter((row: DataRecord) => {
      // Global Search term check
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const matchesAny = orderedColumns.some(col => {
          const val = row[col.key];
          if (val === null || val === undefined) return false;
          return String(val).toLowerCase().includes(term);
        });
        if (!matchesAny) return false;
      }

      // Per-column filter check
      const filterKeys = Object.keys(columnFilters);
      for (let i = 0; i < filterKeys.length; i += 1) {
        const key = filterKeys[i];
        const filter = columnFilters[key];
        if (!filter || !filter.value) continue;

        const val = row[key];
        const filterVal = filter.value.toLowerCase();
        const numVal = typeof val === 'number' ? val : parseFloat(String(val));
        const filterNum = parseFloat(filter.value);

        switch (filter.operator) {
          case 'contains':
            if (val === null || val === undefined) return false;
            if (!String(val).toLowerCase().includes(filterVal)) return false;
            break;
          case 'equals':
            if (String(val ?? '').toLowerCase() !== filterVal) return false;
            break;
          case 'startsWith':
            if (!String(val ?? '').toLowerCase().startsWith(filterVal)) return false;
            break;
          case 'greaterThan':
            if (Number.isNaN(numVal) || Number.isNaN(filterNum) || numVal <= filterNum) return false;
            break;
          case 'lessThan':
            if (Number.isNaN(numVal) || Number.isNaN(filterNum) || numVal >= filterNum) return false;
            break;
          case 'between': {
            const secondaryNum = parseFloat(filter.secondaryValue ?? '');
            if (Number.isNaN(numVal) || Number.isNaN(filterNum) || Number.isNaN(secondaryNum)) return false;
            if (numVal < filterNum || numVal > secondaryNum) return false;
            break;
          }
          default:
            break;
        }
      }

      return true;
    });
  }, [dataWithCalculations, searchTerm, orderedColumns, columnFilters]);

  // --- 6. Sorting ---
  const sortedData = useMemo(() => {
    if (sortConfig.length === 0) return filteredData;

    return [...filteredData].sort((a, b) => {
      for (let i = 0; i < sortConfig.length; i += 1) {
        const { key, direction } = sortConfig[i];
        const valA = a[key];
        const valB = b[key];

        if (valA === valB) continue;
        if (valA === null || valA === undefined) return 1;
        if (valB === null || valB === undefined) return -1;

        const comparison =
          typeof valA === 'number' && typeof valB === 'number'
            ? valA - valB
            : String(valA).localeCompare(String(valB), undefined, { numeric: true });

        return direction === 'asc' ? comparison : -comparison;
      }
      return 0;
    });
  }, [filteredData, sortConfig]);

  const processedData = sortedData;

  // --- 7. Pagination & Virtualization Slicing ---
  const totalEntries = processedData.length;
  const isVirtual = enableVirtualization && totalEntries > pageSize;
  const totalPages = isVirtual ? 1 : Math.max(1, Math.ceil(totalEntries / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages - 1);

  // Virtual window metrics
  const availableTableHeight = Math.max(200, height - 120);
  const overscan = 5;
  const visibleCount = Math.ceil(availableTableHeight / virtualRowHeight);
  const startIndex = isVirtual ? Math.max(0, Math.floor(scrollTop / virtualRowHeight) - overscan) : safeCurrentPage * pageSize;
  const endIndex = isVirtual ? Math.min(totalEntries, startIndex + visibleCount + overscan * 2) : Math.min(totalEntries, (safeCurrentPage + 1) * pageSize);

  const displayedData = useMemo(() => {
    return processedData.slice(startIndex, endIndex);
  }, [processedData, startIndex, endIndex]);

  const topSpacerHeight = isVirtual ? startIndex * virtualRowHeight : 0;
  const bottomSpacerHeight = isVirtual ? Math.max(0, (totalEntries - endIndex) * virtualRowHeight) : 0;

  const handleScroll = useCallback((e: ReactUIEvent<HTMLDivElement>) => {
    if (isVirtual) {
      setScrollTop(e.currentTarget.scrollTop);
    }
  }, [isVirtual]);

  // --- 8. Interactive Handlers ---

  // Sorting Handler (Shift+Click for multi-column sort)
  const handleHeaderClick = useCallback(
    (key: string, event: ReactMouseEvent) => {
      if (!enableColumnSort) return;
      const isShift = event.shiftKey;

      setSortConfig(prev => {
        const existingIdx = prev.findIndex(item => item.key === key);

        if (isShift) {
          if (existingIdx >= 0) {
            const current = prev[existingIdx];
            if (current.direction === 'asc') {
              const updated = [...prev];
              updated[existingIdx] = { key, direction: 'desc' };
              return updated;
            }
            return prev.filter(item => item.key !== key);
          }
          return [...prev, { key, direction: 'asc' }];
        }

        // Single column sort
        if (existingIdx >= 0) {
          const current = prev[existingIdx];
          if (current.direction === 'asc') {
            return [{ key, direction: 'desc' }];
          }
          return [];
        }
        return [{ key, direction: 'asc' }];
      });
      setCurrentPage(0);
    },
    [enableColumnSort],
  );

  // Column Resizing Handler
  const handleResizeMouseDown = useCallback(
    (key: string, e: ReactMouseEvent) => {
      if (!enableColumnResize) return;
      e.preventDefault();
      e.stopPropagation();

      const startX = e.clientX;
      const initialWidth = columnWidths[key] || 120;

      const onMouseMove = (moveEvent: MouseEvent) => {
        const deltaX = moveEvent.clientX - startX;
        const newWidth = Math.max(60, initialWidth + deltaX);
        setColumnWidths(prev => ({ ...prev, [key]: newWidth }));
      };

      const onMouseUp = () => {
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        activeResizeCleanupRef.current = null;
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
      activeResizeCleanupRef.current = onMouseUp;
    },
    [columnWidths, enableColumnResize],
  );

  // Column Reordering (Button & Drag/Drop)
  const handleMoveColumn = useCallback(
    (key: string, direction: 'left' | 'right') => {
      if (!enableColumnReorder) return;
      setColumnOrder(prev => {
        const order = prev.length > 0 ? [...prev] : effectiveColumns.map(c => c.key);
        const idx = order.indexOf(key);
        if (idx === -1) return order;

        const targetIdx = direction === 'left' ? idx - 1 : idx + 1;
        if (targetIdx < 0 || targetIdx >= order.length) return order;

        const temp = order[idx];
        order[idx] = order[targetIdx];
        order[targetIdx] = temp;
        return order;
      });
    },
    [effectiveColumns, enableColumnReorder],
  );

  // Drag and Drop
  const handleDragStart = useCallback(
    (key: string, e: ReactDragEvent) => {
      if (!enableColumnReorder) return;
      setDraggedColKey(key);
      e.dataTransfer.setData('text/plain', key);
      e.dataTransfer.effectAllowed = 'move';
    },
    [enableColumnReorder],
  );

  const handleDragOver = useCallback(
    (key: string, e: ReactDragEvent) => {
      if (!enableColumnReorder) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      if (dragOverColKey !== key) {
        setDragOverColKey(key);
      }
    },
    [enableColumnReorder, dragOverColKey],
  );

  const handleDrop = useCallback(
    (targetKey: string, e: ReactDragEvent) => {
      if (!enableColumnReorder) return;
      e.preventDefault();
      const sourceKey = e.dataTransfer.getData('text/plain') || draggedColKey;
      if (!sourceKey || sourceKey === targetKey) {
        setDraggedColKey(null);
        setDragOverColKey(null);
        return;
      }

      setColumnOrder(prev => {
        const order = prev.length > 0 ? [...prev] : effectiveColumns.map(c => c.key);
        const sourceIdx = order.indexOf(sourceKey);
        const targetIdx = order.indexOf(targetKey);
        if (sourceIdx === -1 || targetIdx === -1) return order;

        order.splice(sourceIdx, 1);
        order.splice(targetIdx, 0, sourceKey);
        return [...order];
      });

      setDraggedColKey(null);
      setDragOverColKey(null);
    },
    [enableColumnReorder, draggedColKey, effectiveColumns],
  );

  // Column Pinning
  const handleSetPinning = useCallback((key: string, pin: ColumnPinType) => {
    setColumnPinning(prev => {
      const next = { ...prev };
      if (pin === 'none') {
        delete next[key];
      } else {
        next[key] = pin;
      }
      return next;
    });
    setActivePinPopover(null);
  }, []);

  // Column Filters
  const handleSetColumnFilter = useCallback(
    (key: string, operator: FilterOperator, value: string, secondaryValue?: string) => {
      setColumnFilters(prev => ({
        ...prev,
        [key]: { key, operator, value, secondaryValue },
      }));
      setCurrentPage(0);
    },
    [],
  );

  const handleClearColumnFilter = useCallback((key: string) => {
    setColumnFilters(prev => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
    setCurrentPage(0);
  }, []);

  // --- 9. Render Guards ---
  if (errorMessage) {
    return (
      <Container width={width} height={height} data-test="enterprise-table-container">
        <ErrorBanner data-test="enterprise-table-error">{errorMessage}</ErrorBanner>
      </Container>
    );
  }

  if (isLoading) {
    return (
      <Container width={width} height={height} data-test="enterprise-table-container">
        <EmptyState data-test="enterprise-table-loading">
          <div>{t('Loading Enterprise Table...')}</div>
        </EmptyState>
      </Container>
    );
  }

  if (data.length === 0) {
    return (
      <Container width={width} height={height} data-test="enterprise-table-container">
        <EmptyState data-test="enterprise-table-empty">
          <div>{t('No data records available')}</div>
        </EmptyState>
      </Container>
    );
  }

  return (
    <Container width={width} height={height} data-test="enterprise-table-container">
      {/* Top Header Bar */}
      <HeaderBar data-test="enterprise-table-header-bar">
        <TitleContainer>
          <Title>{t('Enterprise Interactive Table')}</Title>
          <Badge data-test="row-count-badge">
            {totalEntries} {t('rows')}
          </Badge>
          {layoutSavedMessage && (
            <Badge style={{ backgroundColor: '#f6ffed', color: '#52c41a' }}>
              {layoutSavedMessage}
            </Badge>
          )}
        </TitleContainer>

        <ControlsGroup>
          {includeSearch && (
            <SearchInput
              type="text"
              placeholder={t('Search table...')}
              value={searchTerm}
              onChange={(e: ChangeEvent<HTMLInputElement>) => {
                setSearchTerm(e.target.value);
                setCurrentPage(0);
              }}
              data-test="enterprise-table-search"
            />
          )}

          {enableSavedLayouts && (
            <>
              <ActionButton
                onClick={handleSaveLayout}
                data-test="save-layout-button"
                title={t('Save current column order, widths, and pinning to local browser storage')}
              >
                💾 {t('Save Layout')}
              </ActionButton>
              <ActionButton
                onClick={handleResetLayout}
                data-test="reset-layout-button"
                title={t('Reset table layout to defaults')}
              >
                ↺ {t('Reset')}
              </ActionButton>
            </>
          )}

          {enableExportExcel && (
            <>
              <ActionButton
                onClick={() => exportToExcel(processedData, orderedColumns, 'export.xls', heatMapConfig)}
                data-test="export-excel-button"
                title={t('Export table to native Excel Spreadsheet with heat map colors')}
              >
                📊 {t('Excel')}
              </ActionButton>
              <ActionButton
                onClick={() => exportToCsv(processedData, orderedColumns, 'export.csv')}
                data-test="export-csv-button"
                title={t('Export table to standard CSV')}
              >
                📄 {t('CSV')}
              </ActionButton>
            </>
          )}
        </ControlsGroup>
      </HeaderBar>

      {/* Main Grid Wrapper */}
      <TableWrapper
        ref={tableWrapperRef}
        onScroll={handleScroll}
        data-test="enterprise-table-grid"
      >
        <StyledTable>
          <TableHead>
            <tr>
              {orderedColumns.map((col, index) => {
                const sortItem = sortConfig.find(item => item.key === col.key);
                const isSorted = Boolean(sortItem);
                const sortPriority = sortConfig.findIndex(item => item.key === col.key) + 1;
                const colWidth = columnWidths[col.key];
                const pin = columnPinning[col.key] || 'none';
                const hasFilter = Boolean(columnFilters[col.key]?.value);
                const isFirst = index === 0;
                const isLast = index === orderedColumns.length - 1;

                return (
                  <HeaderCell
                    key={col.key}
                    width={colWidth}
                    isMetric={col.isMetric}
                    pinType={pin}
                    pinLeftOffset={leftOffsets[col.key]}
                    pinRightOffset={rightOffsets[col.key]}
                    isDragging={draggedColKey === col.key}
                    isDragOver={dragOverColKey === col.key}
                    draggable={enableColumnReorder}
                    onDragStart={(e: ReactDragEvent) => handleDragStart(col.key, e)}
                    onDragOver={(e: ReactDragEvent) => handleDragOver(col.key, e)}
                    onDrop={(e: ReactDragEvent) => handleDrop(col.key, e)}
                    data-test={`header-${col.key}`}
                  >
                    <HeaderContent isMetric={col.isMetric}>
                      <HeaderLabel
                        onClick={(e: ReactMouseEvent) => handleHeaderClick(col.key, e)}
                        title={t('Click to sort, Shift+Click for multi-sort')}
                      >
                        {col.isCalculated && (
                          <CalculatedBadge title={t('Quick Table Calculation')}>
                            fx
                          </CalculatedBadge>
                        )}
                        <span style={col.isCalculated ? { fontStyle: 'italic' } : undefined}>
                          {col.label}
                        </span>
                      </HeaderLabel>

                      {isSorted && (
                        <SortIndicator data-test={`sort-indicator-${col.key}`}>
                          {sortItem?.direction === 'asc' ? '▲' : '▼'}
                          {sortConfig.length > 1 && (
                            <SortPriority>{sortPriority}</SortPriority>
                          )}
                        </SortIndicator>
                      )}

                      <HeaderIcons>
                        {/* Column Reorder Arrow Buttons */}
                        {enableColumnReorder && (
                          <>
                            <IconButton
                              disabled={isFirst}
                              onClick={(e: ReactMouseEvent) => {
                                e.stopPropagation();
                                handleMoveColumn(col.key, 'left');
                              }}
                              title={t('Move column left')}
                              data-test={`move-left-${col.key}`}
                            >
                              ◀
                            </IconButton>
                            <IconButton
                              disabled={isLast}
                              onClick={(e: ReactMouseEvent) => {
                                e.stopPropagation();
                                handleMoveColumn(col.key, 'right');
                              }}
                              title={t('Move column right')}
                              data-test={`move-right-${col.key}`}
                            >
                              ▶
                            </IconButton>
                          </>
                        )}

                        {/* Pinning Action */}
                        {enableColumnPinning && (
                          <IconButton
                            active={pin !== 'none'}
                            onClick={(e: ReactMouseEvent) => {
                              e.stopPropagation();
                              setActivePinPopover(activePinPopover === col.key ? null : col.key);
                              setActiveFilterPopover(null);
                            }}
                            title={t('Pin column left or right')}
                            data-test={`pin-button-${col.key}`}
                          >
                            📌
                          </IconButton>
                        )}

                        {/* Filtering Action */}
                        {enableColumnFilters && (
                          <IconButton
                            active={hasFilter}
                            onClick={(e: ReactMouseEvent) => {
                              e.stopPropagation();
                              setActiveFilterPopover(activeFilterPopover === col.key ? null : col.key);
                              setActivePinPopover(null);
                            }}
                            title={t('Filter column')}
                            data-test={`filter-button-${col.key}`}
                          >
                            🔍
                          </IconButton>
                        )}
                      </HeaderIcons>
                    </HeaderContent>

                    {/* Pinning Popover */}
                    {activePinPopover === col.key && (
                      <FilterPopover
                        isMetric={col.isMetric}
                        data-test={`pin-popover-${col.key}`}
                      >
                        <ActionButton
                          active={pin === 'left'}
                          onClick={() => handleSetPinning(col.key, 'left')}
                          data-test={`pin-left-${col.key}`}
                        >
                          ⬅ {t('Pin Left')}
                        </ActionButton>
                        <ActionButton
                          active={pin === 'right'}
                          onClick={() => handleSetPinning(col.key, 'right')}
                          data-test={`pin-right-${col.key}`}
                        >
                          ➡ {t('Pin Right')}
                        </ActionButton>
                        <ActionButton
                          active={pin === 'none'}
                          onClick={() => handleSetPinning(col.key, 'none')}
                          data-test={`pin-none-${col.key}`}
                        >
                          ✕ {t('Unpin')}
                        </ActionButton>
                      </FilterPopover>
                    )}

                    {/* Filtering Popover */}
                    {activeFilterPopover === col.key && (
                      <FilterPopover
                        isMetric={col.isMetric}
                        data-test={`filter-popover-${col.key}`}
                      >
                        <FilterSelect
                          value={
                            columnFilters[col.key]?.operator ??
                            (col.isMetric ? 'greaterThan' : 'contains')
                          }
                          onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                            const op = e.target.value as FilterOperator;
                            handleSetColumnFilter(
                              col.key,
                              op,
                              columnFilters[col.key]?.value ?? '',
                              columnFilters[col.key]?.secondaryValue,
                            );
                          }}
                          data-test={`filter-operator-${col.key}`}
                        >
                          {col.isMetric ? (
                            <>
                              <option value="greaterThan">&gt; {t('Greater than')}</option>
                              <option value="lessThan">&lt; {t('Less than')}</option>
                              <option value="equals">= {t('Equals')}</option>
                              <option value="between">{t('Between')}</option>
                            </>
                          ) : (
                            <>
                              <option value="contains">{t('Contains')}</option>
                              <option value="equals">{t('Equals')}</option>
                              <option value="startsWith">{t('Starts with')}</option>
                            </>
                          )}
                        </FilterSelect>

                        <FilterInput
                          type={col.isMetric ? 'number' : 'text'}
                          placeholder={t('Filter value...')}
                          value={columnFilters[col.key]?.value ?? ''}
                          onChange={(e: ChangeEvent<HTMLInputElement>) => {
                            const currentOp =
                              columnFilters[col.key]?.operator ??
                              (col.isMetric ? 'greaterThan' : 'contains');
                            handleSetColumnFilter(
                              col.key,
                              currentOp,
                              e.target.value,
                              columnFilters[col.key]?.secondaryValue,
                            );
                          }}
                          data-test={`filter-input-${col.key}`}
                        />

                        {columnFilters[col.key]?.operator === 'between' && (
                          <FilterInput
                            type="number"
                            placeholder={t('Max value...')}
                            value={columnFilters[col.key]?.secondaryValue ?? ''}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => {
                              handleSetColumnFilter(
                                col.key,
                                'between',
                                columnFilters[col.key]?.value ?? '',
                                e.target.value,
                              );
                            }}
                            data-test={`filter-secondary-input-${col.key}`}
                          />
                        )}

                        <FilterActions>
                          <ActionButton
                            onClick={() => {
                              handleClearColumnFilter(col.key);
                              setActiveFilterPopover(null);
                            }}
                            data-test={`filter-clear-${col.key}`}
                          >
                            {t('Clear')}
                          </ActionButton>
                          <ActionButton
                            active
                            onClick={() => setActiveFilterPopover(null)}
                            data-test={`filter-apply-${col.key}`}
                          >
                            {t('Close')}
                          </ActionButton>
                        </FilterActions>
                      </FilterPopover>
                    )}

                    {/* Column Resizing Handle */}
                    {enableColumnResize && (
                      <ResizeHandle
                        onMouseDown={(e: ReactMouseEvent) =>
                          handleResizeMouseDown(col.key, e)
                        }
                        data-test={`resize-handle-${col.key}`}
                      />
                    )}
                  </HeaderCell>
                );
              })}
            </tr>
          </TableHead>
          <tbody>
            {/* Top Virtual Spacer */}
            {isVirtual && topSpacerHeight > 0 && (
              <tr style={{ height: `${topSpacerHeight}px` }}>
                <td colSpan={orderedColumns.length} style={{ padding: 0, border: 'none' }} />
              </tr>
            )}

            {displayedData.map((row: DataRecord, index: number) => {
              const rowIndex = isVirtual ? startIndex + index : safeCurrentPage * pageSize + index;
              return (
                <TableRow
                  key={`row-${rowIndex}`}
                  height={virtualRowHeight}
                  data-test={`row-${rowIndex}`}
                >
                  {orderedColumns.map(col => {
                    const val = row[col.key];
                    const colWidth = columnWidths[col.key];
                    const pin = columnPinning[col.key] || 'none';
                    const isNum = typeof val === 'number';

                    // Continuous Highlight Table / Heat Map Calculation
                    let heatMapBg: string | undefined;
                    let heatMapTextColor: string | undefined;

                    if (
                      heatMapConfig &&
                      heatMapConfig.colorMode !== 'none' &&
                      isNum
                    ) {
                      const min =
                        heatMapConfig.scope === 'per_table'
                          ? tableMin
                          : col.minValue ?? 0;
                      const max =
                        heatMapConfig.scope === 'per_table'
                          ? tableMax
                          : col.maxValue ?? 0;
                      const colorInfo = computeHeatMapColor(
                        val as number,
                        min,
                        max,
                        heatMapConfig,
                      );
                      if (colorInfo) {
                        heatMapBg = colorInfo.backgroundColor;
                        heatMapTextColor = colorInfo.textColor;
                      }
                    }

                    // Fallback to Positive / Negative Value Coloring if heat map is off
                    const isPositive = !heatMapBg && enableValueColoring && isNum && (val as number) > 0;
                    const isNegative = !heatMapBg && enableValueColoring && isNum && (val as number) < 0;

                    // Cell Bars calculation
                    let barPercent: number | undefined;
                    if (
                      !heatMapBg &&
                      enableCellBars &&
                      isNum &&
                      col.minValue !== undefined &&
                      col.maxValue !== undefined
                    ) {
                      const range = col.maxValue - (col.minValue < 0 ? col.minValue : 0);
                      if (range > 0) {
                        const effectiveVal = (val as number) - (col.minValue < 0 ? col.minValue : 0);
                        barPercent = Math.max(0, Math.min(100, (effectiveVal / range) * 100));
                      }
                    }

                    // Hyperlink Safe Rendering
                    const isLink = enableHyperlinks && typeof val === 'string' && isSafeUrl(val);

                    // Value formatting for calculated and raw numbers
                    let displayVal = '-';
                    if (val !== null && val !== undefined) {
                      if (col.isCalculated && isNum) {
                        if (
                          col.calculationType === 'percent_of_total' ||
                          col.calculationType === 'percent_difference_from' ||
                          col.calculationType === 'percentile'
                        ) {
                          displayVal = `${(val as number).toFixed(2)}%`;
                        } else if (col.calculationType === 'rank') {
                          displayVal = String(Math.round(val as number));
                        } else {
                          displayVal = Number.isInteger(val as number)
                            ? String(val)
                            : (val as number).toFixed(2);
                        }
                      } else {
                        displayVal = String(val);
                      }
                    }

                    return (
                      <Cell
                        key={`cell-${col.key}-${rowIndex}`}
                        width={colWidth}
                        isMetric={col.isMetric}
                        pinType={pin}
                        pinLeftOffset={leftOffsets[col.key]}
                        pinRightOffset={rightOffsets[col.key]}
                        isPositive={isPositive}
                        isNegative={isNegative}
                        barPercent={barPercent}
                        heatMapBg={heatMapBg}
                        heatMapTextColor={heatMapTextColor}
                        data-test={`cell-${col.key}-${rowIndex}`}
                      >
                        {isLink ? (
                          <SafeLink
                            href={displayVal}
                            target="_blank"
                            rel="noopener noreferrer"
                            data-test={`link-${col.key}-${rowIndex}`}
                          >
                            {displayVal}
                          </SafeLink>
                        ) : (
                          displayVal
                        )}
                      </Cell>
                    );
                  })}
                </TableRow>
              );
            })}

            {/* Bottom Virtual Spacer */}
            {isVirtual && bottomSpacerHeight > 0 && (
              <tr style={{ height: `${bottomSpacerHeight}px` }}>
                <td colSpan={orderedColumns.length} style={{ padding: 0, border: 'none' }} />
              </tr>
            )}
          </tbody>
        </StyledTable>
      </TableWrapper>

      {/* Bottom Pagination Footer */}
      <PaginationFooter data-test="pagination-footer">
        <PaginationInfo>
          {isVirtual
            ? t('Showing %s of %s virtual rows (rendered dynamically)', displayedData.length, totalEntries)
            : t(
                'Showing %s to %s of %s entries',
                totalEntries === 0 ? 0 : safeCurrentPage * pageSize + 1,
                Math.min((safeCurrentPage + 1) * pageSize, totalEntries),
                totalEntries,
              )}
          {totalEntries !== data.length && (
            <span> {t('(filtered from %s total entries)', data.length)}</span>
          )}
        </PaginationInfo>

        {!isVirtual && (
          <PaginationControls>
            <PageSizeSelect
              value={pageSize}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(0);
              }}
              data-test="page-size-select"
            >
              <option value={10}>10 / page</option>
              <option value={20}>20 / page</option>
              <option value={50}>50 / page</option>
              <option value={100}>100 / page</option>
              <option value={200}>200 / page</option>
            </PageSizeSelect>

            <ActionButton
              disabled={safeCurrentPage === 0}
              onClick={() => setCurrentPage(0)}
              data-test="page-first"
              title={t('First page')}
            >
              ⏮
            </ActionButton>
            <ActionButton
              disabled={safeCurrentPage === 0}
              onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
              data-test="page-prev"
              title={t('Previous page')}
            >
              ◀
            </ActionButton>

            <span data-test="page-indicator">
              {t('Page %s of %s', safeCurrentPage + 1, totalPages)}
            </span>

            <ActionButton
              disabled={safeCurrentPage >= totalPages - 1}
              onClick={() => setCurrentPage(prev => Math.min(totalPages - 1, prev + 1))}
              data-test="page-next"
              title={t('Next page')}
            >
              ▶
            </ActionButton>
            <ActionButton
              disabled={safeCurrentPage >= totalPages - 1}
              onClick={() => setCurrentPage(totalPages - 1)}
              data-test="page-last"
              title={t('Last page')}
            >
              ⏭
            </ActionButton>
          </PaginationControls>
        )}
      </PaginationFooter>
    </Container>
  );
};

export default EnterpriseTableChart;
