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

import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  EnterpriseTableChart,
  isSafeUrl,
  escapeXml,
  exportToCsv,
  exportToExcel,
} from '../src/EnterpriseTableChart';
import {
  EnterpriseTableColumn,
  EnterpriseTableTransformedProps,
  TableCalculationConfig,
  HeatMapConfig,
} from '../src/types';

const defaultProps: EnterpriseTableTransformedProps = {
  data: [
    { region: 'North America', sales: 100, profit: 20, link: 'https://example.com/na' },
    { region: 'EMEA', sales: 200, profit: -50, link: 'https://example.com/emea' },
    { region: 'APAC', sales: 150, profit: 30, link: 'javascript:alert(1)' },
    { region: 'LATAM', sales: 80, profit: -15, link: 'mailto:latam@example.com' },
  ],
  columns: [
    { key: 'region', label: 'Region', isMetric: false, dataType: 'string' },
    { key: 'sales', label: 'Sales', isMetric: true, dataType: 'number', minValue: 80, maxValue: 200 },
    { key: 'profit', label: 'Profit', isMetric: true, dataType: 'number', minValue: -50, maxValue: 30 },
    { key: 'link', label: 'Website', isMetric: false, dataType: 'string' },
  ],
  width: 800,
  height: 600,
  pageSize: 2,
  includeSearch: true,
  enableColumnSort: true,
  enableColumnResize: true,
  enableColumnReorder: true,
  enableColumnFilters: true,
  enableColumnPinning: true,
  enableSavedLayouts: true,
  enableCellBars: true,
  enableValueColoring: true,
  enableHyperlinks: true,
  enableExportExcel: true,
  enableVirtualization: false,
  virtualRowHeight: 32,
  layoutStorageKey: 'test_table_layout_1',
  rawFormData: {},
};

beforeEach(() => {
  localStorage.clear();
  jest.clearAllMocks();
});

test('renders empty state when data array is empty', () => {
  render(<EnterpriseTableChart {...defaultProps} data={[]} />);
  expect(screen.getByTestId('enterprise-table-empty')).toBeInTheDocument();
  expect(screen.getByText('No data records available')).toBeInTheDocument();
});

test('renders loading state when isLoading is true', () => {
  render(<EnterpriseTableChart {...defaultProps} isLoading />);
  expect(screen.getByTestId('enterprise-table-loading')).toBeInTheDocument();
  expect(screen.getByText('Loading Enterprise Table...')).toBeInTheDocument();
});

test('renders error state when errorMessage is provided', () => {
  render(
    <EnterpriseTableChart
      {...defaultProps}
      errorMessage="Failed to fetch query data"
    />,
  );
  expect(screen.getByTestId('enterprise-table-error')).toBeInTheDocument();
  expect(screen.getByText('Failed to fetch query data')).toBeInTheDocument();
});

test('renders table headers and data rows correctly with pagination', () => {
  render(<EnterpriseTableChart {...defaultProps} />);
  expect(screen.getByTestId('enterprise-table-container')).toBeInTheDocument();
  expect(screen.getByTestId('enterprise-table-grid')).toBeInTheDocument();
  expect(screen.getByTestId('header-region')).toHaveTextContent('Region');
  expect(screen.getByTestId('header-sales')).toHaveTextContent('Sales');
  expect(screen.getByTestId('row-count-badge')).toHaveTextContent('4 rows');

  // Page 1 displays first 2 rows
  expect(screen.getByTestId('row-0')).toBeInTheDocument();
  expect(screen.getByTestId('row-1')).toBeInTheDocument();
  expect(screen.queryByTestId('row-2')).not.toBeInTheDocument();
});

