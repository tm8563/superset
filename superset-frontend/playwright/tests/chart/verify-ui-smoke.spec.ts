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

test('Smoke test: Superset loads past login with zero module errors and displays Enterprise Table in chart gallery', async ({ page }) => {
  test.setTimeout(90000);
  const artifactDir = process.env.PLAYWRIGHT_ARTIFACT_DIR || path.join(__dirname, '../../../../test-results/smoke-artifacts');
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

  console.log('1. Navigating to login page...');
  await page.goto('http://localhost:8088/login/');
  await page.waitForTimeout(1000);

  const usernameInput = page.locator('input[name="username"], #username');
  if (await usernameInput.isVisible()) {
    console.log('Filling login credentials...');
    await usernameInput.fill('admin');
    await page.locator('input[name="password"], #password').fill('admin');
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle' }),
      page.locator('input[type="submit"], button[type="submit"]').click(),
    ]);
  }

  console.log(`Logged in. Current URL: ${page.url()}`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(artifactDir, '01_welcome_page.png') });

  console.log('2. Navigating to chart creation page...');
  await page.goto('http://localhost:8088/chart/add', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(artifactDir, '02_chart_add_page.png') });

  // Select dataset
  const datasetSelect = page.locator('.ant-select-selector').first();
  if (await datasetSelect.isVisible()) {
    console.log('Selecting dataset from dropdown...');
    await datasetSelect.click();
    await page.waitForTimeout(1000);
    const option = page.locator('.ant-select-item-option').first();
    if (await option.isVisible()) {
      await option.click();
      await page.waitForTimeout(1500);
    }
  }

  await page.screenshot({ path: path.join(artifactDir, '03_dataset_selected.png') });

  // Open Chart Type gallery modal if present
  const vizTypeSelect = page.locator('[data-test="select-viz-type"], [data-test="viz-type-selector"], button:has-text("Choose a type"), div:has-text("Choose chart type"), div:has-text("Choose a visualization type")').first();
  if (await vizTypeSelect.isVisible()) {
    console.log('Opening chart gallery modal...');
    await vizTypeSelect.click();
    await page.waitForTimeout(2000);
  }

  // Search for Enterprise in the gallery search
  const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="search"]').first();
  if (await searchInput.isVisible()) {
    console.log('Searching for Enterprise in gallery...');
    await searchInput.fill('Enterprise');
    await page.waitForTimeout(1500);
  }

  await page.screenshot({ path: path.join(artifactDir, '04_enterprise_table_gallery.png') });

  // Verify zero 'Cannot find module' errors
  const moduleErrors = consoleErrors.filter(e => e.includes('Cannot find module') || e.includes('thumbnail.png'));
  console.log(`Module errors found in browser console: ${moduleErrors.length}`);
  expect(moduleErrors).toHaveLength(0);

  const pageContent = await page.content();
  const hasEnterpriseTable = pageContent.includes('Enterprise Interactive Table') || pageContent.includes('enterprise_table');
  console.log(`Enterprise Interactive Table found in DOM: ${hasEnterpriseTable}`);
  expect(hasEnterpriseTable).toBe(true);

  console.log('SUCCESS: All UI and asset resolution assertions passed.');
});
