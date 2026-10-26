#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "sources" / "raw" / "zhaopin_candidates" / "candidate_pool.json"
OUT_DIR = PROJECT / "sources" / "raw" / "zhaopin_candidates"


def parse_salary(text: str) -> tuple[float | None, float | None, int, str]:
    text = (text or "").strip().replace(" ", "")
    if not text or "面议" in text:
        return None, None, 0, "negotiable"
    months_match = re.search(r"[·・](\d{2})薪", text)
    months = int(months_match.group(1)) if months_match else 0
    core = re.sub(r"[·・]\d{2}薪", "", text)
    if "/天" in core or "元/天" in core:
        return None, None, months, "daily"
    multiplier = 10000 if "万" in core else 1
    nums = [float(x) * multiplier for x in re.findall(r"\d+(?:\.\d+)?", core)]
    if len(nums) >= 2:
        return min(nums[0], nums[1]), max(nums[0], nums[1]), months, "monthly"
    if len(nums) == 1:
        return nums[0], nums[0], months, "monthly"
    return None, None, months, "unknown"


def target_location(row: dict) -> bool:
    loc = " ".join([row.get("job_title", ""), row.get("work_address", ""), row.get("district", "")])
    return any(token in loc for token in ("临港", "南汇新城", "滴水湖"))


def education_flags(text: str) -> tuple[bool, bool]:
    text = text or ""
    bachelor = "本科" in text or "大专" in text or "学历不限" in text
    higher_only = ("硕士" in text or "博士" in text) and "本科" not in text and "大专" not in text
    return bachelor and not higher_only, higher_only


def entry_level(text: str) -> bool:
    return any(token in (text or "") for token in ("经验不限", "应届", "在校", "无经验"))


def work_conditions(description: str) -> dict:
    desc = description or ""
    if re.search(r"周末双休|双休", desc):
        weekend = "double"
    elif re.search(r"单休|周六上班", desc):
        weekend = "single"
    elif re.search(r"轮班|倒班|夜班|四班|值班", desc):
        weekend = "rotating"
    else:
        weekend = "unknown"

    if re.search(r"不出差|无需出差|不需要出差", desc):
        trip = "none"
    elif re.search(r"偶尔出差", desc):
        trip = "occasional"
    elif re.search(r"频繁出差|长期出差", desc):
        trip = "frequent"
    elif re.search(r"需出差|出差", desc):
        trip = "required"
    else:
        trip = "unknown"

    if re.search(r"包住|提供住宿|免费住宿|员工宿舍|宿舍", desc):
        accommodation = "provided"
    elif re.search(r"住房补贴|租房补贴|住宿补贴", desc):
        accommodation = "subsidy"
    elif re.search(r"不包住|不提供住宿|无住宿", desc):
        accommodation = "none"
    else:
        accommodation = "unknown"

    return {"weekend": weekend, "trip_requirement": trip, "accommodation": accommodation}


def main() -> None:
    records = json.loads(SOURCE.read_text(encoding="utf-8"))
    deduped: dict[str, dict] = {}
    for row in records:
        job_id = row["job_id"]
        if job_id not in deduped:
            deduped[job_id] = {**row, "queries": [row["query"]]}
        elif row["query"] not in deduped[job_id]["queries"]:
            deduped[job_id]["queries"].append(row["query"])

    normalized = []
    for row in deduped.values():
        low, high, months, salary_type = parse_salary(row["salary_text"])
        bachelor_ok, higher_only = education_flags(
            " ".join([row["job_title"], row["education"], row["description"]])
        )
        text_all = " ".join([row["job_title"], row["employment_type"], row["description"]])
        explicit_2027 = "2027" in text_all and any(
            token in text_all for token in ("2027届", "2027 届", "2027校招", "2027 校招")
        )
        campus = "校园" in row["employment_type"] or explicit_2027
        target = target_location(row)
        entry = entry_level(row["experience"])
        conditions = work_conditions(row["description"])
        relevance_text = " ".join([row["job_title"], row["job_family"], row["description"][:1000]])
        relevant = any(
            token in relevance_text.lower()
            for token in ("电气", "自动化", "设备", "厂务", "机电", "控制", "电力", "电子", "plc", "mes")
        )

        if not target:
            bucket = "exclude_location"
        elif higher_only:
            bucket = "exclude_education"
        elif not relevant:
            bucket = "exclude_relevance"
        elif not bachelor_ok:
            bucket = "exclude_education"
        elif not entry:
            bucket = "exclude_experience"
        elif salary_type != "monthly" or low is None or high is None:
            bucket = "exclude_salary_negotiable"
        elif explicit_2027 and campus:
            bucket = "direct_2027"
        else:
            bucket = "comparable_entry"

        normalized.append(
            {
                **row,
                "queries": "|".join(row["queries"]),
                "salary_min": low,
                "salary_max": high,
                "salary_mid": (low + high) / 2 if low is not None and high is not None else None,
                "salary_months": months or 12,
                "salary_months_explicit": bool(months),
                "salary_type_normalized": salary_type,
                "explicit_2027": explicit_2027,
                "campus": campus,
                "bachelor_eligible": bachelor_ok,
                "entry_level": entry,
                "target_location": target,
                "relevant_family": relevant,
                "bucket": bucket,
                **conditions,
            }
        )

    normalized.sort(key=lambda r: (r["bucket"], r["company"], r["job_title"]))
    columns = list(normalized[0].keys()) if normalized else []
    with (OUT_DIR / "normalized_jobs.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(normalized)

    summary: dict[str, list[dict]] = {}
    for row in normalized:
        summary.setdefault(row["bucket"], []).append(row)
    (OUT_DIR / "job_analysis.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({bucket: len(rows) for bucket, rows in summary.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