test('handles single and multi-column sorting (Shift+Click)', () => {
  render(<EnterpriseTableChart {...defaultProps} pageSize={10} />);

  // Single click to sort sales ascending
  const salesHeader = screen.getByTestId('header-sales');
  fireEvent.click(salesHeader.querySelector('span')!);

  expect(screen.getByTestId('sort-indicator-sales')).toHaveTextContent('▲');
  expect(screen.getByTestId('cell-sales-0')).toHaveTextContent('80'); // LATAM is lowest

  // Click again for descending sort
  fireEvent.click(salesHeader.querySelector('span')!);
  expect(screen.getByTestId('sort-indicator-sales')).toHaveTextContent('▼');
  expect(screen.getByTestId('cell-sales-0')).toHaveTextContent('200'); // EMEA is highest

  // Shift+Click on region for multi-sort
  const regionHeader = screen.getByTestId('header-region');
  fireEvent.click(regionHeader.querySelector('span')!, { shiftKey: true });
  expect(screen.getByTestId('sort-indicator-region')).toHaveTextContent('▲');
});

test('handles column pinning and sticky left/right layout', () => {
  render(<EnterpriseTableChart {...defaultProps} pageSize={10} />);

  const pinBtn = screen.getByTestId('pin-button-profit');
  fireEvent.click(pinBtn);
  expect(screen.getByTestId('pin-popover-profit')).toBeInTheDocument();

  const pinLeftBtn = screen.getByTestId('pin-left-profit');
  fireEvent.click(pinLeftBtn);

  // Pinned left columns appear first
  const headers = screen.getAllByRole('columnheader');
  expect(headers[0]).toHaveAttribute('data-test', 'header-profit');
});

test('supports saving and resetting table layout in localStorage', () => {
  render(<EnterpriseTableChart {...defaultProps} pageSize={10} />);

  const saveBtn = screen.getByTestId('save-layout-button');
  fireEvent.click(saveBtn);

  const stored = localStorage.getItem('test_table_layout_1');
  expect(stored).not.toBeNull();
  expect(JSON.parse(stored || '{}').version).toBe(1);

  const resetBtn = screen.getByTestId('reset-layout-button');
  fireEvent.click(resetBtn);
  expect(localStorage.getItem('test_table_layout_1')).toBeNull();
});

test('renders positive/negative value coloring and cell bars', () => {
  render(<EnterpriseTableChart {...defaultProps} pageSize={10} />);

  // Profit for North America is positive (20) -> #137333
  const positiveCell = screen.getByTestId('cell-profit-0');
  expect(positiveCell).toHaveStyle({ color: '#137333' });

  // Profit for EMEA is negative (-50) -> #c5221f
  const negativeCell = screen.getByTestId('cell-profit-1');
  expect(negativeCell).toHaveStyle({ color: '#c5221f' });
});

test('safely validates URLs and prevents javascript XSS injection', () => {
  expect(isSafeUrl('https://example.com')).toBe(true);
  expect(isSafeUrl('http://example.com/test')).toBe(true);
  expect(isSafeUrl('mailto:user@example.com')).toBe(true);
  expect(isSafeUrl('javascript:alert(document.cookie)')).toBe(false);
  expect(isSafeUrl('data:text/html,<script>alert(1)</script>')).toBe(false);
  expect(isSafeUrl('vbscript:msgbox(1)')).toBe(false);

  render(<EnterpriseTableChart {...defaultProps} pageSize={10} />);

  // Safe link renders as <a>
  expect(screen.getByTestId('link-link-0')).toBeInTheDocument();
  expect(screen.getByTestId('link-link-0')).toHaveAttribute('href', 'https://example.com/na');
  expect(screen.getByTestId('link-link-0')).toHaveAttribute('rel', 'noopener noreferrer');

  // Malicious javascript: URL is NOT rendered as an <a> link; rendered as safe plain text
  expect(screen.queryByTestId('link-link-2')).not.toBeInTheDocument();
  expect(screen.getByTestId('cell-link-2')).toHaveTextContent('javascript:alert(1)');
});

test('escapeXml correctly escapes &, <, >, ", and \' characters', () => {
  expect(escapeXml('AT&T <corp> "quoted" \'single\'')).toBe(
    'AT&amp;T &lt;corp&gt; &quot;quoted&quot; &apos;single&apos;',
  );
  expect(escapeXml(null)).toBe('');
  expect(escapeXml(undefined)).toBe('');
  expect(escapeXml(123)).toBe('123');
});

