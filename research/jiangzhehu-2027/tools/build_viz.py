# -*- coding: utf-8 -*-
"""Generate a self-contained interactive HTML page for the net-surplus model."""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))

# 餐饮滑块作用在「全体居民食品烟酒支出」原始值上，避免与单身青年系数重复计算
RAW_FOOD = {}
food_csv = os.path.join(HERE, "..", "gh-tools", "餐饮成本推算.csv")
if os.path.exists(food_csv):
    with open(food_csv, encoding="utf-8-sig") as fh:
        header = fh.readline().strip().split(",")
        i_city = header.index("城市")
        i_raw = header.index("食品烟酒月")
        for line in fh:
            parts = line.strip().split(",")
            if len(parts) > i_raw:
                RAW_FOOD[parts[i_city]] = float(parts[i_raw])

cities = [
    {
        "name": x["城市"],
        "salary": x["税前月薪"],
        "rent": x["合租月租"],
        "unit": x["租金元每平米每月"],
        "commute": x["通勤"],
        "food": RAW_FOOD.get(x["城市"], x["餐饮"] / 1.25),
        "utilShare": x["合租分摊"],
        "utilWhole": x["整租自付"],
        "kind": x["房租性质"],
    }
    for x in DATA["cities"]
]

districts = {}
for row in DATA["districtRent"]:
    districts.setdefault(row["城市"], []).append(
        {"name": row["区县"], "unit": row["元每平米每月"]}
    )

job_stats = {}
for job in DATA["jobs"]:
    c = job["city"]
    stats = job_stats.setdefault(c, {"total": 0, "noTravel": 0, "needTravel": 0, "weekend": 0})
    stats["total"] += 1
    stats["noTravel"] += 1 if job["noTravel"] else 0
    stats["needTravel"] += 1 if job["needTravel"] else 0
    stats["weekend"] += 1 if job["weekend"] else 0

