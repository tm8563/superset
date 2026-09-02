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

import { testWithAssets, expect } from '../../helpers/fixtures';
import { apiPost, apiPut } from '../../helpers/api/requests';
import {
  apiPostDashboard,
  buildSingleRowDashboardLayout,
} from '../../helpers/api/dashboard';
import { getDatasetByName } from '../../helpers/api/dataset';
import { extractIdFromResponse } from '../../helpers/api/assertions';
import { DashboardPage } from '../../pages/DashboardPage';
import { TIMEOUT } from '../../utils/constants';
import {
  buildFilterJsonMetadata,
  buildSelectFilter,
} from './dashboard-test-helpers';

const DATASET_NAME = 'enterprise_table_test_data';

testWithAssets(
  'Dashboard Filter Presets: Save, reload, restore 2+ filters, and drift detection warning',
  async ({ page, testAssets }) => {
    testWithAssets.setTimeout(TIMEOUT.SLOW_TEST);

    // 1. Target dataset 28: enterprise_table_test_data
    const datasetId = 28;

    // 2. Create chart
    const chartParams = {
      datasource: `${datasetId}__table`,
      viz_type: 'big_number_total',
      metric: 'count',
      adhoc_filters: [],
      header_font_size: 0.4,
      subheader_font_size: 0.15,
    };
    const chartResp = await apiPost(page, 'api/v1/chart/', {
      slice_name: `filter_presets_e2e_${Date.now()}`,
      viz_type: 'big_number_total',
      datasource_id: datasetId,
      datasource_type: 'table',
      params: JSON.stringify(chartParams),
    });
    expect(chartResp.ok()).toBe(true);
    const chartId = await extractIdFromResponse(chartResp);
    testAssets.trackChart(chartId);

    // 3. Create dashboard with 2 native filters: Gender and State
    const positionJson = buildSingleRowDashboardLayout([
      {
        id: chartId,
        sliceName: 'filter_presets_chart',
        width: 12,
        height: 50,
      },
    ]);

    const filter1 = buildSelectFilter({
      datasetId,
      column: 'customer_region',
      chartsInScope: [chartId],
      name: 'Region',
    });

    const filter2 = buildSelectFilter({
      datasetId,
      column: 'product_category',
      chartsInScope: [chartId],
      name: 'Category',
    });

    const initialJsonMetadata = buildFilterJsonMetadata({
      chartsInScope: [chartId],
      nativeFilters: [filter1, filter2],
    });

    const dashResp = await apiPostDashboard(page, {
      dashboard_title: `filter_presets_e2e_dash_${Date.now()}`,
      published: true,
      position_json: JSON.stringify(positionJson),
      json_metadata: JSON.stringify(initialJsonMetadata),
    });
    expect(dashResp.ok()).toBe(true);
    const dashboardId = await extractIdFromResponse(dashResp);
    testAssets.trackDashboard(dashboardId);

    // Associate chart with dashboard
    const linkResp = await apiPut(page, `api/v1/chart/${chartId}`, {
      dashboards: [dashboardId],
    });
    expect(linkResp.ok()).toBe(true);

    // 4. Navigate to dashboard
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.gotoById(dashboardId);
    await dashboardPage.waitForLoad({ timeout: TIMEOUT.SLOW_TEST });
    await dashboardPage.waitForChartsToLoad();
    const filterBar = await dashboardPage.waitForFilterBar();

    // 5. Select 2 active filters: Region = 'North America' and Category = 'Hardware'
    await filterBar.selectOption('North America', 0);
    await filterBar.selectOption('Hardware', 1);

    const chartDataPromise1 = page.waitForResponse(
      r => r.url().includes('/api/v1/chart/data') && r.request().method() === 'POST',
      { timeout: 15_000 },
    );
    await filterBar.apply();
    await chartDataPromise1;
    await dashboardPage.waitForChartsToLoad();

    // 6. Save a preset via UI
    const presetsDropdownTrigger = page.locator('[data-test="filter-presets-dropdown-trigger"]');
    await expect(presetsDropdownTrigger).toBeVisible();
    await presetsDropdownTrigger.click();

    const saveViewBtn = page.locator('[data-test="save-current-view-btn"]');
    await expect(saveViewBtn).toBeVisible();
    await saveViewBtn.click();

    const presetNameInput = page.locator('[data-test="preset-name-input"]');
    await expect(presetNameInput).toBeVisible();
    const presetName = 'NA Hardware Executive View';
    await presetNameInput.fill(presetName);

    const saveSubmitBtn = page.locator('[data-test="save-filter-preset-submit"]');
    await saveSubmitBtn.click();

    // Verify modal closes and preset is saved in dropdown
    await expect(presetNameInput).not.toBeVisible();
    await presetsDropdownTrigger.click();
    await expect(page.locator(`text=${presetName}`)).toBeVisible();

    // 7. Simulate a new session by reloading the page
    await page.reload();
    await dashboardPage.waitForLoad({ timeout: TIMEOUT.SLOW_TEST });
    await dashboardPage.waitForChartsToLoad();

    // 8. Load the preset via FilterPresetsDropdown UI
    await presetsDropdownTrigger.click();
    const applyPresetBtn = page.locator('[data-test^="apply-preset-"]').first();
    await expect(applyPresetBtn).toBeVisible();
    await applyPresetBtn.click();

    // 9. Confirm the filter bar visually reflects restored values in DOM
    await expect(filterBar.root.getByText('North America')).toBeVisible();
    await expect(filterBar.root.getByText('Hardware')).toBeVisible();

    // 10. Trigger schema drift: modify the dashboard's filter configuration
    // (remove the 'Category' filter to cause checksum and schema drift)
    const driftedJsonMetadata = buildFilterJsonMetadata({
      chartsInScope: [chartId],
      nativeFilters: [filter1], // filter2 (Category) removed
    });

    const updateDashResp = await apiPut(page, `api/v1/dashboard/${dashboardId}`, {
      json_metadata: JSON.stringify(driftedJsonMetadata),
    });
    expect(updateDashResp.ok()).toBe(true);

    // Reload page to pick up drifted dashboard metadata
    await page.reload();
    await dashboardPage.waitForLoad({ timeout: TIMEOUT.SLOW_TEST });
    await dashboardPage.waitForChartsToLoad();

    // 11. Click preset from dropdown to trigger drift detection modal
    await presetsDropdownTrigger.click();
    const applyPresetBtnDrift = page.locator('[data-test^="apply-preset-"]').first();
    await expect(applyPresetBtnDrift).toBeVisible();
    await applyPresetBtnDrift.click();

    // 12. Confirm DriftWarningModal renders with correct warning text
    await expect(page.locator('text=Dashboard Filters Changed (View Drift)')).toBeVisible();
    await expect(
      page.locator('text=This saved view was created before the dashboard filters were modified.'),
    ).toBeVisible();
    await expect(page.locator('[data-test="drift-modal-proceed"]')).toBeVisible();

    // Proceed with applying compatible filters
    await page.locator('[data-test="drift-modal-proceed"]').click();
    await expect(page.locator('text=Dashboard Filters Changed (View Drift)')).not.toBeVisible();
  },
);