test('exportToExcel properly escapes XML in headers and cell values preventing XML injection', () => {
  let generatedXml = '';
  const OriginalBlob = global.Blob;
  global.Blob = jest.fn().mockImplementation((parts: BlobPart[], options?: BlobPropertyBag) => {
    generatedXml = parts.join('');
    return new OriginalBlob(parts, options);
  }) as unknown as typeof Blob;

  const appendChildSpy = jest.spyOn(document.body, 'appendChild');
  const removeChildSpy = jest.spyOn(document.body, 'removeChild');
  window.URL.createObjectURL = jest.fn(() => 'blob:mock-excel-url');
  window.URL.revokeObjectURL = jest.fn();

  const maliciousData = [
    {
      colA: '<Injection>Alert & Test</Injection>',
      colB: 'Safe "Value" & \'Data\'',
      numCol: 42,
    },
  ];
  const columns: EnterpriseTableColumn[] = [
    { key: 'colA', label: 'Header <1> & "A"', isMetric: false, dataType: 'string' },
    { key: 'colB', label: 'Header <b> & \'B\'', isMetric: false, dataType: 'string' },
    { key: 'numCol', label: 'Count', isMetric: true, dataType: 'number' },
  ];

  exportToExcel(maliciousData, columns, 'test.xls');

  expect(generatedXml).toContain('<Data ss:Type="String">Header &lt;1&gt; &amp; &quot;A&quot;</Data>');
  expect(generatedXml).toContain('<Data ss:Type="String">Header &lt;b&gt; &amp; &apos;B&apos;</Data>');
  expect(generatedXml).toContain('<Data ss:Type="String">&lt;Injection&gt;Alert &amp; Test&lt;/Injection&gt;</Data>');
  expect(generatedXml).toContain('<Data ss:Type="String">Safe &quot;Value&quot; &amp; &apos;Data&apos;</Data>');
  expect(generatedXml).toContain('<Data ss:Type="Number">42</Data>');
  // Ensure unescaped XML injection tags do NOT exist in the output XML
  expect(generatedXml).not.toContain('<Injection>');

  global.Blob = OriginalBlob;
  appendChildSpy.mockRestore();
  removeChildSpy.mockRestore();
});

test('handles Excel and CSV export functions from action buttons', () => {
  const appendChildSpy = jest.spyOn(document.body, 'appendChild');
  const removeChildSpy = jest.spyOn(document.body, 'removeChild');
  window.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
  window.URL.revokeObjectURL = jest.fn();

  render(<EnterpriseTableChart {...defaultProps} pageSize={10} />);

  const csvBtn = screen.getByTestId('export-csv-button');
  fireEvent.click(csvBtn);
  expect(window.URL.createObjectURL).toHaveBeenCalled();

  const excelBtn = screen.getByTestId('export-excel-button');
  fireEvent.click(excelBtn);
  expect(window.URL.createObjectURL).toHaveBeenCalled();

  exportToCsv(defaultProps.data, defaultProps.columns);
  exportToExcel(defaultProps.data, defaultProps.columns);

  appendChildSpy.mockRestore();
  removeChildSpy.mockRestore();
});

test('supports virtualization windowing mode for high data volume', () => {
  const largeData = Array.from({ length: 10000 }, (_, i) => ({
    region: `Region ${i}`,
    sales: 100 + i,
    profit: (i % 2 === 0 ? 1 : -1) * (i * 2),
    link: `https://example.com/${i}`,
  }));

  render(
    <EnterpriseTableChart
      {...defaultProps}
      data={largeData}
      enableVirtualization
      virtualRowHeight={30}
      height={300}
    />,
  );

  expect(screen.getByTestId('enterprise-table-container')).toBeInTheDocument();
  // Virtual mode renders visible window rows instead of creating 10,000 DOM nodes
  const rows = screen.getAllByRole('row');
  expect(rows.length).toBeLessThan(50);
});

