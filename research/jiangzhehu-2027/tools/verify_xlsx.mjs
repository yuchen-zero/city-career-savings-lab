import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const OUT = "outputs/01a09ac1-e853-7671-a83f-cea3e7f16019";
const blob = await FileBlob.load(`${OUT}/江浙沪电气应届生调研数据总表.xlsx`);
const wb = await SpreadsheetFile.importXlsx(blob);

const sheets = await wb.inspect({ kind: "sheet", include: "id,name" });
console.log("工作表:", sheets.ndjson);

const city = await wb.inspect({
  kind: "table",
  sheetId: "城市净结余",
  range: "A1:Q8",
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 17,
});
console.log("\n城市净结余前 7 行（含整租）:");
console.log(city.ndjson);

const errs = await wb.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!",
  options: { useRegex: true, maxResults: 50 },
});
console.log("\n公式错误扫描:", errs.recordCount === 0 ? "无" : errs.ndjson);

const preview = await wb.render({ sheetName: "城市净结余", autoCrop: "all", scale: 2 });
await fs.writeFile(`${OUT}/preview-city.png`, new Uint8Array(await preview.arrayBuffer()));
const preview2 = await wb.render({ sheetName: "假设", autoCrop: "all", scale: 2 });
await fs.writeFile(`${OUT}/preview-asm.png`, new Uint8Array(await preview2.arrayBuffer()));
console.log("\n预览已导出");
