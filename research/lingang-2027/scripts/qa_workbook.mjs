import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const xlsxPath = path.join(root, "output", "2027届_电气工程及其自动化_临港_数据总表_2026-10-26.xlsx");
const payload = JSON.parse(await fs.readFile(path.join(root, "data", "analysis_payload.json"), "utf8"));
const qaDir = path.join(root, "output", "_xlsx_render", "qa");
await fs.mkdir(qaDir, { recursive: true });

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(xlsxPath));
const sheetList = await workbook.inspect({ kind: "sheet", include: "id,name" });
await fs.writeFile(path.join(qaDir, "sheets.ndjson"), sheetList.ndjson || "", "utf8");

const expectedSheets = ["结论摘要", "税费计算", "住房预设", "生活假设", "净结余测算", "首月资金", "岗位明细", "岗位汇总", "房租样本", "官方规则", "生活成本", "证据台账"];
const sheetNameMatches = [...(sheetList.ndjson || "").matchAll(/"name":"([^"]+)"/g)].map((m) => m[1]);
if (JSON.stringify(sheetNameMatches) !== JSON.stringify(expectedSheets)) throw new Error(`工作表名称或顺序不符: ${sheetNameMatches.join("|")}`);

const summary = workbook.worksheets.getItem("结论摘要");
const tax = workbook.worksheets.getItem("税费计算");
const housing = workbook.worksheets.getItem("住房预设");
const life = workbook.worksheets.getItem("生活假设");
const net = workbook.worksheets.getItem("净结余测算");
const first = workbook.worksheets.getItem("首月资金");
const jobs = workbook.worksheets.getItem("岗位明细");
const family = workbook.worksheets.getItem("岗位汇总");

workbook.recalculate();
const close = (actual, expected, tolerance = 0.02) => Math.abs(actual - expected) <= tolerance;
const taxSamples = tax.getRange("J32:J35").values.flat();
const expectedTax = [8000, 10000, 12000, 15000].map((salary) => payload.payroll_examples[String(salary)].monthly_cash);
if (!taxSamples.every((value, i) => close(value, expectedTax[i]))) throw new Error(`税费样例不符: ${taxSamples} vs ${expectedTax}`);

const defaultHousing = housing.getRange("B3").values[0][0];
if (defaultHousing !== 2) throw new Error(`默认住房情景应为2，实际${defaultHousing}`);
const defaultCash = net.getRange("D4").values[0][0];
const defaultNet = net.getRange("N4").values[0][0];
const defaultFund = net.getRange("O4").values[0][0];
const defaultFirst = first.getRange("B15").values[0][0];
const defaultReserve = first.getRange("B16").values[0][0];
if (!close(defaultCash, 8197.5)) throw new Error(`默认到手现金不符: ${defaultCash}`);
if (!close(defaultNet, 4153.677333333333)) throw new Error(`默认现金净结余不符: ${defaultNet}`);
if (!close(defaultFund, 4853.677333333333)) throw new Error(`默认含公积金结余不符: ${defaultFund}`);
if (!close(defaultFirst, 8360.9)) throw new Error(`默认首月现金不符: ${defaultFirst}`);
if (!close(defaultReserve, 10360.9)) throw new Error(`默认建议储备不符: ${defaultReserve}`);

if (summary.getRange("B13").values[0][0] !== 0) throw new Error("公开薪资岗位数应保持为0");
if (summary.getRange("B16").values[0][0] !== 0) throw new Error("薪资、双休、不出差同时命中数应保持为0");
if (summary.getRange("B17").values[0][0] !== 10000) throw new Error("摘要税前月薪未正确联动");
const coreRows = family.getRange("A6:H10").values.filter((row) => typeof row[1] === "number" && row[1] > 0);
if (!coreRows.length || coreRows.some((row) => row[3] !== 0)) throw new Error(`岗位族公开薪资数异常: ${JSON.stringify(coreRows)}`);
const includedJobs = jobs.getRange("R6:R19").values.flat().filter((value) => value === "yes").length;
if (includedJobs !== 6) throw new Error(`纳入核心分析岗位数应为6，实际${includedJobs}`);
const jobAnnualized = jobs.getRange("Z6:Z19").values.flat();
const expectedJobAnnualized = payload.jobs.map((job) => job.monthly_min === "" ? null : ((job.monthly_min + job.monthly_max) / 2) * job.annual_months / 12);
if (!jobAnnualized.every((value, i) => expectedJobAnnualized[i] === null ? (value === null || value === "") : close(value, expectedJobAnnualized[i], 0.011))) {
  throw new Error(`岗位明细年化月薪中点不符: ${jobAnnualized} vs ${expectedJobAnnualized}`);
}