test('filters rows when global search term is entered', () => {
  render(<EnterpriseTableChart {...defaultProps} pageSize={10} />);
  const searchInput = screen.getByTestId('enterprise-table-search');
  fireEvent.change(searchInput, { target: { value: 'latam' } });

  expect(screen.getByTestId('cell-region-0')).toHaveTextContent('LATAM');
  expect(screen.queryByTestId('row-1')).not.toBeInTheDocument();
});

test('supports pagination next, prev, and page size selection', () => {
  render(<EnterpriseTableChart {...defaultProps} pageSize={2} />);

  // First page shows North America and EMEA
  expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 1 of 2');
  expect(screen.getByTestId('cell-region-0')).toHaveTextContent('North America');

  // Go to next page
  const nextBtn = screen.getByTestId('page-next');
  fireEvent.click(nextBtn);
  expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 2 of 2');
  expect(screen.getByTestId('cell-region-2')).toHaveTextContent('APAC');

  // Go back to prev page
  const prevBtn = screen.getByTestId('page-prev');
  fireEvent.click(prevBtn);
  expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 1 of 2');

  // Change page size to 10
  const pageSizeSelect = screen.getByTestId('page-size-select');
  fireEvent.change(pageSizeSelect, { target: { value: '10' } });
  expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 1 of 1');
  expect(screen.getByTestId('row-3')).toBeInTheDocument();
});

// ============================================================================
// PHASE 9 TESTS: TABLE CALCULATIONS & HIGHLIGHT TABLE / HEAT MAP
// ============================================================================

