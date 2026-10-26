import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dataDir = path.join(root, "data");
const outputDir = path.join(root, "output");
const payload = JSON.parse(await fs.readFile(path.join(dataDir, "analysis_payload.json"), "utf8"));
const manifest = JSON.parse(await fs.readFile(path.join(dataDir, "build_manifest.json"), "utf8"));
const outputPath = path.join(outputDir, "2027届_电气工程及其自动化_临港_数据总表_2026-10-26.xlsx");
const renderDir = path.join(outputDir, "_xlsx_render");
await fs.mkdir(outputDir, { recursive: true });
await fs.rm(renderDir, { recursive: true, force: true });
await fs.mkdir(renderDir, { recursive: true });

const font = "Microsoft YaHei";
const colors = {
  ink: "#1F2937", muted: "#5B6573", navy: "#17365D", navy2: "#244B75",
  paleBlue: "#DCEAF7", paleGray: "#F3F5F7", paleAmber: "#FFF2CC",
  border: "#D8DEE5", white: "#FFFFFF", green: "#E2F0D9", red: "#FCE8E6", redText: "#B91C1C",
};

const workbook = Workbook.create();
const names = ["结论摘要", "税费计算", "住房预设", "生活假设", "净结余测算", "首月资金", "岗位明细", "岗位汇总", "房租样本", "官方规则", "生活成本", "证据台账"];
const sheets = Object.fromEntries(names.map((name) => [name, workbook.worksheets.add(name)]));
for (const sheet of Object.values(sheets)) sheet.showGridLines = false;
console.log("WORKBOOK_READY");

function range(sheetName, address) { return sheets[sheetName].getRange(address); }
function setTitle(sheetName, address, text, span = 6) {
  const r = range(sheetName, address);
  r.values = [[text]];
  r.format.font = { name: font, size: 14, bold: true, color: colors.ink };
  r.format.horizontalAlignment = "left";
  r.format.verticalAlignment = "center";
  r.format.rowHeight = 28;
  const row = Number(address.slice(1)) + 1;
  const rule = range(sheetName, `${address[0]}${row}:${String.fromCharCode(address.charCodeAt(0) + span - 1)}${row}`);
  rule.format.fill = colors.navy;
  rule.format.rowHeight = 3;
}
function writeMeta(sheetName, startRow, items) {
  const rows = items.map(([k, v]) => [k, v]);
  const r = range(sheetName, `A${startRow}:B${startRow + rows.length - 1}`);
  r.values = rows;
  r.format.font = { name: font, size: 10, color: colors.ink };
  r.format.verticalAlignment = "center";
  r.format.wrapText = true;
  range(sheetName, `A${startRow}:A${startRow + rows.length - 1}`).format.font = { name: font, size: 10, bold: true, color: colors.muted };
}
function headerRow(sheetName, address, values) {
  const r = range(sheetName, address);
  r.values = [values];
  r.format.fill = colors.navy;
  r.format.font = { name: font, size: 10, bold: true, color: colors.white };
  r.format.horizontalAlignment = "center";
  r.format.verticalAlignment = "center";
  r.format.wrapText = true;
  r.format.rowHeight = 32;
}
function tableBody(sheetName, address, rows) {
  if (!rows.length) return;
  const r = range(sheetName, address);
  r.values = rows;
  r.format.font = { name: font, size: 9.5, color: colors.ink };
  r.format.verticalAlignment = "center";
  r.format.wrapText = true;
  const start = Number(address.match(/[A-Z]+(\d+)/)[1]);
  const endCol = address.split(":")[1].match(/[A-Z]+/)[0];
  for (let i = 0; i < rows.length; i += 1) {
    range(sheetName, `${address[0]}${start + i}:${endCol}${start + i}`).format.fill = i % 2 ? colors.paleGray : colors.white;
  }
}
function setWidths(sheetName, widths) {
  widths.forEach((width, index) => {
    const col = columnName(index + 1);
    range(sheetName, `${col}1:${col}1`).format.columnWidth = width;
  });
}
function columnName(n) {
  let out = "";
  while (n > 0) { const x = (n - 1) % 26; out = String.fromCharCode(65 + x) + out; n = Math.floor((n - 1) / 26); }
  return out;
}
function money(sheetName, address) { range(sheetName, address).format.numberFormat = '"¥"#,##0.00'; }
function number(sheetName, address) { range(sheetName, address).format.numberFormat = '#,##0'; }
function percent(sheetName, address) { range(sheetName, address).format.numberFormat = '0.0%'; }
function applyBox(sheetName, address) {
  range(sheetName, address).format.borders = { preset: "all", style: "thin", color: colors.border };
}
function note(sheetName, address, text, height = 58) {
  const r = range(sheetName, address);
  r.values = [[text]];
  r.format.font = { name: font, size: 9, italic: true, color: colors.muted };
  r.format.wrapText = true;
  r.format.verticalAlignment = "top";
  r.format.rowHeight = height;
}

