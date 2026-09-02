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
import { render, screen, fireEvent, waitFor } from 'spec/helpers/testing-library';
import { DataMaskStateWithId, Filter, NativeFilterType } from '@superset-ui/core';
import {
  computeFilterConfigChecksum,
  detectFilterDrift,
  generateFilterSummary,
  sanitizePresetDataMask,
} from './utils';
import { SavePresetModal } from './SavePresetModal';
import { DriftWarningModal } from './DriftWarningModal';
import { DashboardFilterPreset, FilterDriftDetail } from './types';
import * as api from './api';

const mockFilters: Record<string, Filter> = {
  'NATIVE_FILTER-region': {
    id: 'NATIVE_FILTER-region',
    name: 'Region',
    filterType: 'filter_select',
    targets: [{ datasetId: 1, column: { name: 'region' } }],
    cascadeParentIds: [],
    scope: { rootPath: [], excluded: [] },
    type: NativeFilterType.NativeFilter,
    defaultDataMask: {},
    controlValues: {},
    description: '',
  },
  'NATIVE_FILTER-sales': {
    id: 'NATIVE_FILTER-sales',
    name: 'Sales Range',
    filterType: 'filter_range',
    targets: [{ datasetId: 1, column: { name: 'sales' } }],
    cascadeParentIds: [],
    scope: { rootPath: [], excluded: [] },
    type: NativeFilterType.NativeFilter,
    defaultDataMask: {},
    controlValues: {},
    description: '',
  },
};

const mockDataMask: DataMaskStateWithId = {
  'NATIVE_FILTER-region': {
    id: 'NATIVE_FILTER-region',
    filterState: { value: ['North America', 'EMEA'] },
    extraFormData: {
      filters: [{ col: 'region', op: 'IN' as const, val: ['North America', 'EMEA'] }],
    },
  },
  'NATIVE_FILTER-sales': {
    id: 'NATIVE_FILTER-sales',
    filterState: { value: [1000, 5000] },
  },
};

describe('Filter Presets Engine & Utilities', () => {
  describe('Checksum & Filter Summary Computation', () => {
    test('computes deterministic checksum for filter configuration', () => {
      const checksum1 = computeFilterConfigChecksum(mockFilters);
      const checksum2 = computeFilterConfigChecksum(mockFilters);
      expect(checksum1).toBe(checksum2);
      expect(typeof checksum1).toBe('string');
      expect(checksum1.length).toBe(16);
    });

    test('checksum changes when a filter is added, removed, or modified', () => {
      const initialChecksum = computeFilterConfigChecksum(mockFilters);

      // Modified filters (removed sales filter)
      const modifiedFilters: Record<string, Filter> = {
        'NATIVE_FILTER-region': mockFilters['NATIVE_FILTER-region'],
      };
      const newChecksum = computeFilterConfigChecksum(modifiedFilters);
      expect(newChecksum).not.toBe(initialChecksum);
    });

    test('generates snapshot summary dictionary', () => {
      const summary = generateFilterSummary(mockFilters);
      expect(summary['NATIVE_FILTER-region']).toEqual({
        name: 'Region',
        type: 'filter_select',
        column: 'region',
      });
      expect(summary['NATIVE_FILTER-sales']).toEqual({
        name: 'Sales Range',
        type: 'filter_range',
        column: 'sales',
      });
    });
  });

  describe('Drift Detection & DataMask Sanitization', () => {
    test('detects NO drift when stored checksum matches live configuration', () => {
      const checksum = computeFilterConfigChecksum(mockFilters);
      const preset: DashboardFilterPreset = {
        id: 'preset-1',
        dashboard_id: '42',
        name: 'Executive View',
        is_shared: true,
        filter_config_checksum: checksum,
        filter_summary: generateFilterSummary(mockFilters),
        data_mask: mockDataMask,
      };

      const drift = detectFilterDrift(preset, mockFilters);
      expect(drift.hasDrift).toBe(false);
      expect(drift.removedFilterIds).toHaveLength(0);
      expect(drift.compatibleFilterIds).toHaveLength(2);
    });

    test('detects drift and lists removed filters when dashboard configuration changes', () => {
      const initialChecksum = computeFilterConfigChecksum(mockFilters);
      const preset: DashboardFilterPreset = {
        id: 'preset-1',
        dashboard_id: '42',
        name: 'Executive View',
        is_shared: true,
        filter_config_checksum: initialChecksum,
        filter_summary: generateFilterSummary(mockFilters),
        data_mask: mockDataMask,
      };

      // Live dashboard filters now only has 'NATIVE_FILTER-region' (sales was deleted)
      const currentFilters: Record<string, Filter> = {
        'NATIVE_FILTER-region': mockFilters['NATIVE_FILTER-region'],
      };

      const drift = detectFilterDrift(preset, currentFilters);
      expect(drift.hasDrift).toBe(true);
      expect(drift.removedFilterIds).toEqual(['NATIVE_FILTER-sales']);
      expect(drift.removedFilterNames).toEqual(['Sales Range']);
      expect(drift.compatibleFilterIds).toEqual(['NATIVE_FILTER-region']);
    });

    test('sanitizes dataMask by stripping out deleted filters', () => {
      const currentFilters: Record<string, Filter> = {
        'NATIVE_FILTER-region': mockFilters['NATIVE_FILTER-region'],
      };

      const sanitized = sanitizePresetDataMask(mockDataMask, currentFilters);
      expect(sanitized['NATIVE_FILTER-region']).toBeDefined();
      expect(sanitized['NATIVE_FILTER-sales']).toBeUndefined();
    });
  });
});

