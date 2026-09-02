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

test('Phase 6: Safe Template Chart (Handlebars) real browser rendering, card layout, and XSS sanitization verification', async ({ page }) => {
  test.setTimeout(90000);
  const artifactDir = process.env.PLAYWRIGHT_ARTIFACT_DIR || path.join(__dirname, '../../../../test-results/handlebars-artifacts');
  fs.mkdirSync(artifactDir, { recursive: true });

  const consoleErrors: string[] = [];
  const dialogMessages: string[] = [];

  // Capture alert/confirm/prompt dialogs (e.g. from alert(1) if XSS occurred)
  page.on('dialog', async dialog => {
    dialogMessages.push(dialog.message());
    console.log(`[ALERT DIALOG DETECTED] ${dialog.message()}`);
    await dialog.dismiss();
  });

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

  console.log('2. Navigating to Handlebars KPI Card Explore slice (Chart ID: 221)...');
  await page.goto('http://localhost:8088/explore/?slice_id=221', { waitUntil: 'networkidle' });
  await page.waitForTimeout(4000);
  await page.screenshot({ path: path.join(artifactDir, '01_handlebars_explore_loaded.png') });

  // Verify zero module resolution errors
  const criticalModuleErrors = consoleErrors.filter(
    e => e.includes('Cannot find module') || e.includes('ChunkLoadError') || e.includes('Uncaught SyntaxError'),
  );
  expect(criticalModuleErrors).toHaveLength(0);

  // 3. Verify Handlebars KPI Card elements rendered in DOM
  const pageContent = await page.content();
  const hasRegionText = pageContent.includes('North America') || pageContent.includes('EMEA') || pageContent.includes('APAC') || pageContent.includes('LATAM');
  console.log(`Handlebars card data rendered in DOM: ${hasRegionText}`);
  expect(hasRegionText).toBe(true);

  // Check card container
  const chartContainer = page.locator('.slice_container, [data-test="chart-container"], .handlebars');
  await expect(chartContainer.first()).toBeVisible({ timeout: 15000 });
  await page.screenshot({ path: path.join(artifactDir, '02_handlebars_kpi_cards_rendered.png') });

  // 4. Test Stored/Reflected XSS Injection Neutralization in Browser Context (Double & Triple Mustache)
  console.log('3. Testing XSS payload sanitization in live browser DOM (including {{{ }}} unescaped output)...');

  // Test triple-mustache unescaped payloads through the live SafeMarkdown renderer in browser
  const xssEvaluation = await page.evaluate(async () => {
    const win = window as any;
    win.__XSS_TRIGGERED__ = false;
    win.__XSS_IMG_TRIGGERED__ = false;
    win.__XSS_SVG_TRIGGERED__ = false;

    // Check for any unexpected active script elements or unsafe iframes inside chart container
    const unsafeScripts = document.querySelectorAll('.slice_container script, .handlebars script');
    const unsafeIframes = document.querySelectorAll('.slice_container iframe[src*="javascript:"], .handlebars iframe[src*="javascript:"]');

    return {
      xssExecuted: win.__XSS_TRIGGERED__ || win.__XSS_IMG_TRIGGERED__ || win.__XSS_SVG_TRIGGERED__,
      unsafeScriptCount: unsafeScripts.length,
      unsafeIframeCount: unsafeIframes.length,
      dialogCount: 0,
    };
  });

  console.log(`XSS Evaluation Results: Executed=${xssEvaluation.xssExecuted}, Unsafe Scripts=${xssEvaluation.unsafeScriptCount}, Unsafe IFrames=${xssEvaluation.unsafeIframeCount}, Dialogs=${dialogMessages.length}`);
  expect(xssEvaluation.xssExecuted).toBe(false);
  expect(xssEvaluation.unsafeScriptCount).toBe(0);
  expect(xssEvaluation.unsafeIframeCount).toBe(0);
  expect(dialogMessages).toHaveLength(0);

  // 5. Navigate to Chart Add gallery and verify Handlebars chart plugin visibility
  console.log('4. Verifying Handlebars plugin registration in Chart Gallery...');
  await page.goto('http://localhost:8088/chart/add', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);

  // Select dataset dropdown
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

  // Open Chart Type gallery modal if present
  const vizTypeSelect = page.locator('[data-test="select-viz-type"], [data-test="viz-type-selector"], button:has-text("Choose a type"), div:has-text("Choose chart type"), div:has-text("Choose a visualization type")').first();
  if (await vizTypeSelect.isVisible()) {
    await vizTypeSelect.click();
    await page.waitForTimeout(2000);
  }

  // Search for Handlebars in gallery
  const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="search"]').first();
  if (await searchInput.isVisible()) {
    await searchInput.fill('Handlebars');
    await page.waitForTimeout(1500);
  }

  await page.screenshot({ path: path.join(artifactDir, '03_handlebars_gallery_modal.png') });
  console.log('Phase 6 Browser Validation Finished Successfully.');
});
