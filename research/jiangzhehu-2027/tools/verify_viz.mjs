import fs from "node:fs/promises";

const FILE =
  "outputs/01a09ac1-e853-7671-a83f-cea3e7f16019/江浙沪电气应届生净结余测算.html";
const html = await fs.readFile(FILE, "utf8");

console.log("=== 静态结构校验 ===");
const struct = {
  "合租/整租切换": html.includes('name="mode" value="share"') && html.includes('name="mode" value="whole"'),
  "整租面积滑块": html.includes('id="whole"'),
  "整租表头": html.includes('id="th-rent"'),
  "区县表含整租列": (html.match(/整租一居/g) || []).length >= 2,
  "合租：优先实测值": html.includes('c.kind === "实测" ? c.rent * (area / 25.8) : c.unit * area'),
  "整租：单价×面积": html.includes("const wholeRent = c.unit * whole"),
  "水电气宽带条目": html.includes("utilShare") && html.includes("utilWhole"),
  "水电气计入净结余": html.includes("cash - rent - commute - food - util"),
  "房租占收入列": html.includes("ratio: rent / c.salary"),
};
for (const [k, v] of Object.entries(struct)) console.log(`  ${v ? "✓" : "✗"} ${k}`);

// 语法检查：把 <script> 内容交给 Node 解析
const script = html.split("<script>")[1].split("</script>")[0];
try {
  // 整段脚本交给 V8 解析（DOM 调用不会执行，只做语法检查）
  new Function(script);
  console.log("  ✓ JavaScript 语法解析通过（整段脚本）");
} catch (err) {
  console.log("  ✗ 语法错误: " + err.message);
}

// 独立复算：从 HTML 里取出内嵌数据，验证整租口径的排名
const dataLine = script
  .split("\n")
  .find((line) => line.trim().startsWith("const DATA = "));
const payload = JSON.parse(
  dataLine.trim().replace(/^const DATA = /, "").replace(/;\s*$/, "")
);

function tax(t) {
  if (t <= 0) return 0;
  for (const [cap, rate, ded] of [
    [3000, 0.03, 0], [12000, 0.1, 210], [25000, 0.2, 1410],
    [35000, 0.25, 2660], [55000, 0.3, 4410], [80000, 0.35, 7160],
  ]) if (t <= cap) return t * rate - ded;
  return t * 0.45 - 15160;
}

function rank(mode, area = 25.8, whole = 50) {
  return payload.cities
    .map((c) => {
      const soc = c.salary * 0.105;
      const fnd = c.salary * 0.08;
      const cash = c.salary - soc - fnd - tax(Math.max(0, c.salary - soc - fnd - 5000));
      const rent = mode === "share"
        ? (c.kind === "实测" ? c.rent * (area / 25.8) : c.unit * area)
        : c.unit * whole;
      const util = mode === "share" ? c.utilShare : c.utilWhole;
      return {
        name: c.name, rent: Math.round(rent), util,
        net: Math.round(cash - rent - c.commute - c.food * 1.25 - util + fnd),
      };
    })
    .sort((a, b) => b.net - a.net);
}

console.log("\n=== 独立复算：合租口径 TOP5 ===");
rank("share").slice(0, 5).forEach((r, i) => console.log(`  ${i + 1}. ${r.name}  租金 ${r.rent.toLocaleString()}  净结余 ${r.net.toLocaleString()}`));

console.log("\n=== 独立复算：整租一居口径 TOP5 ===");
rank("whole").slice(0, 5).forEach((r, i) => console.log(`  ${i + 1}. ${r.name}  租金 ${r.rent.toLocaleString()}  净结余 ${r.net.toLocaleString()}`));

console.log("\n=== 上海的两种口径对比 ===");
for (const m of ["share", "whole"]) {
  const r = rank(m).find((x) => x.name === "上海");
  console.log(`  ${m === "share" ? "合租" : "整租"}: 租金 ${r.rent.toLocaleString()}，净结余 ${r.net.toLocaleString()}`);
}