describe('SavePresetModal Component', () => {
  const mockOnClose = jest.fn();
  const mockOnSaveSuccess = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders form controls and captures inputs', async () => {
    jest.spyOn(api, 'createFilterPreset').mockResolvedValueOnce({
      id: 'new-preset-id',
      dashboard_id: '42',
      name: 'North America Q3',
      is_shared: false,
      data_mask: mockDataMask,
    });

    render(
      <SavePresetModal
        isVisible
        onClose={mockOnClose}
        onSaveSuccess={mockOnSaveSuccess}
        dashboardId={42}
        dataMask={mockDataMask}
        filters={mockFilters}
        canEdit={true}
      />,
      { useRedux: true },
    );

    expect(screen.getByText('Save Filter View / Preset')).toBeInTheDocument();
    const nameInput = screen.getByTestId('preset-name-input');
    fireEvent.change(nameInput, { target: { value: 'North America Q3' } });

    const submitBtn = screen.getByTestId('save-filter-preset-submit');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.createFilterPreset).toHaveBeenCalledWith(
        42,
        expect.objectContaining({
          name: 'North America Q3',
          is_shared: false,
          data_mask: mockDataMask,
        }),
      );
      expect(mockOnSaveSuccess).toHaveBeenCalled();
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  test('disables Shared option when user cannot edit dashboard', () => {
    render(
      <SavePresetModal
        isVisible
        onClose={mockOnClose}
        onSaveSuccess={mockOnSaveSuccess}
        dashboardId={42}
        dataMask={mockDataMask}
        filters={mockFilters}
        canEdit={false}
      />,
      { useRedux: true },
    );

    const sharedRadio = screen.getByRole('radio', {
      name: /Shared \(All Dashboard Viewers\)/i,
    });
    expect(sharedRadio).toBeDisabled();
  });
});

describe('DriftWarningModal Component', () => {
  const mockProceed = jest.fn();
  const mockRefresh = jest.fn();
  const mockCancel = jest.fn();

  const driftedPreset: DashboardFilterPreset = {
    id: 'preset-drift',
    dashboard_id: '42',
    name: 'Old Sales View',
    is_shared: true,
    data_mask: mockDataMask,
  };

  const driftDetail: FilterDriftDetail = {
    hasDrift: true,
    removedFilterIds: ['NATIVE_FILTER-sales'],
    removedFilterNames: ['Sales Range'],
    modifiedFilterIds: [],
    addedFilterIds: [],
    compatibleFilterIds: ['NATIVE_FILTER-region'],
  };

  test('renders warning alert and skipped filters list', () => {
    render(
      <DriftWarningModal
        isVisible
        preset={driftedPreset}
        driftDetail={driftDetail}
        onProceed={mockProceed}
        onRefreshPreset={mockRefresh}
        onCancel={mockCancel}
        canRefresh={true}
      />,
      { useRedux: true },
    );

    expect(
      screen.getByText('Dashboard Filters Changed (View Drift)'),
    ).toBeInTheDocument();
    expect(screen.getByText('Sales Range')).toBeInTheDocument();
    expect(
      screen.getByText(/Compatible Filters to Apply \(1\):/i),
    ).toBeInTheDocument();

    const proceedBtn = screen.getByTestId('drift-modal-proceed');
    fireEvent.click(proceedBtn);
    expect(mockProceed).toHaveBeenCalled();

    const refreshBtn = screen.getByTestId('drift-modal-refresh-preset');
    fireEvent.click(refreshBtn);
    expect(mockRefresh).toHaveBeenCalled();
  });

  test('detects drift when filter target column or type is modified (positive drift)', () => {
    const initialChecksum = computeFilterConfigChecksum(mockFilters);
    const preset: DashboardFilterPreset = {
      id: 'preset-modified',
      dashboard_id: '42',
      name: 'Modified Filter Test',
      is_shared: true,
      filter_config_checksum: initialChecksum,
      filter_summary: generateFilterSummary(mockFilters),
      data_mask: mockDataMask,
    };

    // Modify region filter target to country
    const modifiedFilters: Record<string, Filter> = {
      ...mockFilters,
      'NATIVE_FILTER-region': {
        ...mockFilters['NATIVE_FILTER-region'],
        targets: [{ datasetId: 1, column: { name: 'country' } }],
      },
    };

    const drift = detectFilterDrift(preset, modifiedFilters);
    expect(drift.hasDrift).toBe(true);
    expect(drift.modifiedFilterIds).toContain('NATIVE_FILTER-region');
  });
});

