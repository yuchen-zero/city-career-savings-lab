import fs from "node:fs/promises";
import path from "node:path";

const project = path.resolve("C:/Users/askl1/Documents/ChatGPT/ChatGPT/lingang-ee-research");
const rawDir = path.join(project, "sources", "raw", "zhaopin_search");
const outDir = path.join(project, "sources", "raw", "zhaopin_candidates");
await fs.mkdir(rawDir, { recursive: true });
await fs.mkdir(outDir, { recursive: true });

const queries = [
  "临港 电气",
  "临港 自动化",
  "临港 设备工程师",
  "临港 厂务工程师",
  "临港 电气工程师 应届",
  "临港 自动化工程师 应届",
  "2027届 临港",
  "2027届 临港 电气",
  "2027届 临港 自动化",
  "南汇新城 电气",
  "南汇新城 自动化",
  "南汇新城 设备工程师",
  "中微公司 临港",
  "中微公司 2027",
  "盛美 临港",
  "盛美 2027",
  "中芯国际 临港",
  "中芯国际 2027",
  "上海电气 临港",
  "积塔半导体 临港",
  "宁德时代 临港 电气",
  "乐孜芯创 临港",
  "临港新片区 电气",
  "滴水湖 电气",
  "泥城 电气",
  "书院 电气",
  "临港 机电",
  "临港 设备维护",
  "临港 应届生",
  "临港 管培生",
  "上海 2027届 电气 本科",
  "上海 2027届 自动化 本科",
  "上海 2027届 设备 本科",
  "上海 2027届 硬件 本科",
  "上海 2027届 电子 本科",
  "浦东 2027届 电气 本科",
  "临港 2027届 硬件",
  "临港 2027届 电力电子",
  "临港 2027届 现场调试",
  "临港 2027届 工程实施",
];

function htmlToText(html = "") {
  return String(html)
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(div|p|li|h\d)>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\r/g, "")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{2,}/g, "\n")
    .trim();
}

function parseInitialState(html) {
  const marker = "<script>__INITIAL_STATE__=";
  const start = html.indexOf(marker);
  if (start < 0) throw new Error("__INITIAL_STATE__ marker not found");
  const from = start + marker.length;
  const end = html.indexOf("</script>", from);
  if (end < 0) throw new Error("__INITIAL_STATE__ closing tag not found");
  return JSON.parse(html.slice(from, end));
}

const records = [];
const seen = new Set();

for (let queryIndex = 0; queryIndex < queries.length; queryIndex += 1) {
  const query = queries[queryIndex];
  const url = `https://sou.zhaopin.com/?jl=538&kw=${encodeURIComponent(query)}&p=1`;
  const slug = String(queryIndex + 1).padStart(2, "0");
  const rawFile = path.join(rawDir, `${slug}_p1.html`);
  let html;
  try {
    html = await fs.readFile(rawFile, "utf8");
  } catch {
    const response = await fetch(url, {
      redirect: "follow",
      headers: {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/156 Safari/537.36",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.5",
      },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status} for ${query}`);
    html = await response.text();
    await fs.writeFile(rawFile, html, "utf8");
    await new Promise((resolve) => setTimeout(resolve, 1200));
  }

  const state = parseInitialState(html);
  for (const item of state.positionList ?? []) {
    const detail = item?.jobDetailData?.position ?? {};
    const base = detail.base ?? {};
    const desc = detail.desc ?? {};
    const dateInfo = detail.date ?? {};
    const workLocation = detail.workLocation ?? {};
    const jobType = detail.jobType ?? {};
    const jobId = String(base.positionNumber ?? item.positionNumber ?? item.number ?? base.positionId ?? "");
    if (!jobId) continue;
    const key = `${jobId}|${query}`;
    if (seen.has(key)) continue;
    seen.add(key);
    records.push({
      query,
      search_page: 1,
      collected_at: "2026-10-26",
      raw_file: path.relative(project, rawFile).replaceAll("\\", "/"),
      job_id: jobId,
      source_url: `https://www.zhaopin.com/jobdetail/${jobId}.htm`,
      mobile_url: `https://m.zhaopin.com/jobs/${jobId}.htm`,
      job_title: base.positionName ?? item.name ?? "",
      company: item.companyName ?? "",
      company_id: item.companyNumber ?? "",
      city: workLocation.positionWorkCity || item.workCity || "上海",
      district: workLocation.positionCityDistrict || item.cityDistrict || "",
      work_address: workLocation.workAddress ?? "",
      salary_text: base.salary ?? item.salary60 ?? "",
      education: base.education ?? item.education ?? "",
      experience: base.positionWorkingExp ?? item.workingExp ?? "",
      employment_type: base.workType ?? item.workType ?? "",
      publish_time: dateInfo.positionPublishTime || item.publishTime || "",
      job_family: jobType.subJobTypeLevelName || item.subJobTypeLevelName || "",
      labels: Array.isArray(desc.labels) ? desc.labels.join("|") : "",
      description: htmlToText(desc.description ?? ""),
      welfare: Array.isArray(desc.welfareTags) ? desc.welfareTags.join("|") : "",
    });
  }

  console.log(`[${queryIndex + 1}/${queries.length}] ${query}: ${state.positionList?.length ?? 0} cards`);
}

await fs.writeFile(path.join(outDir, "candidate_pool.json"), JSON.stringify(records, null, 2), "utf8");

const columns = [
  "query", "search_page", "collected_at", "raw_file", "job_id", "source_url", "mobile_url",
  "job_title", "company", "company_id", "city", "district", "work_address", "salary_text",
  "education", "experience", "employment_type", "publish_time", "job_family", "labels",
  "description", "welfare",
];
const escapeCsv = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
const csv = [columns.join(","), ...records.map((row) => columns.map((col) => escapeCsv(row[col])).join(","))].join("\r\n");
await fs.writeFile(path.join(outDir, "candidate_pool.csv"), "\uFEFF" + csv, "utf8");

const uniqueJobs = new Set(records.map((row) => row.job_id));
console.log(JSON.stringify({ queries: queries.length, cardRecords: records.length, uniqueJobs: uniqueJobs.size }, null, 2));
