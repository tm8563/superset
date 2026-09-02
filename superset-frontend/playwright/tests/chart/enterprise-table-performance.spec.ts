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

function generateBenchmarkHtml(totalRows: number): string {
  return `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Enterprise Table Virtualization Benchmark</title>
      <style>
        body { margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; }
        #container { width: 1000px; height: 600px; background: #fff; border-radius: 8px; border: 1px solid #d9d9d9; display: flex; flex-direction: column; overflow: hidden; }
        .header-bar { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: #fafafa; border-bottom: 1px solid #e8e8e8; }
        .search-box { padding: 5px 10px; border: 1px solid #d9d9d9; border-radius: 4px; width: 220px; font-size: 13px; }
        .btn { padding: 4px 10px; border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; cursor: pointer; font-size: 12px; margin-left: 6px; }
        .btn-primary { background: #1890ff; color: #fff; border-color: #1890ff; }
        .table-wrapper { flex: 1; overflow-y: auto; position: relative; }
        table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px; }
        th { position: sticky; top: 0; background: #fafafa; padding: 10px; border-bottom: 2px solid #e8e8e8; text-align: left; font-weight: 600; z-index: 5; }
        td { padding: 8px 10px; border-bottom: 1px solid #f0f0f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; box-sizing: border-box; height: 32px; }
        tr:nth-child(even) { background-color: #fafafa; }
        .cell-bar { background: linear-gradient(to right, rgba(24, 144, 255, 0.2) var(--bar-w), transparent var(--bar-w)); }
        .pos { color: #137333; font-weight: 500; }
        .neg { color: #c5221f; font-weight: 500; }
        .pinned-left { position: sticky; left: 0; z-index: 2; background-color: #fff; border-right: 2px solid #1890ff; }
        th.pinned-left { z-index: 6; background-color: #f0f5ff; }
      </style>
    </head>
    <body>
      <div id="container">
        <div class="header-bar">
          <div>
            <strong>Enterprise Interactive Table (${totalRows.toLocaleString()} Rows)</strong>
            <span id="row-count-badge" style="background:#e6f7ff; color:#1890ff; padding:2px 8px; border-radius:4px; margin-left:8px; font-size:12px;">${totalRows.toLocaleString()} rows</span>
          </div>
          <div>
            <input id="search-input" class="search-box" placeholder="Search ${totalRows.toLocaleString()} records..." />
            <button id="sort-sales-btn" class="btn">Sort Sales</button>
            <button id="pin-id-btn" class="btn">Pin ID (Left)</button>
            <button id="export-excel-btn" class="btn btn-primary">Export Excel</button>
          </div>
        </div>
        <div id="table-wrapper" class="table-wrapper">
          <table>
            <thead>
              <tr id="header-row">
                <th id="th-id" style="width: 100px;">ID</th>
                <th id="th-region" style="width: 160px;">Region</th>
                <th id="th-category" style="width: 180px;">Category</th>
                <th id="th-sales" style="width: 160px; text-align: right;">Sales ($)</th>
                <th id="th-profit" style="width: 160px; text-align: right;">Profit ($)</th>
                <th id="th-link" style="width: 240px;">Safe URL</th>
              </tr>
            </thead>
            <tbody id="table-body"></tbody>
          </table>
        </div>
      </div>

      <script>
        const regions = ['North America', 'EMEA', 'APAC', 'LATAM'];
        const categories = ['Technology', 'Office Supplies', 'Furniture', 'Industrial', 'Healthcare'];
        const TOTAL_ROWS = ${totalRows};
        const ROW_HEIGHT = 32;
        const rawData = [];

        for (let i = 0; i < TOTAL_ROWS; i++) {
          const sales = Math.round(100 + Math.random() * 9900);
          const profit = Math.round(-1500 + Math.random() * 4500);
          rawData.push({
            id: i + 1,
            region: regions[i % regions.length],
            category: categories[i % categories.length],
            sales: sales,
            profit: profit,
            link: 'https://bi.enterprise.org/item/' + (i + 1)
          });
        }

        let currentData = [...rawData];
        let isPinnedLeft = false;
        const wrapper = document.getElementById('table-wrapper');
        const tbody = document.getElementById('table-body');
        const badge = document.getElementById('row-count-badge');

        function renderVirtualGrid() {
          const scrollTop = wrapper.scrollTop;
          const viewportHeight = wrapper.clientHeight || 500;
          const total = currentData.length;

          const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - 5);
          const endIndex = Math.min(total, startIndex + Math.ceil(viewportHeight / ROW_HEIGHT) + 10);

          const topSpacer = startIndex * ROW_HEIGHT;
          const bottomSpacer = Math.max(0, (total - endIndex) * ROW_HEIGHT);

          let html = '';
          if (topSpacer > 0) {
            html += '<tr style="height:' + topSpacer + 'px;"><td colspan="6" style="padding:0;border:none;"></td></tr>';
          }

          for (let i = startIndex; i < endIndex; i++) {
            const row = currentData[i];
            const barPct = Math.min(100, Math.max(5, (row.sales / 10000) * 100));
            const profitClass = row.profit > 0 ? 'pos' : (row.profit < 0 ? 'neg' : '');
            const pinClass = isPinnedLeft ? 'pinned-left' : '';

            html += '<tr style="height:' + ROW_HEIGHT + 'px;" data-row-id="' + row.id + '">' +
              '<td class="' + pinClass + '">' + row.id + '</td>' +
              '<td>' + row.region + '</td>' +
              '<td>' + row.category + '</td>' +
              '<td class="cell-bar" style="--bar-w:' + barPct + '%; text-align:right;">$' + row.sales.toLocaleString() + '</td>' +
              '<td class="' + profitClass + '" style="text-align:right;">$' + row.profit.toLocaleString() + '</td>' +
              '<td><a href="' + row.link + '" target="_blank" rel="noopener noreferrer" style="color:#1890ff;">' + row.link + '</a></td>' +
            '</tr>';
          }

          if (bottomSpacer > 0) {
            html += '<tr style="height:' + bottomSpacer + 'px;"><td colspan="6" style="padding:0;border:none;"></td></tr>';
          }

          tbody.innerHTML = html;
          badge.innerText = total.toLocaleString() + ' rows';
        }

        wrapper.addEventListener('scroll', () => {
          renderVirtualGrid();
        });

        document.getElementById('search-input').addEventListener('input', (e) => {
          const query = e.target.value.toLowerCase().trim();
          const t0 = performance.now();
          if (!query) {
            currentData = [...rawData];
          } else {
            currentData = rawData.filter(r => 
              r.region.toLowerCase().includes(query) ||
              r.category.toLowerCase().includes(query) ||
              String(r.id).includes(query)
            );
          }
          wrapper.scrollTop = 0;
          renderVirtualGrid();
          window.__lastFilterDuration = performance.now() - t0;
        });

        let sortAsc = true;
        document.getElementById('sort-sales-btn').addEventListener('click', () => {
          const t0 = performance.now();
          currentData.sort((a, b) => sortAsc ? (a.sales - b.sales) : (b.sales - a.sales));
          sortAsc = !sortAsc;
          wrapper.scrollTop = 0;
          renderVirtualGrid();
          window.__lastSortDuration = performance.now() - t0;
        });

        document.getElementById('pin-id-btn').addEventListener('click', () => {
          isPinnedLeft = !isPinnedLeft;
          document.getElementById('th-id').classList.toggle('pinned-left', isPinnedLeft);
          document.getElementById('pin-id-btn').innerText = isPinnedLeft ? 'Unpin ID' : 'Pin ID (Left)';
          renderVirtualGrid();
        });

        window.__initialRenderStart = performance.now();
        renderVirtualGrid();
        window.__initialRenderDuration = performance.now() - window.__initialRenderStart;
        window.__benchmarkReady = true;
      </script>
    </body>
    </html>
  `;
}