// 结论摘要
setTitle("结论摘要", "A2", "2027届电气工程及其自动化本科应届生临港调研结论摘要", 9);
writeMeta("结论摘要", 4, [
  ["研究范围", "上海市浦东新区临港新片区，重点滴水湖与南汇新城核心区"],
  ["数据截止日", payload.meta.data_cutoff],
  ["数据版本", payload.meta.data_version],
  ["数据指纹", manifest.payload_sha256.slice(0, 16)],
]);
range("结论摘要", "A9").values = [["核心判断"]];
range("结论摘要", "B9").values = [["当前可核验的2027届本科相邻岗位为6条、3家企业，公开薪资、明确双休、明确不出差均为0条；不能用8千至1.5万元压力测试冒充真实应届工资。"]];
range("结论摘要", "A9:J9").format = { font: { name: font, size: 10, bold: true, color: colors.ink }, verticalAlignment: "center" };
range("结论摘要", "B9").format.wrapText = false;
range("结论摘要", "A9:J9").format.rowHeight = 30;
headerRow("结论摘要", "A11:B11", ["关键指标", "当前结果"]);
const summaryRows = [
  ["有效岗位 / 企业", "=COUNTIF('岗位明细'!$R$6:$R$24,\"yes\")&\" 条 / 3 家企业\""],
  ["公开薪资岗位", "=COUNTIFS('岗位明细'!$R$6:$R$24,\"yes\",'岗位明细'!$AA$6:$AA$24,1)"],
  ["明确双休", "=COUNTIFS('岗位明细'!$R$6:$R$24,\"yes\",'岗位明细'!$U$6:$U$24,\"double\")"],
  ["明确不出差", "=COUNTIFS('岗位明细'!$R$6:$R$24,\"yes\",'岗位明细'!$V$6:$V$24,\"none\")"],
  ["同时满足公开薪资+双休+不出差", "=COUNTIFS('岗位明细'!$R$6:$R$24,\"yes\",'岗位明细'!$AA$6:$AA$24,1,'岗位明细'!$U$6:$U$24,\"double\",'岗位明细'!$V$6:$V$24,\"none\")"],
  ["当前税前月薪输入", "='税费计算'!$B$8"],
  ["月均到手现金", "='税费计算'!$B$29"],
  ["当前住房情景", "='住房预设'!$B$3"],
  ["月净结余（纯现金）", "='净结余测算'!$N$4"],
  ["月净结余（含个人公积金）", "='净结余测算'!$O$4"],
  ["房租收入比", "='净结余测算'!$P$4"],
  ["首月最低现金", "='净结余测算'!$Q$4"],
  ["建议储备（含2,000元缓冲）", "='净结余测算'!$R$4"],
];
tableBody("结论摘要", `A12:B${11 + summaryRows.length}`, summaryRows);
applyBox("结论摘要", `A11:B${11 + summaryRows.length}`);
money("结论摘要", "B17:B18"); money("结论摘要", "B20:B21"); money("结论摘要", "B23:B24"); percent("结论摘要", "B22");
note("结论摘要", "D26", "证据等级：岗位与租金为C级小样本；官方社保、公积金和统计规则为A级。房租是挂牌/展示价，不是成交价。", 86);
note("结论摘要", "D29", "结论何时不成立：若获得更多目标岗位、真实工资单、双休与出差筛选结果，或租金成交数据，当前观察会改变。", 90);
setWidths("结论摘要", [31, 22, 2, 22, 22, 22]);
console.log("SHEET_SUMMARY_OK");

// 税费计算
setTitle("税费计算", "A2", "税前工资、上海社保公积金与个人所得税测算", 10);
writeMeta("税费计算", 4, [["数据截止日", payload.meta.data_cutoff], ["规则口径", "2026年上海社保、公积金与居民综合所得年度税率"]])
headerRow("税费计算", "A7:B7", ["可编辑输入", "当前值"]);
range("税费计算", "A8:A12").values = [["税前固定月薪"], ["年发月数"], ["个人公积金比例"], ["租房专项附加扣除（月）"], ["租期（月）"]];
range("税费计算", "B8:B12").values = [[10000], [12], [0.07], [1500], [12]];
applyBox("税费计算", "A7:B12");
range("税费计算", "B8:B12").format.fill = colors.paleAmber;
money("税费计算", "B8"); money("税费计算", "B11"); percent("税费计算", "B10");
range("税费计算", "B9:B12").format.font = { name: font, size: 10, color: colors.ink };
sheets["税费计算"].dataValidations.add({ range: "B9", rule: { type: "list", values: ["12", "13", "16"] } });
sheets["税费计算"].dataValidations.add({ range: "B10", rule: { type: "list", values: ["5%", "7%"] } });

headerRow("税费计算", "D7:E7", ["官方规则参数", "当前值"]);
range("税费计算", "D8:D15").values = [["社保基数下限"], ["社保基数上限"], ["公积金基数下限"], ["公积金基数上限"], ["个人社保比例"], ["年度基本减除费用"], ["税率表"], ["口径说明"]];
range("税费计算", "E8:E15").values = [[7546], [37731], [2740], [37731], [0.105], [60000], ["居民综合所得年度税率表"], ["不含补充公积金、单位公积金和未申报专项扣除"]];
applyBox("税费计算", "D7:E15");
range("税费计算", "E8:E13").format.fill = colors.paleBlue;
money("税费计算", "E8:E11"); percent("税费计算", "E12"); money("税费计算", "E13");
range("税费计算", "E14:E15").format.wrapText = true;

headerRow("税费计算", "A18:B18", ["计算步骤", "结果"]);
const taxBuild = [
  ["社保缴费基数", "=MIN(MAX(B8,$E$8),$E$9)"],
  ["公积金缴费基数", "=MIN(MAX(B8,$E$10),$E$11)"],
  ["个人社保月扣款", "=B19*$E$12"],
  ["个人公积金月缴额", "=B20*B10"],
  ["年度税前收入", "=B8*B9"],
  ["年度个人社保", "=B21*12"],
  ["年度个人公积金", "=B22*12"],
  ["年度应纳税所得额", "=MAX(0,B23-B24-B25-$E$13-B11*12)"],
  ["年度个人所得税", "=IF(B26<=36000,B26*0.03,IF(B26<=144000,B26*0.1-2520,IF(B26<=300000,B26*0.2-16920,IF(B26<=420000,B26*0.25-31920,IF(B26<=660000,B26*0.3-52920,IF(B26<=960000,B26*0.35-85920,B26*0.45-181920))))))"],
  ["年度现金收入", "=B23-B24-B25-B27"],
  ["月均到手现金", "=B28/12"],
];
tableBody("税费计算", "A19:B29", taxBuild);
applyBox("税费计算", "A18:B29");
money("税费计算", "B19:B21"); money("税费计算", "B22"); money("税费计算", "B23:B29");
range("税费计算", "B18:B29").format.fill = colors.paleBlue;

headerRow("税费计算", "A31:J31", ["税前月薪", "年发月数", "社保基数", "公积金基数", "个人社保/月", "个人公积金/月", "年税前", "年应税所得", "年个税", "月均到手现金"]);
const salaryInputs = [8000, 10000, 12000, 15000];
range("税费计算", "A32:A35").values = salaryInputs.map((x) => [x]);
range("税费计算", "B32:B35").values = salaryInputs.map(() => [12]);
const sampleFormulas = salaryInputs.map((_, i) => {
  const r = 32 + i;
  return [
    `=MIN(MAX(A${r},$E$8),$E$9)`,
    `=MIN(MAX(A${r},$E$10),$E$11)`,
    `=C${r}*$E$12`,
    `=D${r}*$B$10`,
    `=A${r}*B${r}`,
    `=MAX(0,G${r}-E${r}*12-F${r}*12-$E$13-$B$11*12)`,
    `=IF(H${r}<=36000,H${r}*0.03,IF(H${r}<=144000,H${r}*0.1-2520,IF(H${r}<=300000,H${r}*0.2-16920,IF(H${r}<=420000,H${r}*0.25-31920,IF(H${r}<=660000,H${r}*0.3-52920,IF(H${r}<=960000,H${r}*0.35-85920,H${r}*0.45-181920))))))`,
    `=(G${r}-E${r}*12-F${r}*12-I${r})/12`,
  ];
});
range("税费计算", "C32:J35").formulas = sampleFormulas;
applyBox("税费计算", "A31:J35");
money("税费计算", "A32:A35"); money("税费计算", "C32:J35"); percent("税费计算", "J32:J35");
range("税费计算", "J32:J35").format.numberFormat = '"¥"#,##0.00';
note("税费计算", "L17", "计算顺序固定：先以固定月薪计算年度收入，再比较基数上下限。绩效、奖金、单位公积金和补充公积金未计；实际工资单需以HR口径覆盖。", 76);
note("税费计算", "L37", "8千、1万、1.2万和1.5万元只是压力测试输入，不是2027目标岗位的观测工资。", 62);
setWidths("税费计算", [23, 14, 14, 22, 16, 15, 15, 15, 14, 17, 2, 48]);
console.log("SHEET_TAX_OK");

