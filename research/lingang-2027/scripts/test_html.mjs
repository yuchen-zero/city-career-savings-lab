import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { pathToFileURL, fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const htmlPath = path.join(root, "output", "2027届_电气工程及其自动化_临港_参数化测算_2026-10-26.html");
const payloadBytes = await fs.readFile(path.join(root, "data", "analysis_payload.json"));
const payload = JSON.parse(payloadBytes.toString("utf8"));
const manifest = JSON.parse(await fs.readFile(path.join(root, "data", "build_manifest.json"), "utf8"));
const payloadHash = crypto.createHash("sha256").update(payloadBytes).digest("hex");
if (payloadHash !== manifest.payload_sha256) throw new Error(`payload 指纹不一致: ${payloadHash} != ${manifest.payload_sha256}`);
const qaDir = path.join(root, "output", "_html_qa");
await fs.rm(qaDir, { recursive: true, force: true });
await fs.mkdir(qaDir, { recursive: true });
const chromiumPath = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const browser = await chromium.launch({ headless: true, executablePath: chromiumPath });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
const errors = [];
page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
page.on("pageerror", (error) => errors.push(error.message));
await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "load" });
await page.waitForFunction(() => document.querySelector("#cashValue")?.textContent !== "—");
const defaultValues = await page.evaluate(() => ({
  cash: document.querySelector("#cashValue").textContent,
  net: document.querySelector("#netValue").textContent,
  first: document.querySelector("#firstValue").textContent,
  reserve: document.querySelector("#reserveValue").textContent,
  burden: document.querySelector("#burdenValue").textContent,
  error: document.querySelector("#error").textContent,
  rows: document.querySelectorAll("#scenarioRows tr").length,
}));
if (defaultValues.error) throw new Error(`默认值出现校验错误: ${defaultValues.error}`);
if (defaultValues.rows !== 5) throw new Error(`预期5行情景，实际${defaultValues.rows}`);
if (!defaultValues.cash.includes("8,197.50")) throw new Error(`默认税后现金不符: ${defaultValues.cash}`);
if (!defaultValues.first.includes("8,361")) throw new Error(`默认首月现金不符: ${defaultValues.first}`);
const footerText = await page.locator("footer").textContent();
if (!footerText.includes(manifest.payload_sha256)) throw new Error("页面未嵌入当前 payload 指纹");
await page.screenshot({ path: path.join(qaDir, "desktop-default.png"), fullPage: true });

const parseMoney = (value) => Number(value.replace(/[^\d.-]/g, ""));
const salaryChecks = [];
for (const salary of [8000, 10000, 12000, 15000]) {
  await page.fill("#salary", String(salary));
  await page.waitForTimeout(80);
  const actualText = await page.locator("#cashValue").textContent();
  const actual = parseMoney(actualText);
  const expected = payload.payroll_examples[String(salary)].monthly_cash;
  if (Math.abs(actual - expected) > 0.011) throw new Error(`${salary}元月均到手现金不符: ${actualText} vs ${expected}`);
  salaryChecks.push({ salary, actual, expected });
}
await page.fill("#salary", "10000");
await page.waitForTimeout(80);

await page.selectOption("#months", "13");
await page.selectOption("#fundRate", "0.07");
await page.waitForTimeout(100);
const months13Cash = parseMoney(await page.locator("#cashValue").textContent());
if (Math.abs(months13Cash - 9005.833333333333) > 0.011) throw new Error(`13薪到手现金不符: ${months13Cash}`);

await page.selectOption("#months", "16");
await page.waitForTimeout(100);
const months16Cash = parseMoney(await page.locator("#cashValue").textContent());
if (Math.abs(months16Cash - 11285) > 0.011) throw new Error(`16薪到手现金不符: ${months16Cash}`);

await page.selectOption("#months", "12");
await page.selectOption("#fundRate", "0.05");
await page.waitForTimeout(100);
const fund5Cash = parseMoney(await page.locator("#cashValue").textContent());
if (Math.abs(fund5Cash - 8391.5) > 0.011) throw new Error(`5%公积金到手现金不符: ${fund5Cash}`);

await page.selectOption("#fundRate", "0.07");
await page.waitForTimeout(80);

await page.selectOption("#preset", "whole-agency");
await page.selectOption("#months", "13");
await page.selectOption("#fundRate", "0.05");
await page.waitForTimeout(100);
const changedValues = await page.evaluate(() => ({
  cash: document.querySelector("#cashValue").textContent,
  net: document.querySelector("#netValue").textContent,
  first: document.querySelector("#firstValue").textContent,
  error: document.querySelector("#error").textContent,
}));
if (changedValues.error) throw new Error(`切换参数后出现错误: ${changedValues.error}`);

await page.fill("#salary", "");
await page.waitForTimeout(80);
const blankError = await page.locator("#error").isVisible();
if (!blankError) throw new Error("空工资未显示错误");
await page.fill("#salary", "37731");
await page.fill("#rent", "0");
await page.waitForTimeout(80);
const zeroRentError = await page.locator("#error").isVisible();
if (!zeroRentError) throw new Error("零租金属包住场景未提示如何处理");
await page.fill("#rent", "2200");
await page.fill("#salary", "1000000");
await page.selectOption("#months", "16");
await page.waitForTimeout(100);
if (await page.locator("#error").isVisible()) throw new Error("极大工资边界仍报错");

const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
if (overflow > 1) throw new Error(`桌面页面横向溢出 ${overflow}px`);
await browser.close();

const mobileBrowser = await chromium.launch({ headless: true, executablePath: chromiumPath });
const mobile = await mobileBrowser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const mobileErrors = [];
mobile.on("console", (message) => { if (message.type() === "error") mobileErrors.push(message.text()); });
mobile.on("pageerror", (error) => mobileErrors.push(error.message));
await mobile.goto(pathToFileURL(htmlPath).href, { waitUntil: "load" });
await mobile.waitForFunction(() => document.querySelector("#cashValue")?.textContent !== "—");
const mobileOverflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
if (mobileOverflow > 1) {
  const offenders = await mobile.evaluate(() => [...document.querySelectorAll("body *")]
    .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1)
    .map((el) => ({ tag:el.tagName, id:el.id, cls:el.className, right:Math.round(el.getBoundingClientRect().right), width:Math.round(el.getBoundingClientRect().width), scrollWidth:el.scrollWidth }))
    .slice(0, 20));
  console.log(JSON.stringify({ mobileOverflow, offenders }, null, 2));
  throw new Error(`手机页面横向溢出 ${mobileOverflow}px`);
}
await mobile.screenshot({ path: path.join(qaDir, "mobile-default.png"), fullPage: true });
await mobileBrowser.close();
if (errors.length || mobileErrors.length) throw new Error(`浏览器错误: ${[...errors, ...mobileErrors].join(" | ")}`);
console.log(JSON.stringify({ payloadHash, salaryChecks, defaultValues, changedValues, overflow, mobileOverflow, qaDir }, null, 2));
