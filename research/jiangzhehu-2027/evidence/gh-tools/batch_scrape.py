# -*- coding: utf-8 -*-
"""Batch driver for boss-zhipin-scraper.

Runs one scrape per (city, keyword, experience) combination, skipping
combinations that already have a saved result file, then merges everything
into a single JSON and CSV.
"""

import argparse
import csv
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRAPER = os.path.join(HERE, "boss-zhipin-scraper", "scripts", "boss_cdp_raw.py")

JOB_FIELDS = [
    "job_id",
    "title",
    "salary",
    "location",
    "tags",
    "skills",
    "welfare",
    "boss_name",
    "boss_title",
    "boss_active_status",
    "company_scale",
    "company_stage",
    "company_industry",
    "job_link",
    "source_city",
    "source_keyword",
    "source_experience",
    "scraped_at",
]


def slug(value):
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")


def already_done(path):
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError, ValueError):
        return False
    return isinstance(data.get("jobs"), list)


def run_one(city, keyword, experience, degree, pages, raw_dir, sleep_seconds):
    name = "__".join([slug(city), slug(keyword), "exp" + str(experience)])
    out_json = os.path.join(raw_dir, name + ".json")
    if already_done(out_json):
        return "skip", out_json

    cmd = [
        sys.executable,
        SCRAPER,
        "--keyword",
        keyword,
        "--city",
        city,
        "--pages",
        str(pages),
        "--no-detail",
        "--experience",
        str(experience),
        "--degree",
        str(degree),
        "--output",
        out_json,
    ]
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            env=env,
        )
        ok = proc.returncode == 0 and os.path.exists(out_json)
        time.sleep(sleep_seconds)
        return ("ok" if ok else "fail"), out_json
    except subprocess.TimeoutExpired:
        return "fail", out_json


def load_raw(raw_dir):
    jobs = {}
    files = sorted(glob.glob(os.path.join(raw_dir, "*.json")))
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError, ValueError):
            continue
        city = data.get("city", "")
        keyword = data.get("keyword", "")
        filters = data.get("filters") or {}
        for job in data.get("jobs", []):
            job_id = job.get("job_id")
            if not job_id:
                continue
            record = dict(job)
            record["source_city"] = city
            record["source_keyword"] = keyword
            record["source_experience"] = filters.get("experience", "")
            record["scraped_at"] = data.get("scraped_at", "")
            jobs.setdefault(job_id, record)
    return list(jobs.values())


def write_outputs(jobs, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    combined_json = os.path.join(out_dir, "combined_jobs.json")
    combined_csv = os.path.join(out_dir, "combined_jobs.csv")

    with open(combined_json, "w", encoding="utf-8") as handle:
        json.dump(jobs, handle, ensure_ascii=False, indent=2)

    with open(combined_csv, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=JOB_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for job in jobs:
            writer.writerow({key: job.get(key, "") for key in JOB_FIELDS})

    return combined_json, combined_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cities", required=True, help="逗号分隔的城市列表")
    parser.add_argument("--keywords", required=True, help="逗号分隔的关键词列表")
    parser.add_argument("--experiences", default="102,101", help="经验筛选代码，逗号分隔")
    parser.add_argument("--degree", default="203", help="学历筛选代码")
    parser.add_argument("--pages", type=int, default=1, help="每个组合抓取页数")
    parser.add_argument(
        "--big-cities", default="", help="需要多抓页数的城市，逗号分隔"
    )
    parser.add_argument("--big-pages", type=int, default=3, help="大城市的抓取页数")
    parser.add_argument("--outdir", required=True, help="输出目录")
    parser.add_argument("--sleep", type=float, default=2.5, help="每次抓取之间的间隔秒数")
    parser.add_argument(
        "--merge-only", action="store_true", help="只合并已有结果，不发起抓取"
    )
    args = parser.parse_args()

    cities = [c.strip() for c in args.cities.split(",") if c.strip()]
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    experiences = [e.strip() for e in args.experiences.split(",") if e.strip()]
    big_cities = {c.strip() for c in args.big_cities.split(",") if c.strip()}

    raw_dir = os.path.join(args.outdir, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    if args.merge_only:
        jobs = load_raw(raw_dir)
        combined_json, combined_csv = write_outputs(jobs, args.outdir)
        print("合并完成，去重后职位总数: %d" % len(jobs))
        print("合并 JSON: %s" % combined_json)
        print("合并 CSV : %s" % combined_csv)
        return

    total = len(cities) * len(keywords) * len(experiences)
    done = skipped = failed = 0
    started = time.time()

    print(
        "计划组合数 %d (城市 %d x 关键词 %d x 经验档 %d)"
        % (total, len(cities), len(keywords), len(experiences))
    )
    for city in cities:
        pages = args.big_pages if city in big_cities else args.pages
        for keyword in keywords:
            for experience in experiences:
                done += 1
                status, path = run_one(
                    city, keyword, experience, args.degree, pages, raw_dir, args.sleep
                )
                if status == "skip":
                    skipped += 1
                    tag = "跳过(已有)"
                elif status == "ok":
                    tag = "完成"
                else:
                    failed += 1
                    tag = "失败"
                elapsed = time.time() - started
                print(
                    "[%3d/%3d] %-4s %s | %s | 经验%s | %d页"
                    % (done, total, tag, city, keyword, experience, pages)
                    + ("  (%.0fs)" % elapsed)
                )
                sys.stdout.flush()

    jobs = load_raw(raw_dir)
    combined_json, combined_csv = write_outputs(jobs, args.outdir)

    print("")
    print("=" * 60)
    print("完成 %d, 跳过 %d, 失败 %d" % (done - skipped - failed, skipped, failed))
    print("去重后职位总数: %d" % len(jobs))
    print("合并 JSON: %s" % combined_json)
    print("合并 CSV : %s" % combined_csv)
    print("耗时: %.1f 秒" % (time.time() - started))


if __name__ == "__main__":
    main()
