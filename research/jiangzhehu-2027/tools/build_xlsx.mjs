import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const data = JSON.parse(await fs.readFile("data.json", "utf8"));
const FONT = "微软雅黑";
const OUT = "outputs/01a09ac1-e853-7671-a83f-cea3e7f16019";
await fs.mkdir(OUT, { recursive: true });

const wb = Workbook.create();
const HEADER = {
  fill: "#1F3864",
  font: { name: FONT, bold: true, color: "#FFFFFF", size: 10 },
  verticalAlignment: "center",
  wrapText: true,
};
const BODY = { font: { name: FONT, size: 10 }, verticalAlignment: "center" };

function colLetter(n) {
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function writeBlock(sheet, startRow, matrix) {
  const rows = matrix.length;
  const cols = matrix[0].length;
  sheet
    .getRange(`A${startRow}:${colLetter(cols)}${startRow + rows - 1}`)
    .values = matrix;
  return { rows, cols, last: startRow + rows - 1 };
}

/* ---------- 假设（可调参数） ---------- */
const asm = wb.worksheets.add("假设");
asm.getRange("A1:D1").values = [["参数", "值", "说明", "来源 / 依据"]];
asm.getRange("A2:D16").values = [
  ["合租等效面积（平方米）", 25.8, "合租单间月租 = 城市租金单价 × 该面积", "由上海、杭州、南京、温州四城实测合租价反推的中位数"],
  ["整租一居面积（平方米）", 50, "整租一居月租 = 城市租金单价 × 该面积", "一居室建筑面积的市场常规口径"],
  ["社保个人缴存比例", 0.105, "养老 8% + 医疗 2% + 失业 0.5%", "江浙沪各市基本一致"],
  ["公积金个人缴存比例", 0.08, "各市区间 5%–12%，取中间值", "不影响含公积金净结余，仅影响现金到手"],
  ["社保缴费基数下限（元）", 4900, "月薪低于此值按下限计缴", "各市 4500–5500 之间"],
  ["个税起征点（元/月）", 5000, "经营所得以外综合所得", "个人所得税法"],
  ["工作天数（天/月）", 22, "用于通勤计算", "法定月均计薪天数 21.75，取整"],
  ["地铁单程票价（元）", 3.5, "无区级票价的城市的默认值", "各市公开计价规则"],
  ["公交单程票价（元）", 2.0, "无轨道交通城市的默认值", "各市公开票价"],
  ["餐饮单身青年系数", 1.25, "在全体居民食品烟酒支出基础上的上浮", "单身青年在外饮食比例高于全体居民"],
  ["报告截止日期", "2026-09-15", "全部数据的采集时点", "—"],
  ["中介费（月房租倍数）", 1.0, "通过中介租普通房源时一次性支付，通常为 1 个月房租", "行业惯例，部分城市为 0.5 个月"],
  ["中介费摊销月数", 12, "把一次性中介费摊到租期上，按月计入成本", "按一年租期摊薄"],
  ["品牌公寓服务费率", 0.10, "自如等品牌公寓按月收取的服务费占房租比例", "公开报价区间 8%–12%"],
  ["押付首期月数", 4, "押一付三时首期需支付 1 个月押金加 3 个月房租", "市场最常见付法"],
];
asm.getRange("B2:B16").format.numberFormat = "0.00";
asm.getRange("A1:D1").format = HEADER;
asm.getRange("A2:D16").format = { ...BODY, wrapText: true };
asm.getRange("A1:A16").format.columnWidth = 26;
asm.getRange("B1:B16").format.columnWidth = 12;
asm.getRange("C1:C16").format.columnWidth = 44;
asm.getRange("D1:D16").format.columnWidth = 52;
asm.getRange("A1:D1").format.rowHeight = 22;
asm.freezePanes.freezeRows(1);

/* ---------- 城市净结余（Build，公式驱动） ---------- */
const city = wb.worksheets.add("城市净结余");
const c = data.cities;
const cityHead = ["城市", "税前月薪", "社保", "公积金", "个税", "现金到手",
  "租金单价（元/㎡/月）", "合租月租", "整租一居月租", "通勤", "餐饮",
  "水电气宽带（合租）", "水电气宽带（整租）",
  "中介费摊销", "品牌公寓服务费",
  "净结余（合租·直租）", "净结余（合租·中介）", "净结余（合租·品牌公寓）", "净结余（整租·直租）",
  "首月现金（合租·中介）", "房租占收入（合租）", "房租占收入（整租）",
  "全国租金排名", "合租实测值"];
const CITY_COLS = "A1:X1";
city.getRange(CITY_COLS).values = [cityHead];
const rows = c.map((x) => {
  return [
    x["城市"], x["税前月薪"], null, null, null, null,
    x["租金元每平米每月"], null, null, x["通勤"], x["餐饮"],
    x["合租分摊"], x["整租自付"],
    null, null,
    null, null, null, null, null, null, null,
    x["全国排名"],
    x["房租性质"] === "实测" ? x["合租月租"] : null,
  ];
});
city.getRange(`A2:X${rows.length + 1}`).values = rows;
const last = rows.length + 1;
const A = "'假设'!";
city.getRange(`C2:C${last}`).formulas = [[`=MAX(B2,${A}$B$6)*${A}$B$4`]];
city.getRange(`D2:D${last}`).formulas = [[`=MAX(B2,${A}$B$6)*${A}$B$5`]];
// 个税按七级超额累进税率计算
city.getRange(`E2:E${last}`).formulas = [[
  `=LET(t,MAX(0,B2-C2-D2-${A}$B$7),` +
  `IF(t<=3000,t*0.03,` +
  `IF(t<=12000,t*0.1-210,` +
  `IF(t<=25000,t*0.2-1410,` +
  `IF(t<=35000,t*0.25-2660,` +
  `IF(t<=55000,t*0.3-4410,t*0.35-7160))))))`,
]];
city.getRange(`F2:F${last}`).formulas = [["=B2-C2-D2-E2"]];
// 合租：优先用实测值，没有实测按等效面积换算；整租一居按独立面积换算
// 实测值所在列由表头动态定位，避免后续增删列时引用失效
const MEASURED_COL = colLetter(cityHead.indexOf("合租实测值") + 1);
city.getRange(`H2:H${last}`).formulas = [[`=IF(${MEASURED_COL}2>0,${MEASURED_COL}2,G2*${A}$B$2)`]];
city.getRange(`I2:I${last}`).formulas = [[`=G2*${A}$B$3`]];
// 中介费按租期摊薄；品牌公寓按月收服务费
city.getRange(`N2:N${last}`).formulas = [[`=H2*${A}$B$13/${A}$B$14`]];
city.getRange(`O2:O${last}`).formulas = [[`=H2*${A}$B$15`]];
// 三条租房路径：直租（基准）、中介（含中介费摊销）、品牌公寓（含服务费）
city.getRange(`P2:P${last}`).formulas = [["=F2-H2-J2-K2-L2"]];
city.getRange(`Q2:Q${last}`).formulas = [["=P2-N2"]];
city.getRange(`R2:R${last}`).formulas = [["=P2-O2"]];
city.getRange(`S2:S${last}`).formulas = [["=F2-I2-J2-K2-M2"]];
city.getRange(`T2:T${last}`).formulas = [[`=(H2+N2)*${A}$B$16`]];
city.getRange(`U2:U${last}`).formulas = [["=H2/B2"]];
city.getRange(`V2:V${last}`).formulas = [["=I2/B2"]];
city.getRange(`C2:F${last}`).fillDown();
city.getRange(`H2:I${last}`).fillDown();
city.getRange(`N2:V${last}`).fillDown();
city.getRange(CITY_COLS).format = HEADER;
city.getRange(`B2:T${last}`).format.numberFormat = "#,##0";
city.getRange(`U2:V${last}`).format.numberFormat = "0.0%";
city.getRange(CITY_COLS).format.rowHeight = 34;
const cityWidths = { A: 10, B: 11, C: 10, D: 10, E: 9, F: 11, G: 15, H: 11,
  I: 13, J: 9, K: 10, L: 14, M: 14, N: 12, O: 14,
  P: 16, Q: 16, R: 18, S: 16, T: 17, U: 14, V: 14, W: 11, X: 11 };
for (const [col, w] of Object.entries(cityWidths)) {
  city.getRange(`${col}1:${col}1`).format.columnWidth = w;
}
city.getRange(`A2:X${last}`).format = BODY;
city.freezePanes.freezeRows(1);

/* ---------- 区级净结余 ---------- */
const dist = wb.worksheets.add("区级净结余");
const dr = data.districtRent;
const drHead = ["城市", "区县", "租金（元/㎡/月）", "合租单间（估算）", "整租一居（估算）",
  "电气岗位数", "月薪中位数（元）", "净结余（合租）", "净结余（整租）"];
dist.getRange("A1:I1").values = [drHead];
const drRows = dr.map((x) => [x["城市"], x["区县"], x["元每平米每月"], null, null, null, null, null, null]);
dist.getRange(`A2:I${drRows.length + 1}`).values = drRows;
const drLast = drRows.length + 1;
dist.getRange(`D2:D${drLast}`).formulas = [[`=C2*${A}$B$2`]];
dist.getRange(`E2:E${drLast}`).formulas = [[`=C2*${A}$B$3`]];
dist.getRange("A1:I1").format = HEADER;
dist.getRange(`C2:E${drLast}`).format.numberFormat = "#,##0.0";
dist.getRange(`F2:I${drLast}`).format.numberFormat = "#,##0";
dist.getRange("A1:I1").format.rowHeight = 34;
const drWidths = { A: 10, B: 14, C: 15, D: 15, E: 15, F: 12, G: 15, H: 15, I: 15 };
for (const [col, w] of Object.entries(drWidths)) {
  dist.getRange(`${col}1:${col}1`).format.columnWidth = w;
}
dist.getRange(`A2:I${drLast}`).format = BODY;
dist.freezePanes.freezeRows(1);

/* ---------- 电气岗位清单 ---------- */
const job = wb.worksheets.add("电气岗位");
job.getRange("A1:H1").values = [[
  "城市", "区县", "岗位", "公司", "薪资", "月薪下限（元）", "需要出差", "不需要出差",
]];
const jr = data.jobs.map((x) => [
  x.city, x.district, x.title, x.company, x.salary, x.lo,
  x.needTravel ? "是" : "", x.noTravel ? "是" : "",
]);
job.getRange(`A2:H${jr.length + 1}`).values = jr;
job.getRange("A1:H1").format = HEADER;
job.getRange(`F2:F${jr.length + 1}`).format.numberFormat = "#,##0";
job.getRange("A1:H1").format.rowHeight = 26;
job.getRange("A1:A1").format.columnWidth = 9;
job.getRange("B1:B1").format.columnWidth = 12;
job.getRange("C1:C1").format.columnWidth = 34;
job.getRange("D1:D1").format.columnWidth = 24;
job.getRange("E1:E1").format.columnWidth = 13;
job.getRange("F1:F1").format.columnWidth = 14;
job.getRange("G1:H1").format.columnWidth = 11;
job.getRange(`A2:H${jr.length + 1}`).format = { font: { name: FONT, size: 9 }, verticalAlignment: "center" };
job.freezePanes.freezeRows(1);
job.freezePanes.freezeColumns(2);

/* ---------- 官方统计 ---------- */
const off = wb.worksheets.add("官方统计");
const occ = data.official;
const offHead = Object.keys(occ[0]);
off.getRange(`A1:${colLetter(offHead.length)}1`).values = [offHead];
off.getRange(`A2:${colLetter(offHead.length)}${occ.length + 1}`).values =
  occ.map((x) => offHead.map((k) => x[k] ?? ""));
off.getRange(`A1:${colLetter(offHead.length)}1`).format = HEADER;
off.getRange(`A2:${colLetter(offHead.length)}${occ.length + 1}`).format =
  { font: { name: FONT, size: 9 }, verticalAlignment: "center" };
off.getRange("A1:A1").format.columnWidth = 9;
off.getRange("B1:B1").format.columnWidth = 46;
off.getRange(`C1:${colLetter(offHead.length)}1`).format.columnWidth = 15;
off.freezePanes.freezeRows(1);

/* ---------- 数据来源与证据等级 ---------- */
const src = wb.worksheets.add("数据来源");
src.getRange("A1:D1").values = [["数据模块", "来源", "覆盖范围", "证据等级"]];
src.getRange("A2:D13").values = [
  ["薪资（招聘市场）", "BOSS 直聘 API", "6197 条岗位，25 城 × 12 关键词 × 2 经验档", "B 平台数据"],
  ["薪资（官方工资）", "各市统计局《单位就业人员年平均工资统计公报》", "11 城", "A 官方数据"],
  ["居民收入与消费支出", "台州统计年鉴 2025 表 20-3（转载各市统计局）", "25 城 2024 年", "A 官方数据"],
  ["居民收入与消费支出", "各市统计局国民经济和社会发展统计公报", "14 城 2025 年", "A 官方数据"],
  ["房租（城市级）", "中国房价行情网 城市房租排行（近 3 个月）", "25 城，全国 323 城口径统一", "B 平台数据"],
  ["房租（区县级）", "中国房价行情网 各城市房租页", "12 城 66 个区县", "B 平台数据"],
  ["合租价格", "中国房价行情网 城市合租排行", "4 城实测（上海、杭州、南京、温州）", "B 平台数据"],
  ["餐饮成本", "台州统计年鉴食品烟酒分项推算", "13 城官方分项 + 12 城按比值推算", "A/B 混合"],
  ["工作条件（出差、双休、倒班）", "BOSS 直聘技能标签字段", "6197 条岗位的结构化标签", "B 平台数据"],
  ["岗位描述文本", "BOSS 直聘职位详情页", "141 条 JD 全文", "B 平台数据"],
  ["社保与个税", "江浙沪各市人社局、公积金中心公开规则", "全省适用", "A 官方规则"],
  ["通勤票价", "各市地铁与公交公开计价规则", "25 城", "A 官方规则"],
];
src.getRange("A1:D1").format = HEADER;
src.getRange("A2:D13").format = { ...BODY, wrapText: true };
src.getRange("A1:A1").format.columnWidth = 26;
src.getRange("B1:B1").format.columnWidth = 52;
src.getRange("C1:C1").format.columnWidth = 46;
src.getRange("D1:D1").format.columnWidth = 14;
src.getRange("A2:D13").format.rowHeight = 26;
src.freezePanes.freezeRows(1);

// 行顺序：假设 → 城市净结余 → 区级净结余 → 电气岗位 → 官方统计 → 数据来源
wb.worksheets.getItem("假设").tabColor = "#C00000";

wb.recalculate();
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(`${OUT}/江浙沪电气应届生调研数据总表.xlsx`);
console.log("exported");