const anchors = payload.jobs.filter((job) => job.include_in_analysis === "no" && job.monthly_min !== "");
const expectedAnchors = anchors.map((job) => ((job.monthly_min + job.monthly_max) / 2) * job.annual_months / 12);
const anchorLabels = family.getRange("A1:A40").values.flat().map((value) => String(value ?? ""));
const anchorTitleIndex = anchorLabels.findIndex((value) => value.includes("排除样本中的市场锚点"));
if (anchorTitleIndex < 0) throw new Error("未找到岗位汇总中的市场锚点区");
const anchorTitleRow = anchorTitleIndex + 1;
const anchorValues = family.getRange(`E${anchorTitleRow + 2}:E${anchorTitleRow + 1 + anchors.length}`).values.flat();
if (anchors.length !== 7) throw new Error(`市场锚点应为7条，实际${anchors.length}`);
if (anchorValues.length !== expectedAnchors.length || !anchorValues.every((value, i) => close(value, expectedAnchors[i], 0.011))) {
  throw new Error(`市场锚点年化月薪中点公式不符: ${anchorValues} vs ${expectedAnchors}`);
}
const anchorMin = Math.min(...expectedAnchors);
const anchorMedian = [...expectedAnchors].sort((a, b) => a - b)[Math.floor(expectedAnchors.length / 2)];
const anchorMax = Math.max(...expectedAnchors);
if (!close(anchorMin, payload.headline.market_annualized_mid_min) ||
    !close(anchorMedian, payload.headline.market_annualized_mid_median) ||
    !close(anchorMax, payload.headline.market_annualized_mid_max)) {
  throw new Error(`市场锚点汇总与payload不一致: ${anchorMin}/${anchorMedian}/${anchorMax}`);
}

const housingResults = [];
housing.getRange("B3").values = [[1]];
for (let index = 1; index <= 5; index += 1) {
  housing.getRange("B3").values = [[index]];
  workbook.recalculate();
  const netValue = net.getRange("N4").values[0][0];
  const firstValue = net.getRange("Q4").values[0][0];
  housingResults.push({ index, net: netValue, first: firstValue });
}
const expectedHousing = [4291.6, 4153.683333333333, 3229.266666666667, 3165.093333333333, 3909.266666666667];
if (!housingResults.every((row, i) => close(row.net, expectedHousing[i]))) throw new Error(`住房切换结果不符: ${JSON.stringify(housingResults)}`);

housing.getRange("B3").values = [[2]];
tax.getRange("B10").values = [[0.05]];
workbook.recalculate();
const fund5Net = net.getRange("N4").values[0][0];
if (!close(fund5Net, 4347.683333333333, 0.1)) throw new Error(`5%公积金情景不符: ${fund5Net}`);

tax.getRange("B10").values = [[0.07]];
tax.getRange("B9").values = [[13]];
workbook.recalculate();
const months13Net = net.getRange("N4").values[0][0];
if (!close(months13Net, 4962.016666666667, 0.1)) throw new Error(`13薪情景不符: ${months13Net}`);

tax.getRange("B9").values = [[12]];
life.getRange("B3").values = [[1]];
workbook.recalculate();
const foodLowNet = net.getRange("N4").values[0][0];
if (!close(foodLowNet, 4753.683333333333, 0.1)) throw new Error(`低餐饮情景不符: ${foodLowNet}`);

life.getRange("B3").values = [[2]];
tax.getRange("B8").values = [[37731]];
workbook.recalculate();
const maxBaseCash = tax.getRange("B29").values[0][0];
if (!Number.isFinite(maxBaseCash) || maxBaseCash <= 0) throw new Error(`社保上限边界异常: ${maxBaseCash}`);

tax.getRange("B8").values = [[10000]];
workbook.recalculate();
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "exported workbook formula error scan",
});
await fs.writeFile(path.join(qaDir, "formula_errors.ndjson"), errors.ndjson || "", "utf8");
if (!(errors.ndjson || "").includes("Cell search matched 0 entries")) throw new Error(errors.ndjson);

const renderFiles = [];
for (const sheetName of expectedSheets) {
  const blob = await workbook.render({ sheetName, autoCrop: "all", scale: 1.4, format: "png" });
  const file = path.join(qaDir, `${sheetName.replace(/[\\/:*?"<>|]/g, "_")}.png`);
  await fs.writeFile(file, new Uint8Array(await blob.arrayBuffer()));
  renderFiles.push(file);
}

console.log(JSON.stringify({ taxSamples, defaultCash, defaultNet, defaultFund, defaultFirst, defaultReserve, housingResults, fund5Net, months13Net, foodLowNet, includedJobs, marketAnchors: { count: anchors.length, min: anchorMin, median: anchorMedian, max: anchorMax, values: expectedAnchors }, renderFiles }, null, 2));