PAYLOAD = json.dumps(
    {"cities": cities, "districts": districts, "jobStats": job_stats}, ensure_ascii=False
)

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>江浙沪电气应届生净结余测算</title>
<style>
  :root { --ink:#111827; --muted:#6b7280; --line:#e5e7eb; --accent:#1f3864; --pos:#047857; --neg:#b91c1c; }
  * { box-sizing: border-box; }
  body { margin:0; font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif; color:var(--ink); background:#f8fafc; line-height:1.6; }
  .wrap { max-width:1180px; margin:0 auto; padding:32px 24px 64px; }
  h1 { font-size:26px; margin:0 0 6px; }
  .sub { color:var(--muted); font-size:14px; margin-bottom:24px; }
  .panel { background:#fff; border:1px solid var(--line); border-radius:10px; padding:20px 22px; margin-bottom:20px; }
  .panel h2 { font-size:16px; margin:0 0 14px; color:var(--accent); }
  .sliders { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:16px 26px; }
  .sl { display:flex; flex-direction:column; gap:4px; }
  .sl label { font-size:13px; display:flex; justify-content:space-between; }
  .sl b { color:var(--accent); font-variant-numeric:tabular-nums; }
  input[type=range] { width:100%; accent-color:var(--accent); }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th, td { padding:8px 10px; border-bottom:1px solid var(--line); text-align:right; }
  th:first-child, td:first-child { text-align:left; }
  thead th { background:var(--accent); color:#fff; font-weight:600; position:sticky; top:0; }
  tbody tr:nth-child(even) { background:#f9fafb; }
  .bar { position:relative; height:18px; background:#eef2f7; border-radius:4px; min-width:60px; }
  .bar > span { position:absolute; left:0; top:0; bottom:0; border-radius:4px; background:linear-gradient(90deg,#2563eb,#60a5fa); }
  .num { font-variant-numeric:tabular-nums; }
  .pos { color:var(--pos); font-weight:600; }
  .neg { color:var(--neg); font-weight:600; }
  .hint { font-size:12px; color:var(--muted); margin-top:10px; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
  @media (max-width:820px){ .grid2 { grid-template-columns:1fr; } }
  select { padding:6px 10px; border:1px solid var(--line); border-radius:6px; font-family:inherit; font-size:13px; }
  .tag { display:inline-block; font-size:11px; padding:1px 7px; border-radius:10px; background:#eef2ff; color:#3730a3; margin-left:6px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>江浙沪电气与自动化应届生 月净结余测算</h1>
  <div class="sub">数据采集截止 2026-09-15 · 拖动参数即可重算全部城市的净结余排名</div>

  <div class="panel">
    <h2>参数（可调）</h2>
    <div style="margin-bottom:14px">
      <b style="font-size:13px">租房方式：</b>
      <label style="margin-left:10px;font-size:13px"><input type="radio" name="mode" value="share" checked> 合租单间</label>
      <label style="margin-left:16px;font-size:13px"><input type="radio" name="mode" value="whole"> 整租一居</label>
      <span class="hint" style="margin-left:12px">切换后表格与排名会按对应口径重算</span>
    </div>
    <div style="margin-bottom:14px">
      <b style="font-size:13px">租房渠道：</b>
      <label style="margin-left:10px;font-size:13px"><input type="radio" name="chan" value="direct" checked> 房东直租（无中介费）</label>
      <label style="margin-left:16px;font-size:13px"><input type="radio" name="chan" value="agent"> 中介（1 个月中介费）</label>
      <label style="margin-left:16px;font-size:13px"><input type="radio" name="chan" value="brand"> 品牌公寓（10% 服务费）</label>
    </div>
    <div class="sliders">
      <div class="sl"><label>合租等效面积 <b><span id="v-area">25.8</span> ㎡</b></label>
        <input type="range" id="area" min="15" max="40" step="0.2" value="25.8"></div>
      <div class="sl"><label>整租一居面积 <b><span id="v-whole">50</span> ㎡</b></label>
        <input type="range" id="whole" min="30" max="90" step="2" value="50"></div>
      <div class="sl"><label>社保个人比例 <b><span id="v-social">10.5</span>%</b></label>
        <input type="range" id="social" min="8" max="12" step="0.1" value="10.5"></div>
      <div class="sl"><label>公积金个人比例 <b><span id="v-fund">8</span>%</b></label>
        <input type="range" id="fund" min="5" max="12" step="0.5" value="8"></div>
      <div class="sl"><label>餐饮上浮系数 <b><span id="v-food">1.25</span></b></label>
        <input type="range" id="food" min="0.8" max="1.8" step="0.05" value="1.25"></div>
      <div class="sl"><label>月工作天数 <b><span id="v-days">22</span> 天</b></label>
        <input type="range" id="days" min="18" max="26" step="1" value="22"></div>
      <div class="sl"><label>医保与失业附加 <b><span id="v-extra">0</span>%</b></label>
        <input type="range" id="extra" min="0" max="2" step="0.1" value="0"></div>
      <div class="sl"><label>押付首期月数 <b><span id="v-dep">4</span> 个月</b></label>
        <input type="range" id="dep" min="2" max="6" step="1" value="4"></div>
    </div>
    <div class="hint">公积金是个人账户资金，可提取用于租房，因此同时给出「现金净结余」和「含公积金净结余」两个口径。
      中介费按 12 个月摊薄计入月度成本；押付首期默认为押一付三（4 个月房租），只影响首月现金、不影响月均。</div>
  </div>

  <div class="panel">
    <h2>城市净结余排名</h2>
    <table>
      <thead><tr>
        <th>城市</th><th>税前月薪</th><th>现金到手</th><th id="th-rent">合租</th><th>通勤</th><th>餐饮</th>
        <th>水电气宽带</th><th id="th-fee">中介费摊销</th>
        <th>净结余（现金）</th><th>净结余（含公积金）</th><th>首月现金</th><th>房租占收入</th><th style="width:110px">相对水平</th>
      </tr></thead>
      <tbody id="rows"></tbody>
    </table>
    <div class="hint">月薪为 BOSS 直聘「应届生档」岗位薪资下限的中位数；餐饮按各城市官方食品烟酒支出推算；
      水电气宽带按省级居民阶梯价格与单人月用量估算（合租按人头分摊，整租全部自付）。</div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>区级房租（元/㎡/月）</h2>
      <label>选择城市：<select id="citySel"></select></label>
      <table style="margin-top:12px"><thead><tr><th>区县</th><th>租金单价</th><th>合租估算</th><th>整租一居</th></tr></thead>
      <tbody id="distRows"></tbody></table>
      <div class="hint">合租估算 = 租金单价 × 合租等效面积；整租一居 = 租金单价 × 整租面积。仅 12 个城市有区县级数据。</div>
    </div>

    <div class="panel">
      <h2>岗位工作条件（应届生电气岗）</h2>
      <table><thead><tr><th>城市</th><th>岗位数</th><th>标注需要出差</th><th>标注不需要出差</th><th>标注双休</th></tr></thead>
      <tbody id="jobRows"></tbody></table>
      <div class="hint">工作条件来自 BOSS 直聘的结构化技能标签字段，未标注不代表没有该条件。</div>
    </div>
  </div>

  <div class="panel">
    <h2>数据来源与证据等级</h2>
    <table>
      <thead><tr><th>数据模块</th><th>来源</th><th>覆盖范围</th><th>等级</th></tr></thead>
      <tbody>
        <tr><td>招聘薪资</td><td>BOSS 直聘 API</td><td>6197 条岗位，25 城</td><td class="num">B</td></tr>
        <tr><td>官方工资</td><td>各市统计局工资统计公报</td><td>11 城</td><td class="num">A</td></tr>
        <tr><td>居民收入与消费</td><td>台州统计年鉴转载各市统计局</td><td>25 城 2024 年</td><td class="num">A</td></tr>
        <tr><td>房租</td><td>中国房价行情网</td><td>25 城 + 12 城区县</td><td class="num">B</td></tr>
        <tr><td>餐饮</td><td>统计年鉴食品烟酒分项推算</td><td>25 城</td><td class="num">A/B</td></tr>
        <tr><td>社保与个税</td><td>各市人社局与公积金中心规则</td><td>全省适用</td><td class="num">A</td></tr>
      </tbody>
    </table>
  </div>
</div>

<script>
const DATA = __PAYLOAD__;
const $ = (id) => document.getElementById(id);

function tax(t) {
  if (t <= 0) return 0;
  const b = [[3000,0.03,0],[12000,0.10,210],[25000,0.20,1410],[35000,0.25,2660],[55000,0.30,4410],[80000,0.35,7160]];
  for (const [cap, rate, ded] of b) if (t <= cap) return t * rate - ded;
  return t * 0.45 - 15160;
}

function pick(name) { return document.querySelector(`input[name=${name}]:checked`).value; }

function compute() {
  const area = +$("area").value;
  const whole = +$("whole").value;
  const m = pick("mode");
  const chan = pick("chan");
  const social = (+$("social").value + +$("extra").value) / 100;
  const fund = +$("fund").value / 100;
  const foodK = +$("food").value;
  const days = +$("days").value;
  const depMonths = +$("dep").value;

  $("v-area").textContent = area.toFixed(1);
  $("v-whole").textContent = whole;
  $("v-social").textContent = (+$("social").value).toFixed(1);
  $("v-fund").textContent = (+$("fund").value).toFixed(1);
  $("v-food").textContent = foodK.toFixed(2);
  $("v-days").textContent = days;
  $("v-extra").textContent = (+$("extra").value).toFixed(1);
  $("v-dep").textContent = depMonths;
  $("th-rent").textContent = m === "share" ? "合租" : "整租一居";
  $("th-fee").textContent = chan === "agent" ? "中介费摊销" : (chan === "brand" ? "服务费" : "无渠道费");

  const rows = DATA.cities.map((c) => {
    const base = Math.max(c.salary, 4900);
    const soc = base * social;
    const fnd = base * fund;
    const t = Math.max(0, c.salary - soc - fnd - 5000);
    const cash = c.salary - soc - fnd - tax(t);
    // 合租：有实测值用实测，否则按等效面积换算；整租：单价 × 一居面积
    const shareRent = c.kind === "实测" ? c.rent * (area / 25.8) : c.unit * area;
    const wholeRent = c.unit * whole;
    const rent = m === "share" ? shareRent : wholeRent;
    const commute = c.commute * (days / 22);
    const food = c.food * foodK;
    const util = m === "share" ? c.utilShare : c.utilWhole;
    // 渠道费：中介费按 12 个月摊薄；品牌公寓按月收 10% 服务费；直租为零
    const fee = chan === "agent" ? rent / 12 : (chan === "brand" ? rent * 0.1 : 0);
    const netCash = cash - rent - commute - food - util - fee;
    const upfront = (rent + fee) * depMonths;
    return { ...c, cash, rent, commute, food, util, fee, upfront, netCash, net: netCash + fnd,
             ratio: rent / c.salary };
  }).sort((a, b) => b.net - a.net);

  const max = Math.max(...rows.map((r) => r.net), 1);
  $("rows").innerHTML = rows.map((r) => {
    const w = Math.max(2, (r.net / max) * 100);
    const cls = r.netCash >= 3000 ? "pos" : (r.netCash < 1500 ? "neg" : "");
    return `<tr>
      <td><b>${r.name}</b>${m === "share" && r.kind === "实测" ? '<span class="tag">房租实测</span>' : ""}</td>
      <td class="num">${r.salary.toLocaleString()}</td>
      <td class="num">${Math.round(r.cash).toLocaleString()}</td>
      <td class="num">${Math.round(r.rent).toLocaleString()}</td>
      <td class="num">${Math.round(r.commute).toLocaleString()}</td>
      <td class="num">${Math.round(r.food).toLocaleString()}</td>
      <td class="num">${Math.round(r.util).toLocaleString()}</td>
      <td class="num">${r.fee ? Math.round(r.fee).toLocaleString() : "—"}</td>
      <td class="num ${cls}">${Math.round(r.netCash).toLocaleString()}</td>
      <td class="num pos">${Math.round(r.net).toLocaleString()}</td>
      <td class="num">${Math.round(r.upfront).toLocaleString()}</td>
      <td class="num ${r.ratio > 0.35 ? "neg" : ""}">${(r.ratio * 100).toFixed(1)}%</td>
      <td><div class="bar"><span style="width:${w}%"></span></div></td>
    </tr>`;
  }).join("");
}

function renderDistricts() {
  const city = $("citySel").value;
  const area = +$("area").value;
  const whole = +$("whole").value;
  const list = (DATA.districts[city] || []).slice().sort((a, b) => b.unit - a.unit);
  $("distRows").innerHTML = list.length
    ? list.map((d) => `<tr><td>${d.name}</td><td class="num">${d.unit.toFixed(2)}</td>
        <td class="num">${Math.round(d.unit * area).toLocaleString()}</td>
        <td class="num">${Math.round(d.unit * whole).toLocaleString()}</td></tr>`).join("")
    : '<tr><td colspan="4" style="color:#6b7280">该城市暂无区县级房租数据</td></tr>';
}

function renderJobs() {
  const keys = Object.keys(DATA.jobStats);
  $("jobRows").innerHTML = keys.map((k) => {
    const s = DATA.jobStats[k];
    return `<tr><td>${k}</td><td class="num">${s.total}</td>
      <td class="num">${s.needTravel || ""}</td><td class="num">${s.noTravel || ""}</td>
      <td class="num">${s.weekend || ""}</td></tr>`;
  }).join("");
}

const sel = $("citySel");
Object.keys(DATA.districts).forEach((c) => {
  const o = document.createElement("option");
  o.value = c; o.textContent = c;
  sel.appendChild(o);
});

["area","whole","social","fund","food","days","extra","dep"].forEach((id) =>
  $(id).addEventListener("input", () => { compute(); renderDistricts(); })
);
document.querySelectorAll('input[name=mode]').forEach((el) =>
  el.addEventListener("change", () => { compute(); renderDistricts(); })
);
document.querySelectorAll('input[name=chan]').forEach((el) =>
  el.addEventListener("change", compute)
);
sel.addEventListener("change", renderDistricts);

compute();
renderDistricts();
renderJobs();
</script>
</body>
</html>
"""

out = os.path.join(HERE, "outputs", "01a09ac1-e853-7671-a83f-cea3e7f16019")
os.makedirs(out, exist_ok=True)
path = os.path.join(out, "江浙沪电气应届生净结余测算.html")
with open(path, "w", encoding="utf-8") as fh:
    fh.write(HTML.replace("__PAYLOAD__", PAYLOAD))
print("已生成", path, os.path.getsize(path), "字节")