describe('Phase 9: Table Calculations & Highlight Table Integration', () => {
  test('renders active quick table calculations with fx badge and computed values', () => {
    const tableCalculations: TableCalculationConfig[] = [
      {
        column: 'sales',
        type: 'percent_of_total',
        basis: 'column',
      },
      {
        column: 'sales',
        type: 'rank',
        rankMode: 'dense',
        rankDirection: 'desc',
      },
      {
        column: 'sales',
        type: 'running_total',
      },
    ];

    render(
      <EnterpriseTableChart
        {...defaultProps}
        pageSize={10}
        tableCalculations={tableCalculations}
      />,
    );

    // Total sales = 100 + 200 + 150 + 80 = 530
    // Header for calculated columns should have fx badge
    const pctHeader = screen.getByTestId('header-sales_calc_percent_of_total_column');
    expect(pctHeader).toBeInTheDocument();
    expect(pctHeader).toHaveTextContent('fx');
    expect(pctHeader).toHaveTextContent('% of Column (Sales)');

    const rankHeader = screen.getByTestId('header-sales_calc_rank_dense_desc');
    expect(rankHeader).toBeInTheDocument();
    expect(rankHeader).toHaveTextContent('Dense Rank (Desc) of Sales');

    const runningHeader = screen.getByTestId('header-sales_calc_running_total');
    expect(runningHeader).toBeInTheDocument();
    expect(runningHeader).toHaveTextContent('Running Total of Sales');

    // Values in cells:
    // Row 0: NA (sales 100) -> 100/530 = 18.87%, Rank 3, Running Total 100
    expect(screen.getByTestId('cell-sales_calc_percent_of_total_column-0')).toHaveTextContent('18.87%');
    expect(screen.getByTestId('cell-sales_calc_rank_dense_desc-0')).toHaveTextContent('3');
    expect(screen.getByTestId('cell-sales_calc_running_total-0')).toHaveTextContent('100');

    // Row 1: EMEA (sales 200) -> 200/530 = 37.74%, Rank 1, Running Total 300
    expect(screen.getByTestId('cell-sales_calc_percent_of_total_column-1')).toHaveTextContent('37.74%');
    expect(screen.getByTestId('cell-sales_calc_rank_dense_desc-1')).toHaveTextContent('1');
    expect(screen.getByTestId('cell-sales_calc_running_total-1')).toHaveTextContent('300');
  });

  test('renders continuous heat map background colors with contrast text', () => {
    const heatMapConfig: HeatMapConfig = {
      colorMode: 'sequential',
      palette: 'dark_blue',
      scope: 'per_column',
    };

    render(
      <EnterpriseTableChart
        {...defaultProps}
        pageSize={10}
        heatMapConfig={heatMapConfig}
      />,
    );

    // Sales min is 80 (LATAM), max is 200 (EMEA)
    const maxSalesCell = screen.getByTestId('cell-sales-1'); // EMEA sales 200
    expect(maxSalesCell).toHaveStyle({ backgroundColor: expect.stringMatching(/#|rgb/) });

    const minSalesCell = screen.getByTestId('cell-sales-3'); // LATAM sales 80
    expect(minSalesCell).toHaveStyle({ backgroundColor: expect.stringMatching(/#|rgb/) });
  });

  test('exportToExcel generates ss:Interior and Style definitions with exact cell color matching', () => {
    let generatedXml = '';
    const OriginalBlob = global.Blob;
    global.Blob = jest.fn().mockImplementation((parts: BlobPart[], options?: BlobPropertyBag) => {
      generatedXml = parts.join('');
      return new OriginalBlob(parts, options);
    }) as unknown as typeof Blob;

    const appendChildSpy = jest.spyOn(document.body, 'appendChild');
    const removeChildSpy = jest.spyOn(document.body, 'removeChild');
    window.URL.createObjectURL = jest.fn(() => 'blob:mock-excel-url');
    window.URL.revokeObjectURL = jest.fn();

    const heatMapConfig: HeatMapConfig = {
      colorMode: 'diverging',
      scope: 'per_column',
      midpoint: 0,
    };

    // Columns: profit has min = -50, max = 30
    // Sample Cell 1: EMEA profit = -50 (minimum / negative endpoint)
    // Sample Cell 2: LATAM profit = -15 (intermediate negative)
    // Sample Cell 3: NA profit = 20 (positive value)
    // Sample Cell 4: APAC profit = 30 (maximum / positive endpoint)
    exportToExcel(defaultProps.data, defaultProps.columns, 'heatmap_test.xls', heatMapConfig);

    // 1. Verify Styles container & attributes
    expect(generatedXml).toContain('<Styles>');
    expect(generatedXml).toContain('<Interior ss:Color=');
    expect(generatedXml).toContain('ss:Pattern="Solid"');

    // 2. Sample Cell 1: EMEA profit = -50 (diverging min -> #D73027)
    // Diverging palette[0] is #d73027
    expect(generatedXml).toContain('<Style ss:ID="s_D73027">');
    expect(generatedXml).toContain('<Interior ss:Color="#D73027" ss:Pattern="Solid"/>');
    expect(generatedXml).toContain('<Cell ss:StyleID="s_D73027"><Data ss:Type="Number">-50</Data></Cell>');

    // 3. Sample Cell 2: APAC profit = 30 (diverging max -> #1A9850)
    // Diverging palette[8] is #1a9850
    expect(generatedXml).toContain('<Style ss:ID="s_1A9850">');
    expect(generatedXml).toContain('<Interior ss:Color="#1A9850" ss:Pattern="Solid"/>');
    expect(generatedXml).toContain('<Cell ss:StyleID="s_1A9850"><Data ss:Type="Number">30</Data></Cell>');

    // 4. Sample Cell 3: NA profit = 20 (interpolated positive -> 20/30 of upper scale)
    // Upper scale: 0.5 + 0.5*(20/30) = 0.8333 -> color between #A6D96A and #66BD63 -> #7BC665
    expect(generatedXml).toContain('<Cell ss:StyleID="s_7BC665"><Data ss:Type="Number">20</Data></Cell>');
    expect(generatedXml).toContain('<Style ss:ID="s_7BC665">');
    expect(generatedXml).toContain('<Interior ss:Color="#7BC665" ss:Pattern="Solid"/>');

    global.Blob = OriginalBlob;
    appendChildSpy.mockRestore();
    removeChildSpy.mockRestore();
  });
});