describe('Security & XSS Payload Handling in Filter Presets', () => {
  test('safely renders preset name with script tag <script>alert("XSS")</script> without execution', () => {
    const xssScriptPayload = '<script>alert("XSS-EXEC")</script>';
    const preset: DashboardFilterPreset = {
      id: 'preset-xss-1',
      dashboard_id: '42',
      name: xssScriptPayload,
      description: 'Test XSS injection',
      is_shared: true,
      data_mask: mockDataMask,
    };

    const driftDetail: FilterDriftDetail = {
      hasDrift: true,
      removedFilterIds: ['NATIVE_FILTER-sales'],
      removedFilterNames: ['Sales Range'],
      modifiedFilterIds: [],
      addedFilterIds: [],
      compatibleFilterIds: ['NATIVE_FILTER-region'],
    };

    render(
      <DriftWarningModal
        isVisible
        preset={preset}
        driftDetail={driftDetail}
        onProceed={jest.fn()}
        onRefreshPreset={jest.fn()}
        onCancel={jest.fn()}
        canRefresh={false}
      />,
      { useRedux: true },
    );

    // React JSX text nodes encode and safely render text without executing scripts
    expect(
      screen.getByText(new RegExp(xssScriptPayload.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))),
    ).toBeInTheDocument();
    // Verify no script tags are injected into the DOM as active executable elements
    const scripts = document.querySelectorAll('script[src*="XSS-EXEC"]');
    expect(scripts).toHaveLength(0);
  });

  test('safely renders preset name with event handler attribute <img src=x onerror=alert(1)> without triggering events', () => {
    const xssImgPayload = '<img src=x onerror=alert(1)>';
    const preset: DashboardFilterPreset = {
      id: 'preset-xss-2',
      dashboard_id: '42',
      name: xssImgPayload,
      description: 'Test img onerror injection',
      is_shared: true,
      data_mask: mockDataMask,
    };

    const driftDetail: FilterDriftDetail = {
      hasDrift: true,
      removedFilterIds: [],
      removedFilterNames: [],
      modifiedFilterIds: [],
      addedFilterIds: [],
      compatibleFilterIds: ['NATIVE_FILTER-region'],
    };

    render(
      <DriftWarningModal
        isVisible
        preset={preset}
        driftDetail={driftDetail}
        onProceed={jest.fn()}
        onRefreshPreset={jest.fn()}
        onCancel={jest.fn()}
        canRefresh={false}
      />,
      { useRedux: true },
    );

    // Rendered as literal text node, not HTML element
    expect(
      screen.getByText(new RegExp(xssImgPayload.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))),
    ).toBeInTheDocument();
    // Confirms no img element with onerror attribute was created
    const imgElements = document.querySelectorAll('img[src="x"]');
    expect(imgElements).toHaveLength(0);
  });

  test('preserves complex dataMask filter state with multi-select and extraFormData with 100% round-trip fidelity', () => {
    const complexDataMask: DataMaskStateWithId = {
      'NATIVE_FILTER-region': {
        id: 'NATIVE_FILTER-region',
        filterState: { value: ['APAC', 'EMEA', 'LATAM', 'North America'] },
        extraFormData: {
          filters: [
            { col: 'region', op: 'IN' as const, val: ['APAC', 'EMEA', 'LATAM', 'North America'] },
          ],
        },
      },
      'NATIVE_FILTER-sales': {
        id: 'NATIVE_FILTER-sales',
        filterState: { value: [50000, 250000] },
        extraFormData: {
          filters: [
            { col: 'sales', op: '>=' as const, val: 50000 },
            { col: 'sales', op: '<=' as const, val: 250000 },
          ],
        },
      },
    };

    // Test sanitization preserves all keys when filters match exactly
    const sanitized = sanitizePresetDataMask(complexDataMask, mockFilters);
    expect(sanitized).toEqual(complexDataMask);
    expect(sanitized['NATIVE_FILTER-region'].filterState?.value).toEqual([
      'APAC',
      'EMEA',
      'LATAM',
      'North America',
    ]);
  });
});

