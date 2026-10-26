import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const project = path.resolve('C:/Users/askl1/Documents/ChatGPT/ChatGPT/lingang-ee-research');
const outDir = path.join(project, 'sources', 'raw', 'boss_smoke');
await fs.mkdir(outDir, { recursive: true });

const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
const context = browser.contexts()[0];
const pages = context.pages();
const page = pages[0] ?? (await context.newPage());

const target = 'https://www.zhipin.com/web/geek/job?city=101020100&query=%E7%94%B5%E6%B0%94%E5%B7%A5%E7%A8%8B%E5%B8%88';
await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(5000);

const bodyText = await page.locator('body').innerText();
const snapshot = {
  url: page.url(),
  title: await page.title(),
  bodyText: bodyText.slice(0, 30000),
  cards: await page.locator('.job-card-wrapper, .job-card-box, li.job-card-wrapper').count(),
  links: await page.locator('a[href*="/job_detail/"]').count(),
  htmlFile: path.join(outDir, 'search_page.html'),
  screenshotFile: path.join(outDir, 'search_page.png'),
};

await fs.writeFile(snapshot.htmlFile, await page.content(), 'utf8');
await page.screenshot({ path: snapshot.screenshotFile, fullPage: true });
await fs.writeFile(path.join(outDir, 'smoke.json'), JSON.stringify(snapshot, null, 2), 'utf8');

console.log(JSON.stringify({
  url: snapshot.url,
  title: snapshot.title,
  cards: snapshot.cards,
  links: snapshot.links,
  bodyPreview: snapshot.bodyText.slice(0, 1200),
}, null, 2));

await browser.close();