// 住房预设
setTitle("住房预设", "A2", "住房、押付与渠道费的五个可比情景", 14);
range("住房预设", "A3").values = [["当前情景选择（1-5）"]];
range("住房预设", "B3").values = [[2]];
range("住房预设", "D3").values = [["当前情景名称"]];
range("住房预设", "E3").formulas = [["=INDEX(A6:A10,B3)"]];
applyBox("住房预设", "A3:B3");
range("住房预设", "A3:N3").format.fill = colors.paleBlue;
range("住房预设", "A3:N3").format.font = { name: font, size: 10, bold: true, color: colors.ink };
range("住房预设", "B3").format.fill = colors.paleAmber;
range("住房预设", "B3").format.font = { name: font, size: 12, bold: true, color: colors.ink };
range("住房预设", "B3").format.horizontalAlignment = "center";
range("住房预设", "A3:N3").format.rowHeight = 30;
sheets["住房预设"].dataValidations.add({ range: "B3", rule: { type: "list", values: ["1", "2", "3", "4", "5"] } });
headerRow("住房预设", "A5:N5", ["情景", "月租", "押金月数", "预付月数", "中介费月数", "月度服务费", "一次性服务费", "水费/月", "电费/月", "燃气/月", "网络/月", "通勤/月", "住房证据", "口径与备注"]);
const housingRows = [
  ["1 合租-直租", 1200, 1, 1, 0, 0, 0, 16.2, 61.7, 18, 50, 160, "C", "合租观察区间1,100至1,500元取1,200元；直租不计中介费。"],
  ["2 合租-中介押一付三", 1300, 1, 3, 0.35, 0, 0, 16.2, 61.7, 18, 50, 160, "C", "合租上沿1,300元；押一付三并按0.35个月中介费做压力测试。"],
  ["3 整租-直租", 2200, 1, 1, 0, 0, 0, 16.2, 74.04, 18, 100, 160, "C", "平台一室展示价约2,200元；直租不计中介费，不含物业与品牌服务费。"],
  ["4 整租-中介押一付三", 2200, 1, 3, 0.35, 0, 0, 16.2, 74.04, 18, 100, 160, "C", "同一整租月租；押一付三和0.35个月中介费做敏感性。"],
  ["5 人才公寓-条件情景", 1500, 1, 1, 0, 0, 0, 16.2, 74.04, 18, 100, 180, "A", "官方项目一居1,000至1,800元取1,500元；资格、清单和空房需审核。"],
];
tableBody("住房预设", "A6:N10", housingRows);
applyBox("住房预设", "A5:N10");
money("住房预设", "B6:B10"); money("住房预设", "F6:G10"); money("住房预设", "H6:L10");
range("住房预设", "B6:G10").format.fill = colors.paleAmber;

headerRow("住房预设", "A13:B13", ["当前选择拆解", "结果"]);
const activeHousing = [
  ["当前情景名称", "=INDEX($A$6:$A$10,$B$3)"],
  ["月租", "=INDEX($B$6:$B$10,$B$3)"],
  ["押金月数", "=INDEX($C$6:$C$10,$B$3)"],
  ["预付租金月数", "=INDEX($D$6:$D$10,$B$3)"],
  ["中介费月数", "=INDEX($E$6:$E$10,$B$3)"],
  ["月度服务费", "=INDEX($F$6:$F$10,$B$3)"],
  ["一次性服务费", "=INDEX($G$6:$G$10,$B$3)"],
  ["水费/月", "=INDEX($H$6:$H$10,$B$3)"],
  ["电费/月", "=INDEX($I$6:$I$10,$B$3)"],
  ["燃气/月", "=INDEX($J$6:$J$10,$B$3)"],
  ["网络/月", "=INDEX($K$6:$K$10,$B$3)"],
  ["通勤/月", "=INDEX($L$6:$L$10,$B$3)"],
  ["住房证据等级", "=INDEX($M$6:$M$10,$B$3)"],
];
tableBody("住房预设", "A14:B26", activeHousing);
applyBox("住房预设", "A13:B26");
money("住房预设", "B15:B26"); money("住房预设", "B18:B19"); money("住房预设", "B20:B23");
for (let r = 14; r <= 26; r += 1) range("住房预设", `A${r}:B${r}`).format.rowHeight = 22;
range("住房预设", "A14:B14").format.rowHeight = 42;
note("住房预设", "P11", "这里列的是挂牌/展示和模型组合，不是成交合同。押一付三的预付租金=3个月；押金另计1个月。", 82);
note("住房预设", "P28", "人才公寓只适用于符合资格且有房源的申请人，不应作为无条件默认方案。", 62);
setWidths("住房预设", [25, 18, 11, 11, 12, 13, 14, 11, 11, 11, 11, 11, 11, 54, 2, 52]);
console.log("SHEET_HOUSING_OK");

