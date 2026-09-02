import { chromium } from 'playwright';
import * as path from 'path';
import * as fs from 'fs';

async function run() {
  const artifactDir = '/home/bi-tool-ryobilao/.gemini/antigravity-ide/brain/9773d874-d5f7-4827-b313-6e91a93935a5';
  fs.mkdirSync(artifactDir, { recursive: true });

  const consoleErrors = [];
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

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
  await page.goto('http://localhost:8088/login/', { waitUntil: 'networkidle' });
  await page.screenshot({ path: path.join(artifactDir, '01_login_page.png') });

  console.log('2. Logging in as admin...');
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin');
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle' }),
    page.click('input[type="submit"]'),
  ]);

  console.log(`Current URL after login: ${page.url()}`);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(artifactDir, '02_welcome_page.png') });

  console.log('3. Navigating to chart creation page...');
  await page.goto('http://localhost:8088/chart/add', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(artifactDir, '03_chart_creation_page.png') });

  // Open dataset dropdown or chart picker
  const chooseDatasetBtn = page.locator('span.ant-select-selection-search input, .ant-select-selector').first();
  if (await chooseDatasetBtn.isVisible()) {
    console.log('Clicking dataset selector...');
    await chooseDatasetBtn.click();
    await page.waitForTimeout(500);
    // pick first dataset item
    const firstOption = page.locator('.ant-select-item-option').first();
    if (await firstOption.isVisible()) {
      await firstOption.click();
      await page.waitForTimeout(1000);
    }
  }

  // Click on chart type gallery picker
  const chartTypeCard = page.locator('.chart-type-card, [data-test="viz-type-select"], .control-label:has-text("Chart Type") + div, div:has-text("Choose a visualization type")').first();
  if (await chartTypeCard.isVisible()) {
    console.log('Opening chart gallery picker...');
    await chartTypeCard.click();
    await page.waitForTimeout(1500);
  }

  await page.screenshot({ path: path.join(artifactDir, '04_chart_picker_gallery.png') });

  const pageContent = await page.content();
  console.log(`Chart page title: ${await page.title()}`);

  const moduleErrors = consoleErrors.filter(e => e.includes('Cannot find module') || e.includes('thumbnail.png'));
  console.log(`Cannot find module errors count: ${moduleErrors.length}`);

  const hasEnterpriseTable = pageContent.includes('Enterprise Interactive Table') ||
                             pageContent.includes('enterprise_table');
  console.log(`Has 'Enterprise Interactive Table' in page DOM: ${hasEnterpriseTable}`);

  await browser.close();

  console.log('SUCCESS: Browser verification complete.');
}

run().catch(err => {
  console.error('FAILED:', err);
  process.exit(1);
});