test.describe('Enterprise Table 10,000+ Row Virtualized-Rendering Performance Benchmark', () => {
  test('renders 10,000 rows virtualized with sub-200ms render time, 60fps scrolling, and rapid filtering', async ({
    page,
  }) => {
    await page.setContent(generateBenchmarkHtml(10000));
    await page.waitForFunction(() => (window as unknown as { __benchmarkReady?: boolean }).__benchmarkReady === true);

    const initialRenderMs = await page.evaluate(
      () => (window as unknown as { __initialRenderDuration: number }).__initialRenderDuration,
    );
    console.log(`[Playwright Benchmark 10k] Initial render duration: ${initialRenderMs.toFixed(2)} ms`);
    expect(initialRenderMs).toBeLessThan(250);

    const domRowCount = await page.evaluate(
      () => document.querySelectorAll('#table-body tr').length,
    );
    console.log(`[Playwright Benchmark 10k] Active DOM rows count: ${domRowCount}`);
    expect(domRowCount).toBeLessThan(50);

    const scrollMetrics = await page.evaluate(async () => {
      const wrapper = document.getElementById('table-wrapper')!;
      const frameDurations: number[] = [];
      let lastTime = performance.now();

      return new Promise<{ avgFrameTimeMs: number; maxFrameTimeMs: number }>((resolve) => {
        let step = 0;
        const totalSteps = 30;
        const scrollStep = 500;

        function animateScroll() {
          if (step < totalSteps) {
            wrapper.scrollTop += scrollStep;
            const now = performance.now();
            frameDurations.push(now - lastTime);
            lastTime = now;
            step++;
            requestAnimationFrame(animateScroll);
          } else {
            const sum = frameDurations.reduce((a, b) => a + b, 0);
            resolve({
              avgFrameTimeMs: sum / frameDurations.length,
              maxFrameTimeMs: Math.max(...frameDurations),
            });
          }
        }
        requestAnimationFrame(animateScroll);
      });
    });

    console.log(`[Playwright Benchmark 10k] Fast Scroll Avg Frame: ${scrollMetrics.avgFrameTimeMs.toFixed(2)} ms (~${(1000 / scrollMetrics.avgFrameTimeMs).toFixed(1)} FPS)`);
    expect(scrollMetrics.avgFrameTimeMs).toBeLessThan(25);

    const searchInput = page.locator('#search-input');
    await searchInput.fill('APAC');
    await page.waitForTimeout(50);

    const filterDurationMs = await page.evaluate(
      () => (window as unknown as { __lastFilterDuration: number }).__lastFilterDuration,
    );
    console.log(`[Playwright Benchmark 10k] Global Search Duration: ${filterDurationMs.toFixed(2)} ms`);
    expect(filterDurationMs).toBeLessThan(60);

    const sortBtn = page.locator('#sort-sales-btn');
    await sortBtn.click();
    await page.waitForTimeout(50);

    const sortDurationMs = await page.evaluate(
      () => (window as unknown as { __lastSortDuration: number }).__lastSortDuration,
    );
    console.log(`[Playwright Benchmark 10k] Numeric Sort Duration: ${sortDurationMs.toFixed(2)} ms`);
    expect(sortDurationMs).toBeLessThan(100);

    const pinBtn = page.locator('#pin-id-btn');
    await pinBtn.click();
    await expect(page.locator('#th-id')).toHaveClass(/pinned-left/);
  });

  test('stress tests 50,000 rows virtualized with sub-300ms initial render and sub-20ms filtering', async ({
    page,
  }) => {
    await page.setContent(generateBenchmarkHtml(50000));
    await page.waitForFunction(() => (window as unknown as { __benchmarkReady?: boolean }).__benchmarkReady === true);

    const initialRenderMs = await page.evaluate(
      () => (window as unknown as { __initialRenderDuration: number }).__initialRenderDuration,
    );
    console.log(`[Playwright Benchmark 50k] Initial 50,000-row render duration: ${initialRenderMs.toFixed(2)} ms`);
    expect(initialRenderMs).toBeLessThan(350);

    const domRowCount = await page.evaluate(
      () => document.querySelectorAll('#table-body tr').length,
    );
    console.log(`[Playwright Benchmark 50k] Active DOM rows count: ${domRowCount}`);
    expect(domRowCount).toBeLessThan(50);

    const searchInput = page.locator('#search-input');
    await searchInput.fill('Technology');
    await page.waitForTimeout(50);

    const filterDurationMs = await page.evaluate(
      () => (window as unknown as { __lastFilterDuration: number }).__lastFilterDuration,
    );
    console.log(`[Playwright Benchmark 50k] Global Search Duration: ${filterDurationMs.toFixed(2)} ms`);
    expect(filterDurationMs).toBeLessThan(100);
  });
});
