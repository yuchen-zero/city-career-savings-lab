# -*- coding: utf-8 -*-
"""Turn combined BOSS scrape output into an Excel workbook for review."""

import argparse
import json
import os
import re

import pandas as pd

SALARY_RANGE = re.compile(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)K")
SALARY_DAILY = re.compile(r"(\d+)-(\d+)元/天")
MONTH_COUNT = re.compile(r"·(\d+)薪")

DAYS_PER_MONTH = 21.75

ANON_MARKERS = ("某", "保密", "上市公司", "有限公司")


def parse_salary(text):
    """Return (low_k, high_k, months, note) for a salary string."""
    text = (text or "").strip()
    if not text:
        return None, None, None, "无薪资"
    if "面议" in text or "元/天" not in text and not SALARY_RANGE.search(text):
        if "元/天" in text:
            match = SALARY_DAILY.search(text)
            if match:
                low = float(match.group(1)) * DAYS_PER_MONTH / 1000
                high = float(match.group(2)) * DAYS_PER_MONTH / 1000
                return round(low, 1), round(high, 1), 12, "日薪换算"
        return None, None, None, "面议" if "面议" in text else "无法解析"

    match = SALARY_RANGE.search(text)
    if not match:
        return None, None, None, "无法解析"
    low = float(match.group(1))
    high = float(match.group(2))
    months_match = MONTH_COUNT.search(text)
    months = int(months_match.group(1)) if months_match else 12
    note = "含%d薪" % months if months != 12 else ""
    return low, high, months, note


