# -*- coding: utf-8 -*-
"""Batch driver that collects job descriptions for work-condition analysis."""

import argparse
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRAPER = os.path.join(HERE, "boss-zhipin-scraper", "scripts", "boss_cdp_raw.py")


def slug(value):
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")


def done(path):
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError, ValueError):
        return False
    return isinstance(data, list) and len(data) > 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cities", required=True)
    parser.add_argument("--keywords", required=True)
    parser.add_argument("--experience", default="102")
    parser.add_argument("--degree", default="203")
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--max-details", type=int, default=10)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    cities = [c.strip() for c in args.cities.split(",") if c.strip()]
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    raw_dir = os.path.join(args.outdir, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    total = len(cities) * len(keywords)
    index = 0
    started = time.time()

    print("计划 %d 个组合，每个最多 %d 条 JD" % (total, args.max_details))
    for city in cities:
        for keyword in keywords:
            index += 1
            name = "__".join([slug(city), slug(keyword)])
            list_path = os.path.join(raw_dir, name + "_list.json")
            detail_path = os.path.join(raw_dir, name + "_detail.json")
            if done(detail_path):
                print("[%2d/%2d] 跳过 %s %s（已有详情）" % (index, total, city, keyword))
                continue

            cmd = [
                sys.executable,
                SCRAPER,
                "--keyword", keyword,
                "--city", city,
                "--pages", str(args.pages),
                "--experience", args.experience,
                "--degree", args.degree,
                "--output", list_path,
                "--detail-output", detail_path,
                "--max-details", str(args.max_details),
            ]
            env = dict(os.environ)
            env["PYTHONIOENCODING"] = "utf-8"
            print(
                "[%2d/%2d] 开始 %s %s（已用时 %.0f 分钟）"
                % (index, total, city, keyword, (time.time() - started) / 60)
            )
            sys.stdout.flush()
            try:
                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=3600,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                print("    超时跳过")
            count = 0
            if os.path.exists(detail_path):
                try:
                    with open(detail_path, "r", encoding="utf-8") as handle:
                        count = len(json.load(handle))
                except Exception:
                    count = 0
            print(
                "[%2d/%2d] 完成 %s %s -> %d 条详情（累计 %.0f 分钟）"
                % (index, total, city, keyword, count, (time.time() - started) / 60)
            )
            sys.stdout.flush()

    files = glob.glob(os.path.join(raw_dir, "*_detail.json"))
    print()
    print("=" * 60)
    print("完成 %d 个组合，详情文件 %d 个，总耗时 %.0f 分钟"
          % (total, len(files), (time.time() - started) / 60))


if __name__ == "__main__":
    main()