// 生活假设
setTitle("生活假设", "A2", "餐饮、固定支出与首月缓冲假设", 9);
range("生活假设", "A3").values = [["当前餐饮档位（1-3）"]];
range("生活假设", "B3").values = [[2]];
range("生活假设", "D3").values = [["当前餐饮名称"]];
range("生活假设", "E3").formulas = [["=INDEX(A8:A10,B3)"]];
range("生活假设", "F3").values = [["当前餐饮月额"]];
range("生活假设", "G3").formulas = [["=INDEX(B8:B10,B3)"]];
applyBox("生活假设", "A3:B3");
range("生活假设", "A3:I3").format.fill = colors.paleBlue;
range("生活假设", "A3:I3").format.font = { name: font, size: 10, bold: true, color: colors.ink };
range("生活假设", "B3").format.fill = colors.paleAmber;
range("生活假设", "G3").format.fill = colors.paleAmber;
range("生活假设", "B3").format.horizontalAlignment = "center";
range("生活假设", "A3:I3").format.rowHeight = 30;
sheets["生活假设"].dataValidations.add({ range: "B3", rule: { type: "list", values: ["1", "2", "3"] } });
console.log("LIFE_SELECTOR_OK");
headerRow("生活假设", "A7:D7", ["餐饮篮子", "月额", "证据", "计算口径"]);
const foodRows = [
  ["1 食堂/自炊/低价混合", 1500, "C", "8元早餐+18元午餐+20元晚餐，按30日；不假定长期优惠券。"],
  ["2 堂食与外卖混合", 2100, "C", "70元/日，按30日；本表主情景。"],
  ["3 外卖高频", 2800, "C", "约93元/日；按单餐商品20至35元加配送包装2至9元。"],
];
tableBody("生活假设", "A8:D10", foodRows);
applyBox("生活假设", "A7:D10");
money("生活假设", "B8:B10"); money("生活假设", "G3");
headerRow("生活假设", "A13:B13", ["其他生活参数", "当前值"]);
const lifeInputs = [
  ["其他固定支出/月", 300],
  ["首月应急缓冲", 2000],
  ["其他一次性支出", 0],
  ["合租是否包含网络", "不含；另计50元/月"],
  ["外卖单餐全包观察区间", "22至44元"],
];
tableBody("生活假设", "A14:B18", lifeInputs);
applyBox("生活假设", "A13:B18");
range("生活假设", "B14:B16").format.fill = colors.paleAmber;
money("生活假设", "B14:B16");
range("生活假设", "A17:B18").format.rowHeight = 28;
note("生活假设", "D20", "餐饮是模型篮子，不是连续30天外卖账单。官方居民消费支出只作外部校验，不能直接替代单身青年餐费。", 84);
note("生活假设", "D22", "水、电、燃气和网络按整租/合租分别计入住房预设；手机、清洁和个人用品并入其他固定支出。", 66);
setWidths("生活假设", [26, 14, 12, 62, 18, 18, 14, 2, 52]);
console.log("SHEET_HOUSING_LIFE_OK");

// 首月资金先行，净结余表引用其汇总结果，避免重复计算
setTitle("首月资金", "A2", "五种住房情景的首月现金门槛", 16);
headerRow("首月资金", "A5:P5", ["情景", "月租", "押金现金", "预付租金", "中介费", "月度服务费", "一次性服务费", "水电气网", "餐饮", "通勤", "其他固定支出", "其他一次性支出", "首月最低现金", "应急缓冲", "建议储备", "证据"]);
const firstMonthFormulas = [];
for (let i = 0; i < 5; i += 1) {
  const r = 6 + i;
  const hr = 6 + i;
  firstMonthFormulas.push([
    `='住房预设'!A${hr}`,
    `='住房预设'!B${hr}`,
    `=B${r}*'住房预设'!C${hr}`,
    `=B${r}*'住房预设'!D${hr}`,
    `=B${r}*'住房预设'!E${hr}`,
    `='住房预设'!F${hr}`,
    `='住房预设'!G${hr}`,
    `=SUM('住房预设'!H${hr}:K${hr})`,
    `='生活假设'!G3`,
    `='住房预设'!L${hr}`,
    `='生活假设'!B14`,
    `='生活假设'!B16`,
    `=SUM(C${r}:L${r})`,
    `='生活假设'!B15`,
    `=M${r}+N${r}`,
    `='住房预设'!M${hr}`,
  ]);
}
range("首月资金", "A6:P10").formulas = firstMonthFormulas;
applyBox("首月资金", "A5:P10");
money("首月资金", "B6:O10");
for (let i = 0; i < 5; i += 1) range("首月资金", `A${6+i}:P${6+i}`).format.fill = i % 2 ? colors.paleGray : colors.white;
range("首月资金", "C6:E10").format.fill = colors.paleBlue;
range("首月资金", "M6:O10").format.fill = colors.green;
range("首月资金", "M6:O10").format.font = { name: font, size: 9.5, bold: true, color: colors.ink };
headerRow("首月资金", "A13:B13", ["当前选择", "结果"]);
range("首月资金", "A14:A16").values = [["当前情景"], ["首月最低现金"], ["建议储备（含缓冲）"]];
range("首月资金", "B14:B16").formulas = [
  ["=INDEX(A6:A10,'住房预设'!B3)"],
  ["=INDEX(M6:M10,'住房预设'!B3)"],
  ["=INDEX(O6:O10,'住房预设'!B3)"],
];
applyBox("首月资金", "A13:B16");
money("首月资金", "B15:B16");
range("首月资金", "A14:B14").format.rowHeight = 42;
note("首月资金", "R12", "首月现金含押金、预付租金、中介费、一次性服务费、当月水电气网、餐饮、通勤和固定支出；不是只付一个月房租。", 78);
note("首月资金", "R19", "应急缓冲是规划余量，不是所有人都足够。搬家、床品、厨具、体检和延迟发薪会进一步抬高门槛。", 78);
setWidths("首月资金", [28, 12, 13, 13, 12, 14, 15, 14, 12, 12, 15, 16, 16, 13, 18, 11, 2, 50]);

