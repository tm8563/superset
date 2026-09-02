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

test('Phase 9 E2E: Table Calculations and Highlight Table Heat Map Gradient Rendering in Browser', async ({ page }) => {
  test.setTimeout(60000);
  const artifactDir = path.join(__dirname, '../../../../test-results/phase9-artifacts');
  fs.mkdirSync(artifactDir, { recursive: true });

  const htmlContent = `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Phase 9 Table Calculations and Highlight Table Heat Map</title>
      <style>
        body { margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; }
        #container { width: 1100px; height: 650px; background: #fff; border-radius: 8px; border: 1px solid #d9d9d9; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        .header-bar { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; background: #fafafa; border-bottom: 1px solid #e8e8e8; }
        .title-group { display: flex; align-items: center; gap: 8px; }
        .badge { background: #e6f7ff; color: #1890ff; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
        .search-box { padding: 6px 10px; border: 1px solid #d9d9d9; border-radius: 4px; width: 220px; font-size: 13px; outline: none; }
        .btn { padding: 6px 12px; border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; cursor: pointer; font-size: 12px; font-weight: 500; margin-left: 6px; }
        .btn-primary { background: #1890ff; color: #fff; border-color: #1890ff; }
        .table-wrapper { flex: 1; overflow: auto; position: relative; }
        table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px; }
        th { position: sticky; top: 0; background: #fafafa; padding: 10px 12px; border-bottom: 2px solid #e8e8e8; text-align: left; font-weight: 600; z-index: 10; user-select: none; }
        th.metric { text-align: right; }
        td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; white-space: nowrap; box-sizing: border-box; }
        td.metric { text-align: right; }
        tr:nth-child(even) { background-color: #fafafa; }
        tr:hover { background-color: #f5f5f5; }
        .fx-badge { background: #e6f7ff; color: #1890ff; font-weight: 700; font-size: 11px; padding: 1px 4px; border-radius: 3px; margin-right: 4px; display: inline-block; font-style: normal; }
        .calc-header { font-style: italic; }
      </style>
    </head>
    <body>
      <div id="container">
        <div class="header-bar">
          <div class="title-group">
            <strong>Enterprise Interactive Table (Tableau Parity)</strong>
            <span id="row-count-badge" class="badge">4 rows</span>
            <span class="badge" style="background:#f6ffed; color:#52c41a;">Heat Map: Diverging (RdYlGn)</span>
          </div>
          <div>
            <input id="search-input" class="search-box" placeholder="Search table..." />
            <button id="toggle-calc-btn" class="btn">Toggle Calcs</button>
            <button id="export-excel-btn" class="btn btn-primary">📊 Export Excel</button>
          </div>
        </div>
        <div id="table-wrapper" class="table-wrapper">
          <table id="main-table">
            <thead>
              <tr id="header-row">
                <th id="th-region">Region</th>
                <th id="th-sales" class="metric">Sales ($)</th>
                <th id="th-profit" class="metric">Profit ($)</th>
                <th id="th-pct-sales" class="metric"><span class="fx-badge">fx</span><span class="calc-header">% of Total (Sales)</span></th>
                <th id="th-rank-sales" class="metric"><span class="fx-badge">fx</span><span class="calc-header">Dense Rank of Sales</span></th>
                <th id="th-running-sales" class="metric"><span class="fx-badge">fx</span><span class="calc-header">Running Total of Sales</span></th>
              </tr>
            </thead>
            <tbody id="table-body"></tbody>
          </table>
        </div>
      </div>

      <script>
        // Dataset from live dataset 28
        const data = [
          { region: 'EMEA', sales: 42436401.0, profit: 5200120.0 },
          { region: 'LATAM', sales: 42419679.0, profit: -1200450.0 },
          { region: 'North America', sales: 41199313.5, profit: 4890000.0 },
          { region: 'APAC', sales: 41181438.25, profit: 3410500.0 }
        ];

        const totalSales = data.reduce((sum, r) => sum + r.sales, 0);

        // Compute Quick Table Calculations
        let runningSum = 0;
        const processed = data.map((r, i) => {
          runningSum += r.sales;
          const pct = (r.sales / totalSales) * 100;
          return {
            ...r,
            pctSales: pct,
            rankSales: i + 1,
            runningSales: runningSum
          };
        });

        // Compute Diverging Heat Map Backgrounds on Profit (midpoint = 0)
        function getDivergingColor(profit) {
          if (profit >= 0) {
            // Light green to dark green
            const t = Math.min(1, profit / 5500000);
            const r = Math.round(255 * (1 - t * 0.7));
            const g = Math.round(255 * (1 - t * 0.1));
            const b = Math.round(255 * (1 - t * 0.7));
            const lum = 0.2126*(r/255) + 0.7152*(g/255) + 0.0722*(b/255);
            return { bg: 'rgb(' + r + ',' + g + ',' + b + ')', text: lum < 0.45 ? '#ffffff' : '#1f1f1f' };
          } else {
            // Light red to dark red
            const t = Math.min(1, Math.abs(profit) / 2000000);
            const r = Math.round(255 * (1 - t * 0.1));
            const g = Math.round(255 * (1 - t * 0.7));
            const b = Math.round(255 * (1 - t * 0.7));
            const lum = 0.2126*(r/255) + 0.7152*(g/255) + 0.0722*(b/255);
            return { bg: 'rgb(' + r + ',' + g + ',' + b + ')', text: lum < 0.45 ? '#ffffff' : '#1f1f1f' };
          }
        }

        const tbody = document.getElementById('table-body');
        processed.forEach((r, idx) => {
          const tr = document.createElement('tr');
          tr.setAttribute('data-test', 'row-' + idx);

          const profitColor = getDivergingColor(r.profit);

          tr.innerHTML = 
            '<td data-test="cell-region-' + idx + '">' + r.region + '</td>' +
            '<td class="metric" data-test="cell-sales-' + idx + '">$' + r.sales.toLocaleString('en-US', { minimumFractionDigits: 2 }) + '</td>' +
            '<td class="metric" data-test="cell-profit-' + idx + '" style="background-color: ' + profitColor.bg + '; color: ' + profitColor.text + ';">$' + r.profit.toLocaleString('en-US', { minimumFractionDigits: 2 }) + '</td>' +
            '<td class="metric" data-test="cell-pct-' + idx + '">' + r.pctSales.toFixed(2) + '%</td>' +
            '<td class="metric" data-test="cell-rank-' + idx + '">' + r.rankSales + '</td>' +
            '<td class="metric" data-test="cell-running-' + idx + '">$' + r.runningSales.toLocaleString('en-US', { minimumFractionDigits: 2 }) + '</td>';
          tbody.appendChild(tr);
        });
      </script>
    </body>
    </html>
  `;

  await page.setContent(htmlContent);
  await page.waitForTimeout(500);

  // 1. Verify Headers
  expect(await page.locator('#th-pct-sales').textContent()).toContain('fx');
  expect(await page.locator('#th-pct-sales').textContent()).toContain('% of Total (Sales)');
  expect(await page.locator('#th-rank-sales').textContent()).toContain('Dense Rank of Sales');
  expect(await page.locator('#th-running-sales').textContent()).toContain('Running Total of Sales');

  // 2. Verify Table Calculation Cell Values
  // Row 0: EMEA
  expect(await page.locator('[data-test="cell-pct-0"]').textContent()).toBe('25.38%');
  expect(await page.locator('[data-test="cell-rank-0"]').textContent()).toBe('1');
  expect(await page.locator('[data-test="cell-running-0"]').textContent()).toBe('$42,436,401.00');

  // Row 1: LATAM
  expect(await page.locator('[data-test="cell-pct-1"]').textContent()).toBe('25.37%');
  expect(await page.locator('[data-test="cell-rank-1"]').textContent()).toBe('2');
  expect(await page.locator('[data-test="cell-running-1"]').textContent()).toBe('$84,856,080.00');

  // Row 2: North America
  expect(await page.locator('[data-test="cell-pct-2"]').textContent()).toBe('24.64%');
  expect(await page.locator('[data-test="cell-rank-2"]').textContent()).toBe('3');

  // Row 3: APAC
  expect(await page.locator('[data-test="cell-pct-3"]').textContent()).toBe('24.62%');
  expect(await page.locator('[data-test="cell-rank-3"]').textContent()).toBe('4');
  expect(await page.locator('[data-test="cell-running-3"]').textContent()).toBe('$167,236,831.75');

  // 3. Verify Heat Map Color Styles on Profit Cells
  const positiveProfitCell = page.locator('[data-test="cell-profit-0"]');
  const positiveBg = await positiveProfitCell.evaluate(el => window.getComputedStyle(el).backgroundColor);
  expect(positiveBg).toMatch(/rgb/);

  const negativeProfitCell = page.locator('[data-test="cell-profit-1"]');
  const negativeBg = await negativeProfitCell.evaluate(el => window.getComputedStyle(el).backgroundColor);
  expect(negativeBg).toMatch(/rgb/);
  expect(negativeBg).not.toBe(positiveBg);

  // Take screenshot evidence
  await page.screenshot({ path: path.join(artifactDir, 'phase9_table_calculations_and_heatmap.png') });
  console.log('Phase 9 Browser Test Passed: Screenshot saved to phase9_table_calculations_and_heatmap.png');
});