def is_anonymous(name):
    name = (name or "").strip()
    if not name:
        return False
    return name.startswith("某") or "某" in name[:6]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="combined_jobs.json 路径")
    parser.add_argument("--output", required=True, help="输出的 xlsx 路径")
    parser.add_argument("--title", default="试点样本", help="工作表标题前缀")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as handle:
        jobs = json.load(handle)

    rows = []
    for job in jobs:
        low, high, months, note = parse_salary(job.get("salary", ""))
        location = job.get("location", "") or ""
        parts = [p for p in location.split("·") if p]
        city = job.get("source_city") or (parts[0] if parts else "")
        district = parts[1] if len(parts) > 1 else ""
        tags = job.get("tags") or ""
        rows.append(
            {
                "城市": city,
                "区": district,
                "商圈": parts[2] if len(parts) > 2 else "",
                "岗位名称": job.get("title", ""),
                "薪资原文": job.get("salary", ""),
                "月薪下限K": low,
                "月薪上限K": high,
                "月数": months,
                "年薪下限万": round(low * months / 10, 1) if low and months else None,
                "年薪上限万": round(high * months / 10, 1) if high and months else None,
                "经验与学历": tags,
                "公司": job.get("boss_name", ""),
                "公司匿名": "是" if is_anonymous(job.get("boss_name", "")) else "",
                "公司规模": job.get("company_scale", ""),
                "行业": job.get("company_industry", ""),
                "来源城市": job.get("source_city", ""),
                "来源关键词": job.get("source_keyword", ""),
                "经验筛选档": job.get("source_experience", ""),
                "薪资解析备注": note,
                "岗位链接": job.get("job_link", ""),
            }
        )

    df = pd.DataFrame(rows)
    parsed = df.dropna(subset=["月薪下限K"])

    city_summary = (
        parsed.groupby("城市")
        .agg(
            岗位数=("岗位名称", "count"),
            月薪下限中位数=("月薪下限K", "median"),
            月薪上限中位数=("月薪上限K", "median"),
            下限最低=("月薪下限K", "min"),
            上限最高=("月薪上限K", "max"),
        )
        .round(1)
        .reset_index()
        .sort_values("月薪下限中位数", ascending=False)
    )

    keyword_summary = (
        parsed.groupby("来源关键词")
        .agg(
            岗位数=("岗位名称", "count"),
            月薪下限中位数=("月薪下限K", "median"),
            月薪上限中位数=("月薪上限K", "median"),
        )
        .round(1)
        .reset_index()
        .sort_values("月薪下限中位数", ascending=False)
    )

    experience_summary = (
        parsed.groupby("经验筛选档")
        .agg(
            岗位数=("岗位名称", "count"),
            月薪下限中位数=("月薪下限K", "median"),
            月薪上限中位数=("月薪上限K", "median"),
        )
        .round(1)
        .reset_index()
    )
    experience_summary["经验档含义"] = experience_summary["经验筛选档"].map(
        {"102": "应届生", "101": "经验不限"}
    )

    # 相对本地市场中位数判定异常高薪，避免用绝对阈值误伤高薪城市
    city_ceiling = parsed.groupby("城市")["月薪上限K"].median()
    df["本地上限中位数"] = df["城市"].map(city_ceiling)
    anonymous_outlier = (df["公司匿名"] == "是") & (
        df["月薪上限K"] >= df["本地上限中位数"] * 1.5
    )
    low_bar_outlier = (
        df["经验与学历"].str.contains("学历不限", na=False)
        & df["经验与学历"].str.contains("经验不限", na=False)
        & (df["月薪上限K"] >= df["本地上限中位数"] * 2.0)
    )
    suspicious = df[anonymous_outlier | low_bar_outlier].copy()
    reasons = []
    for _, row in suspicious.iterrows():
        notes = []
        if row["公司匿名"] == "是":
            notes.append("公司名称被平台匿名")
        if "学历不限" in str(row["经验与学历"]) and "经验不限" in str(row["经验与学历"]):
            notes.append("经验与学历均不限")
        notes.append(
            "薪资上限为本地中位数的 %.1f 倍" % (row["月薪上限K"] / row["本地上限中位数"])
        )
        reasons.append("；".join(notes))
    suspicious["可疑原因"] = reasons

    district_summary = (
        parsed[parsed["区"] != ""]
        .groupby(["城市", "区"])
        .agg(
            岗位数=("岗位名称", "count"),
            月薪下限中位数=("月薪下限K", "median"),
            月薪上限中位数=("月薪上限K", "median"),
        )
        .round(1)
        .reset_index()
        .sort_values(["城市", "月薪下限中位数"], ascending=[True, False])
    )

    summary_rows = [
        ("样本来源", "BOSS直聘 应届生与经验不限筛选 + 本科学历筛选"),
        ("岗位总数（去重后）", len(df)),
        ("可解析薪资的岗位数", len(parsed)),
        ("无法解析（面议等）", len(df) - len(parsed)),
        ("覆盖城市", "、".join(sorted(df["城市"].unique()))),
        ("覆盖关键词", "、".join(sorted(df["来源关键词"].unique()))),
        ("月薪下限中位数（全体）", round(parsed["月薪下限K"].median(), 1)),
        ("月薪上限中位数（全体）", round(parsed["月薪上限K"].median(), 1)),
        ("公司匿名的岗位数", int((df["公司匿名"] == "是").sum())),
        ("被标记为可疑的岗位数", len(suspicious)),
    ]
    summary = pd.DataFrame(summary_rows, columns=["项目", "数值"])

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with pd.ExcelWriter(args.output, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="概览", index=False)
        city_summary.to_excel(writer, sheet_name="城市汇总", index=False)
        keyword_summary.to_excel(writer, sheet_name="关键词汇总", index=False)
        experience_summary.to_excel(writer, sheet_name="经验档对比", index=False)
        district_summary.to_excel(writer, sheet_name="区级汇总", index=False)
        suspicious.to_excel(writer, sheet_name="可疑岗位", index=False)
        df.to_excel(writer, sheet_name="岗位明细", index=False)

        for sheet in writer.sheets.values():
            for column_cells in sheet.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in column_cells)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(
                    max(width + 2, 10), 46
                )
            sheet.freeze_panes = "A2"

    print("已生成: %s" % args.output)
    print("岗位总数 %d，可解析薪资 %d，可疑标记 %d" % (len(df), len(parsed), len(suspicious)))
    print(city_summary.to_string(index=False))


if __name__ == "__main__":
    main()