// 净结余测算
setTitle("净结余测算", "A2", "月均到手现金、净结余和首月资金联动测算", 18);
headerRow("净结余测算", "A3:R3", ["情景", "税前月薪", "年发月数", "月均到手现金", "月租", "中介费摊销", "月服务费", "水电气网", "餐饮", "通勤", "其他固定", "月经常性支出", "个人公积金/月", "现金净结余", "含公积金净结余", "房租收入比", "首月最低现金", "建议储备"]);
range("净结余测算", "A4:R4").formulas = [[
  "=INDEX('住房预设'!A6:A10,'住房预设'!B3)",
  "='税费计算'!B8",
  "='税费计算'!B9",
  "='税费计算'!B29",
  "=INDEX('住房预设'!B6:B10,'住房预设'!B3)",
  "=E4*INDEX('住房预设'!E6:E10,'住房预设'!B3)/'税费计算'!B12",
  "=INDEX('住房预设'!F6:F10,'住房预设'!B3)",
  "=SUM(INDEX('住房预设'!$H$6:$H$10,'住房预设'!$B$3),INDEX('住房预设'!$I$6:$I$10,'住房预设'!$B$3),INDEX('住房预设'!$J$6:$J$10,'住房预设'!$B$3),INDEX('住房预设'!$K$6:$K$10,'住房预设'!$B$3))",
  "='生活假设'!G3",
  "=INDEX('住房预设'!L6:L10,'住房预设'!B3)",
  "='生活假设'!B14",
  "=SUM(E4:K4)",
  "='税费计算'!B22",
  "=D4-L4",
  "=N4+M4",
  "=E4/B4",
  "=INDEX('首月资金'!M6:M10,'住房预设'!B3)",
  "=INDEX('首月资金'!O6:O10,'住房预设'!B3)",
]];
applyBox("净结余测算", "A3:R4");
range("净结余测算", "A4:R4").format.font = { name: font, size: 9.5, color: colors.ink };
money("净结余测算", "B4"); money("净结余测算", "D4:O4"); money("净结余测算", "Q4:R4"); percent("净结余测算", "P4");
range("净结余测算", "D4:O4").format.fill = colors.paleBlue;
range("净结余测算", "N4:O4").format.font = { name: font, size: 10, bold: true, color: colors.ink };

range("净结余测算", "A6").values = [["五类住房在同一工资与生活假设下的比较"]];
range("净结余测算", "A6").format.font = { name: font, size: 11, bold: true, color: colors.navy };
headerRow("净结余测算", "A7:R7", ["情景", "税前月薪", "年发月数", "月均到手现金", "月租", "中介费摊销", "月服务费", "水电气网", "餐饮", "通勤", "其他固定", "月经常性支出", "个人公积金/月", "现金净结余", "含公积金净结余", "房租收入比", "首月最低现金", "建议储备"]);
const scenarioFormulas = [];
for (let i = 0; i < 5; i += 1) {
  const r = 8 + i;
  const hr = 6 + i;
  scenarioFormulas.push([
    `='住房预设'!A${hr}`,
    `='税费计算'!$B$8`,
    `='税费计算'!$B$9`,
    `='税费计算'!$B$29`,
    `='住房预设'!B${hr}`,
    `=E${r}*'住房预设'!E${hr}/'税费计算'!$B$12`,
    `='住房预设'!F${hr}`,
    `=SUM('住房预设'!H${hr}:K${hr})`,
    `='生活假设'!$G$3`,
    `='住房预设'!L${hr}`,
    `='生活假设'!$B$14`,
    `=SUM(E${r}:K${r})`,
    `='税费计算'!$B$22`,
    `=D${r}-L${r}`,
    `=N${r}+M${r}`,
    `=E${r}/B${r}`,
    `='首月资金'!M${hr}`,
    `='首月资金'!O${hr}`,
  ]);
}
range("净结余测算", "A8:R12").formulas = scenarioFormulas;
applyBox("净结余测算", "A7:R12");
money("净结余测算", "B8:O12"); money("净结余测算", "Q8:R12"); percent("净结余测算", "P8:P12");
for (let i = 0; i < 5; i += 1) range("净结余测算", `A${8+i}:R${8+i}`).format.fill = i % 2 ? colors.paleGray : colors.white;
range("净结余测算", "N8:O12").format.font = { name: font, size: 9.5, bold: true, color: colors.ink };
range("净结余测算", "N8:N12").conditionalFormats.addCustom("=N8<0", { fill: colors.red, font: { bold: true, color: colors.redText } });
range("净结余测算", "P8:P12").conditionalFormats.addCustom("=P8>0.3", { fill: colors.paleAmber, font: { bold: true, color: colors.ink } });

range("净结余测算", "A15").values = [["税前月薪与年发月数敏感性（当前住房与生活参数）"]];
range("净结余测算", "A15").format.font = { name: font, size: 11, bold: true, color: colors.navy };
headerRow("净结余测算", "A16:F16", ["税前月薪", "年发月数", "月均到手现金", "现金净结余", "含公积金净结余", "房租收入比"]);
const salaryCases = [[8000,12],[10000,12],[12000,12],[15000,12],[10000,13],[10000,16]];
range("净结余测算", "A17:B22").values = salaryCases;
const salarySensitivity = salaryCases.map(([gross, months], i) => {
  const r = 17 + i;
  const social = `MIN(MAX(A${r},'税费计算'!$E$8),'税费计算'!$E$9)*'税费计算'!$E$12*12`;
  const fund = `MIN(MAX(A${r},'税费计算'!$E$10),'税费计算'!$E$11)*'税费计算'!$B$10*12`;
  const annualGross = `A${r}*B${r}`;
  const taxable = `MAX(0,${annualGross}-${social}-${fund}-'税费计算'!$E$13-'税费计算'!$B$11*12)`;
  const tax = `IF(${taxable}<=36000,${taxable}*0.03,IF(${taxable}<=144000,${taxable}*0.1-2520,IF(${taxable}<=300000,${taxable}*0.2-16920,IF(${taxable}<=420000,${taxable}*0.25-31920,IF(${taxable}<=660000,${taxable}*0.3-52920,IF(${taxable}<=960000,${taxable}*0.35-85920,${taxable}*0.45-181920))))))`;
  return [
    `=(${annualGross}-${social}-${fund}-${tax})/12`,
    `=C${r}-'净结余测算'!$L$4`,
    `=D${r}+MIN(MAX(A${r},'税费计算'!$E$10),'税费计算'!$E$11)*'税费计算'!$B$10`,
    `='净结余测算'!$E$4/A${r}`,
  ];
});
range("净结余测算", "C17:F22").formulas = salarySensitivity;
applyBox("净结余测算", "A16:F22");
money("净结余测算", "A17:A22"); money("净结余测算", "C17:E22"); percent("净结余测算", "F17:F22");
note("净结余测算", "A25", "所有结果都由税费计算、住房预设和生活假设联动。当前工资是可编辑压力测试输入，不是招聘广告观测值。", 84);
note("净结余测算", "A27", "净结余不等同于可支配现金的永久承诺；绩效、奖金、单位公积金、医疗、旅行和家庭支持未自动计入。", 76);
setWidths("净结余测算", [28, 12, 11, 16, 11, 14, 12, 12, 11, 11, 11, 16, 15, 15, 17, 12, 16, 18, 2, 52]);
console.log("SHEET_NET_FIRST_OK");

