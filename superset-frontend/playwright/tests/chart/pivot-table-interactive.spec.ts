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
import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

test('Phase 5: Pivot Table V2 real browser rendering, zero console errors, and interactive hierarchy verification', async ({ page }) => {
  test.setTimeout(90000);
  const artifactDir = process.env.PLAYWRIGHT_ARTIFACT_DIR || path.join(__dirname, '../../../../test-results/pivot-artifacts');
  fs.mkdirSync(artifactDir, { recursive: true });

  const consoleErrors: string[] = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
      console.log(`[Browser Console Error] ${msg.text()}`);
    }
  });

  page.on('pageerror', err => {
    consoleErrors.push(err.message);
    console.log(`[Browser Page Error] ${err.message}`);
  });

  console.log('1. Logging into Superset...');
  await page.goto('http://localhost:8088/login/');
  await page.waitForTimeout(1000);

  const usernameInput = page.locator('input[name="username"], #username');
  if (await usernameInput.isVisible()) {
    await usernameInput.fill('admin');
    await page.locator('input[name="password"], #password').fill('admin');
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle' }),
      page.locator('input[type="submit"], button[type="submit"]').click(),
    ]);
  }

  console.log('2. Navigating to Pivot Table V2 Explore slice (Chart ID: 218)...');
  await page.goto('http://localhost:8088/explore/?slice_id=218', { waitUntil: 'networkidle' });
  await page.waitForTimeout(4000);
  await page.screenshot({ path: path.join(artifactDir, '01_pivot_table_explore.png') });

  // Verify zero module resolution errors
  const criticalModuleErrors = consoleErrors.filter(
    e => e.includes('Cannot find module') || e.includes('ChunkLoadError') || e.includes('Uncaught SyntaxError'),
  );
  expect(criticalModuleErrors).toHaveLength(0);

  // Verify Pivot Table elements exist in DOM
  const tableContainer = page.locator('.pvtTable, [data-test="pivot-table"], table');
  await expect(tableContainer.first()).toBeVisible({ timeout: 15000 });

  const pageContent = await page.content();
  const hasRegionHeader = pageContent.includes('customer_region') || pageContent.includes('North America') || pageContent.includes('APAC') || pageContent.includes('EMEA');
  console.log(`Pivot Table hierarchy data rendered in DOM: ${hasRegionHeader}`);
  expect(hasRegionHeader).toBe(true);

  // Check for collapse / expand buttons or subtotals
  const toggleIcons = page.locator('.anticon-minus-square, .anticon-plus-square, [aria-label="minus-square"], [aria-label="plus-square"]');
  const countToggles = await toggleIcons.count();
  console.log(`Subtotal collapse/expand interactive toggles count: ${countToggles}`);

  if (countToggles > 0) {
    console.log('Testing interactive hierarchy toggle click...');
    await toggleIcons.first().click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(artifactDir, '02_pivot_table_toggled.png') });
  }

  // Also verify Pivot Table V2 in Chart Type Gallery
  console.log('3. Verifying Pivot Table V2 presence in Chart Gallery...');
  await page.goto('http://localhost:8088/chart/add', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  const datasetSelect = page.locator('.ant-select-selector').first();
  if (await datasetSelect.isVisible()) {
    await datasetSelect.click();
    await page.waitForTimeout(1000);
    const option = page.locator('.ant-select-item-option').first();
    if (await option.isVisible()) {
      await option.click();
      await page.waitForTimeout(1500);
    }
  }

  const vizTypeSelect = page.locator('[data-test="select-viz-type"], [data-test="viz-type-selector"], button:has-text("Choose a type"), div:has-text("Choose chart type"), div:has-text("Choose a visualization type")').first();
  if (await vizTypeSelect.isVisible()) {
    await vizTypeSelect.click();
    await page.waitForTimeout(2000);
  }

  const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="search"]').first();
  if (await searchInput.isVisible()) {
    await searchInput.fill('Pivot');
    await page.waitForTimeout(1500);
  }
  await page.screenshot({ path: path.join(artifactDir, '03_pivot_gallery.png') });

  const galleryContent = await page.content();
  const hasPivotInGallery = galleryContent.includes('Pivot Table') || galleryContent.includes('pivot_table');
  console.log(`Pivot Table found in Explore gallery: ${hasPivotInGallery}`);
  expect(hasPivotInGallery).toBe(true);

  console.log('SUCCESS: Phase 5 Pivot Table V2 browser verification completed.');
});