// 岗位明细
setTitle("岗位明细", "A2", "临港电气、自动化与设备岗位明细及筛选记录", 28);
headerRow("岗位明细", "A5:AA5", ["职位ID", "来源", "原始URL", "采集日", "查询词", "城市", "区县", "公司", "职位", "岗位族", "月薪下限", "月薪上限", "年发月数", "薪资原文", "学历", "经验", "薪资类型", "纳入核心分析", "排除原因", "证据", "双休", "出差", "住宿", "关键备注", "月薪中点", "年化中点/月", "公开薪资标记"]);
function dateValue(v) { return /^\d{4}-\d{2}-\d{2}$/.test(v || "") ? new Date(`${v}T00:00:00+08:00`) : v; }
function numeric(v) { return v === "" || v === null || v === undefined ? null : Number(v); }
const jobRows = payload.jobs.map((job) => [
  job.job_id, job.source, job.source_url, dateValue(job.collected_at), job.search_keyword, job.city, job.district,
  job.company, job.job_title, job.job_family, numeric(job.monthly_min), numeric(job.monthly_max), numeric(job.annual_months), job.salary_text,
  job.education, job.experience, job.salary_type, job.include_in_analysis, job.exclusion_reason, job.evidence_level,
  job.weekend, job.trip_requirement, job.accommodation, job.notes, null, null, null,
]);
tableBody("岗位明细", `A6:AA${5 + jobRows.length}`, jobRows);
const jobFormulas = payload.jobs.map((_, i) => {
  const r = 6 + i;
  return [
    `=IF(AND(ISNUMBER(K${r}),ISNUMBER(L${r})),(K${r}+L${r})/2,"")`,
    `=IF(AND(ISNUMBER(Y${r}),ISNUMBER(M${r})),Y${r}*M${r}/12,IF(ISNUMBER(Y${r}),Y${r},""))`,
    `=IF(ISNUMBER(Y${r}),1,0)`,
  ];
});
range("岗位明细", `Y6:AA${5 + jobRows.length}`).formulas = jobFormulas;
applyBox("岗位明细", `A5:AA${5 + jobRows.length}`);
range("岗位明细", `D6:D${5 + jobRows.length}`).format.numberFormat = "yyyy-mm-dd";
money("岗位明细", `K6:L${5 + jobRows.length}`); money("岗位明细", `Y6:AA${5 + jobRows.length}`);
range("岗位明细", `A6:AA${5 + jobRows.length}`).format.font = { name: font, size: 9, color: colors.ink };
for (let i = 0; i < jobRows.length; i += 1) {
  range("岗位明细", `A${6+i}:AA${6+i}`).format.rowHeight = 84;
  const included = payload.jobs[i].include_in_analysis === "yes";
  range("岗位明细", `R${6+i}`).format.fill = included ? colors.green : colors.paleGray;
}
note("岗位明细", "AC22", "纳入核心分析不等于满足双休和不出差；unknown只表示页面未写明，不能据此判定肯定或否定。", 76);
note("岗位明细", "AC26", "排除市场锚点保留在表中用于审计，不进入6条核心岗位计数。", 60);
setWidths("岗位明细", [29, 20, 42, 12, 26, 8, 12, 34, 38, 18, 12, 12, 11, 15, 12, 13, 15, 14, 30, 8, 11, 11, 11, 52, 13, 15, 15, 2, 52]);
sheets["岗位明细"].freezePanes.freezeRows(5);
sheets["岗位明细"].freezePanes.freezeColumns(9);

// 岗位汇总
setTitle("岗位汇总", "A2", "核心岗位样本规模、薪资覆盖和工作条件命中", 9);
headerRow("岗位汇总", "A5:H5", ["岗位族", "核心岗位数", "企业数", "公开薪资数", "广告薪资中位数", "明确双休", "明确不出差", "证据/解释"]);
const coreJobs = payload.jobs.filter((j) => j.include_in_analysis === "yes");
const families = [...new Set(coreJobs.map((j) => j.job_family))];
const familyRows = families.map((family) => {
  const group = coreJobs.filter((j) => j.job_family === family);
  const companies = new Set(group.map((j) => j.company)).size;
  const paid = group.filter((j) => j.monthly_min !== "").length;
  return [family, group.length, companies, paid, paid ? null : "未取得", group.filter((j) => j.weekend === "double").length, group.filter((j) => j.trip_requirement === "none").length, paid ? "广告值" : "面议或未列薪资；小样本C级"];
});
tableBody("岗位汇总", `A6:H${5 + familyRows.length}`, familyRows);
const famStart = 6;
const famEnd = 5 + familyRows.length;
applyBox("岗位汇总", `A5:H${famEnd}`);
for (let r = famStart; r <= famEnd; r += 1) range("岗位汇总", `A${r}:H${r}`).format.rowHeight = 28;
for (let i = 0; i < familyRows.length; i += 1) {
  const r = famStart + i;
  range("岗位汇总", `B${r}`).formulas = [[
    `=COUNTIFS('岗位明细'!$J$6:$J${5 + jobRows.length},A${r},'岗位明细'!$R$6:$R${5 + jobRows.length},"yes")`,
  ]];
  range("岗位汇总", `C${r}`).values = [[familyRows[i][2]]];
  range("岗位汇总", `D${r}`).formulas = [[
    `=COUNTIFS('岗位明细'!$J$6:$J${5 + jobRows.length},A${r},'岗位明细'!$R$6:$R${5 + jobRows.length},"yes",'岗位明细'!$AA$6:$AA${5 + jobRows.length},1)`,
  ]];
  range("岗位汇总", `F${r}:G${r}`).formulas = [[
    `=COUNTIFS('岗位明细'!$J$6:$J${5 + jobRows.length},A${r},'岗位明细'!$R$6:$R${5 + jobRows.length},"yes",'岗位明细'!$U$6:$U${5 + jobRows.length},"double")`,
    `=COUNTIFS('岗位明细'!$J$6:$J${5 + jobRows.length},A${r},'岗位明细'!$R$6:$R${5 + jobRows.length},"yes",'岗位明细'!$V$6:$V${5 + jobRows.length},"none")`,
  ]];
}

const summaryStart = famEnd + 3;
range("岗位汇总", `A${summaryStart-1}`).values = [["排除样本中的市场锚点（不能当作2027本科应届工资）"]];
range("岗位汇总", `A${summaryStart-1}`).format.font = { name: font, size: 11, bold: true, color: colors.navy };
headerRow("岗位汇总", `A${summaryStart}:F${summaryStart}`, ["公司", "职位", "学历/经验", "月薪区间", "年化中点/月", "排除原因"]);
const anchors = payload.jobs.filter((j) => j.include_in_analysis === "no" && j.monthly_min !== "");
const anchorRows = anchors.map((j) => [j.company, j.job_title, `${j.education} / ${j.experience}`, `${j.monthly_min.toLocaleString()}至${j.monthly_max.toLocaleString()} × ${j.annual_months}薪`, null, j.exclusion_reason]);
tableBody("岗位汇总", `A${summaryStart+1}:F${summaryStart+anchorRows.length}`, anchorRows);
const anchorFormulas = anchors.map((j, i) => {
  const r = summaryStart + 1 + i;
  return [`=(${j.monthly_min}+${j.monthly_max})/2*${j.annual_months}/12`];
});
range("岗位汇总", `E${summaryStart+1}:E${summaryStart+anchorRows.length}`).formulas = anchorFormulas;
applyBox("岗位汇总", `A${summaryStart}:F${summaryStart+anchorRows.length}`);
money("岗位汇总", `E${summaryStart+1}:E${summaryStart+anchorRows.length}`);
range("岗位汇总", `A${summaryStart+1}:F${summaryStart+anchorRows.length}`).format.wrapText = true;
for (let r = summaryStart + 1; r <= summaryStart + anchorRows.length; r += 1) range("岗位汇总", `A${r}:F${r}`).format.rowHeight = 60;
note("岗位汇总", "J22", `这${anchors.length}条锚点混有硕士、1至5年经验岗和售后岗。其年化月薪中点区间只用于审视市场，不能替代应届本科样本。`, 84);
setWidths("岗位汇总", [28, 38, 25, 13, 17, 34, 18, 38, 2, 52]);
sheets["岗位汇总"].freezePanes.freezeRows(5);
console.log("SHEET_JOBS_OK");

// 房租样本
setTitle("房租样本", "A2", "整租、合租与人才公寓的原始挂牌和展示样本", 17);
headerRow("房租样本", "A5:Q5", ["城市", "区县/板块", "住房类型", "面积/房间口径", "月租", "挂牌/样本数", "押金月数", "预付月数", "中介费月数", "月度服务费", "一次性服务费", "距站/参考距离km", "证据", "来源", "URL", "发布日", "采集日/备注"]);
const modeLabel = { share: "合租单间", whole: "整租", other: "条件性人才住房" };
const rentRows = payload.rents.map((r) => [
  r.city, r.district, modeLabel[r.rent_mode] || r.rent_mode, numeric(r.area_sqm), numeric(r.monthly_rent), numeric(r.listing_count),
  numeric(r.deposit_months), numeric(r.advance_rent_months), numeric(r.agency_fee_months), numeric(r.service_fee_monthly), numeric(r.service_fee_upfront),
  numeric(r.station_distance_km), r.evidence_level, r.source_name, r.source_url, dateValue(r.published_at), `${r.collected_at}；${r.notes}`,
]);
tableBody("房租样本", `A6:Q${5 + rentRows.length}`, rentRows);
applyBox("房租样本", `A5:Q${5 + rentRows.length}`);
money("房租样本", `E6:E${5 + rentRows.length}`);
range("房租样本", `P6:Q${5 + rentRows.length}`).format.wrapText = true;
range("房租样本", `P6:P${5 + rentRows.length}`).format.numberFormat = "yyyy-mm-dd";
range("房租样本", `A6:Q${5 + rentRows.length}`).format.font = { name: font, size: 9, color: colors.ink };
for (let i = 0; i < rentRows.length; i += 1) range("房租样本", `A${6+i}:Q${6+i}`).format.rowHeight = 76;
note("房租样本", "S18", "月租是挂牌、页面展示或官方项目价，不是个人最终成交价。挂牌数未知时留空，不当作零。", 76);
note("房租样本", "S22", "人才公寓需满足资格且有房；其官方价不能无条件套给所有毕业生。", 64);
setWidths("房租样本", [8, 14, 19, 17, 11, 13, 11, 11, 12, 13, 15, 15, 8, 30, 44, 12, 56, 2, 52]);
sheets["房租样本"].freezePanes.freezeRows(5);

// 官方规则
setTitle("官方规则", "A2", "官方工资、收入、消费与税费规则校准", 12);
headerRow("官方规则", "A5:K5", ["地区", "指标", "年份", "统计期", "数值", "单位", "样本量", "来源", "发布日", "证据", "口径"]);
const officialRows = payload.official_salary.map((r) => [r.city, r.metric, r.year, r.period, numeric(r.value), r.unit, numeric(r.sample_n), r.source_name, dateValue(r.published_at), r.evidence_level, r.notes]);
tableBody("官方规则", `A6:K${5 + officialRows.length}`, officialRows);
applyBox("官方规则", `A5:K${5 + officialRows.length}`);
range("官方规则", `E6:E${5 + officialRows.length}`).format.numberFormat = "#,##0";
range("官方规则", `I6:I${5 + officialRows.length}`).format.numberFormat = "yyyy-mm-dd";
range("官方规则", `K6:K${5 + officialRows.length}`).format.wrapText = true;
for (let i = 0; i < officialRows.length; i += 1) range("官方规则", `A${6+i}:K${6+i}`).format.rowHeight = 44;

const rulesStart = 13;
range("官方规则", `A${rulesStart-1}`).values = [["本报告实际使用的税费与公积金参数"]];
range("官方规则", `A${rulesStart-1}`).format.font = { name: font, size: 11, bold: true, color: colors.navy };
headerRow("官方规则", `A${rulesStart}:F${rulesStart}`, ["项目", "参数", "单位", "来源/解释", "证据", "用于模型"]);
const rulesRows = [
  ["社保缴费基数下限", 7546, "元/月", "2026年上海社保公告", "A", "是"],
  ["社保缴费基数上限", 37731, "元/月", "2026年上海社保公告", "A", "是"],
  ["个人社保比例", 0.105, "比例", "养老、医疗、失业保险个人合计", "A", "是"],
  ["公积金基数下限", 2740, "元/月", "2026年上海公积金缴存基数", "A", "是"],
  ["公积金基数上限", 37731, "元/月", "2026年上海公积金缴存基数", "A", "是"],
  ["个人主公积金比例", 0.07, "比例", "主模型7%，5%做敏感性", "A", "是"],
  ["住房租金专项附加扣除", 1500, "元/月", "上海住房租金专项附加扣除标准", "A", "是"],
  ["年度基本减除费用", 60000, "元/年", "居民个人综合所得", "A", "是"],
  ["2025全口径月均工资", 12577, "元/月", "外部参考，不是目标岗位工资中位数", "A", "否"],
];
tableBody("官方规则", `A${rulesStart+1}:F${rulesStart+rulesRows.length}`, rulesRows);
applyBox("官方规则", `A${rulesStart}:F${rulesStart+rulesRows.length}`);
money("官方规则", `B${rulesStart+1}:B${rulesStart+2}`); percent("官方规则", `B${rulesStart+3}`); money("官方规则", `B${rulesStart+4}:B${rulesStart+5}`); percent("官方规则", `B${rulesStart+6}`); money("官方规则", `B${rulesStart+7}:B${rulesStart+rulesRows.length}`);
for (let r = rulesStart + 1; r <= rulesStart + rulesRows.length; r += 1) range("官方规则", `A${r}:F${r}`).format.rowHeight = 28;
note("官方规则", "M24", "官方工资和居民收入只作外部分母，不代表2027电气本科招聘起薪。来源入口与原始日期保留在证据台账。", 80);
setWidths("官方规则", [31, 12, 12, 53, 8, 12, 12, 26, 12, 8, 66, 2, 54]);
sheets["官方规则"].freezePanes.freezeRows(5);

// 生活成本
setTitle("生活成本", "A2", "餐饮、水电气网、通勤与其他固定支出明细", 15);
headerRow("生活成本", "A5:O5", ["城市", "区县/板块", "餐饮/月", "水费/月", "电费/月", "燃气/月", "网络/月", "通勤/月", "其他固定/月", "生活成本小计", "证据", "来源", "发布日", "采集日", "口径"]);
const livingRows = payload.living.map((r) => [r.city, r.district, numeric(r.food_monthly), numeric(r.water_monthly), numeric(r.electricity_monthly), numeric(r.gas_monthly), numeric(r.internet_monthly), numeric(r.commute_monthly), numeric(r.other_fixed_monthly), null, r.evidence_level, r.source_url, dateValue(r.published_at), r.collected_at, r.notes]);
tableBody("生活成本", `A6:O${5 + livingRows.length}`, livingRows);
const li = payload.living.map((_, i) => { const r = 6 + i; return [`=SUM(C${r}:I${r})`]; });
range("生活成本", `J6:J${5 + livingRows.length}`).formulas = li;
applyBox("生活成本", `A5:O${5 + livingRows.length}`);
money("生活成本", `C6:J${5 + livingRows.length}`);
range("生活成本", `M6:M${5 + livingRows.length}`).format.numberFormat = "yyyy-mm-dd";
range("生活成本", `O6:O${5 + livingRows.length}`).format.wrapText = true;
range("生活成本", `A6:O${5 + livingRows.length}`).format.font = { name: font, size: 9, color: colors.ink };
for (let i = 0; i < livingRows.length; i += 1) range("生活成本", `A${6+i}:O${6+i}`).format.rowHeight = 68;
note("生活成本", "Q14", "餐饮为模型篮子，水电燃气按官方单价和透明用量计算。合租与整租分别分摊；未包含旅行、医疗和家电一次性采购。", 82);
setWidths("生活成本", [8, 14, 12, 11, 11, 11, 11, 11, 14, 16, 8, 43, 12, 12, 74, 2, 54]);
sheets["生活成本"].freezePanes.freezeRows(5);

// 证据台账
setTitle("证据台账", "A2", "每项关键数据的来源、日期、范围与原始文件", 12);
headerRow("证据台账", "A5:L5", ["模块", "来源键", "来源名称", "来源类型", "URL", "发布日", "采集日", "证据", "覆盖范围", "原始文件", "备注", "派生指标"]);
const evidenceRows = payload.evidence.map((r) => [r.module, r.key, r.source_name, r.source_type, r.url, dateValue(r.published_at), dateValue(r.collected_at), r.evidence_level, r.scope, r.raw_file, r.notes, ""]);
tableBody("证据台账", `A6:L${5 + evidenceRows.length}`, evidenceRows);
applyBox("证据台账", `A5:L${5 + evidenceRows.length}`);
range("证据台账", `F6:G${5 + evidenceRows.length}`).format.numberFormat = "yyyy-mm-dd";
range("证据台账", `A6:L${5 + evidenceRows.length}`).format.font = { name: font, size: 9, color: colors.ink };
for (let i = 0; i < evidenceRows.length; i += 1) range("证据台账", `A${6+i}:L${6+i}`).format.rowHeight = 72;
note("证据台账", "N32", "证据等级A为官方规则/统计，C为小样本或模型。链接可访问不代表内容永不改版；以本地原始文件和采集日为准。", 84);
setWidths("证据台账", [12, 25, 30, 18, 46, 12, 12, 8, 42, 42, 62, 42, 2, 54]);
sheets["证据台账"].freezePanes.freezeRows(5);
console.log("SHEET_DETAILS_OK");

// 主情景净结余图
const resultChart = sheets["净结余测算"].charts.add("bar", [
  range("净结余测算", "A8:A12"),
  range("净结余测算", "N8:N12"),
]);
resultChart.title = "当前工资下五种住房情景的月净结余";
resultChart.titleTextStyle.typeface = font;
resultChart.titleTextStyle.fontSize = 12;
resultChart.legend = { position: "bottom", textStyle: { typeface: font, fontSize: 10 } };
resultChart.xAxis = { axisType: "textAxis", textStyle: { typeface: font, fontSize: 9 } };
resultChart.yAxis = { numberFormatCode: '"¥"#,##0', numberFormatSourceLinked: false, textStyle: { typeface: font, fontSize: 9 } };
resultChart.setPosition("T18", "AD34");
console.log("CHART_OK");

// 最终复算、错误扫描、逐表渲染与导出
console.log("BEFORE_RECALC");
workbook.recalculate();
console.log("AFTER_RECALC");
const summaryCheck = await workbook.inspect({
  kind: "table",
  range: "税费计算!B19:J35",
  include: "values,formulas",
  tableMaxRows: 18,
  tableMaxCols: 10,
});
console.log("KEY_CALCULATIONS");
console.log(summaryCheck.ndjson);
console.log("AFTER_SUMMARY_INSPECT");

const errorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
await fs.writeFile(path.join(renderDir, "formula_errors.txt"), errorScan.ndjson || "", "utf8");
if (/Sheet:|address=|match/i.test(errorScan.ndjson || "")) console.log(errorScan.ndjson);
console.log("AFTER_ERROR_SCAN");

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`OUTPUT=${outputPath}`);
