#!/usr/bin/env python3
"""Collect public search-result snippets as a fallback evidence source.

This script deliberately stores the search page and structured snippets only.
It does not bypass login walls, CAPTCHAs, paywalls, or platform access controls.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/156.0.0.0 Safari/537.36"
)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_sogou(html: str, query: str, page_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, str]] = []
    for block in soup.select("div.vrwrap"):
        heading = block.select_one("h3.vr-title a")
        if not heading:
            continue
        title = clean(heading.get_text(" ", strip=True))
        summary = block.select_one(".space-txt, .str-text, .fz-mid")
        snippet = clean(summary.get_text(" ", strip=True)) if summary else ""
        cite = block.select_one(".citeLinkClass")
        display_url = ""
        published = ""
        actual_url = ""
        if cite:
            spans = [clean(x.get_text(" ", strip=True)) for x in cite.select("span")]
            display_url = spans[0] if spans else ""
            date_like = [x for x in spans[1:] if re.search(r"20\d{2}-\d{2}-\d{2}", x)]
            published = date_like[0] if date_like else ""
        data_url = block.select_one("[data-url]")
        if data_url and data_url.get("data-url"):
            actual_url = data_url["data-url"].strip()
        if not actual_url and heading.get("href"):
            actual_url = urljoin(page_url, heading["href"])
        rows.append(
            {
                "query": query,
                "title": title,
                "snippet": snippet,
                "display_url": display_url,
                "url": actual_url,
                "published_at": published,
                "search_url": page_url,
            }
        )
    return rows


def parse_so360(html: str, query: str, page_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, str]] = []
    for block in soup.select("li.res-list"):
        heading = block.select_one("h3.res-title a")
        if not heading:
            continue
        title = clean(heading.get_text(" ", strip=True))
        summary = block.select_one(".res-desc, [data-result-summary]")
        snippet = clean(summary.get_text(" ", strip=True)) if summary else ""
        cite = block.select_one(".g-linkinfo cite")
        display_url = clean(cite.get_text(" ", strip=True)) if cite else ""
        published = ""
        date_node = block.select_one(".res-desc .g-c-gray")
        if date_node:
            date_match = re.search(r"20\d{2}-\d{2}-\d{2}", date_node.get_text(" ", strip=True))
            published = date_match.group(0) if date_match else ""
        actual_url = clean(heading.get("data-mdurl", "")) or urljoin(page_url, heading.get("href", ""))
        rows.append(
            {
                "query": query,
                "title": title,
                "snippet": snippet,
                "display_url": display_url,
                "url": actual_url,
                "published_at": published,
                "search_url": page_url,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--query-file")
    parser.add_argument("--query-set")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--engine", choices=["sogou", "so360"], default="sogou")
    args = parser.parse_args()

    queries = list(args.query)
    if args.query_file:
        query_doc = json.loads(Path(args.query_file).read_text(encoding="utf-8"))
        if args.query_set:
            queries.extend(query_doc[args.query_set])
        else:
            for values in query_doc.values():
                queries.extend(values)
    if not queries:
        parser.error("provide --query or --query-file")

    project = Path(args.project).resolve()
    raw_dir = project / "sources" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    collected_at = date.today().isoformat()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9"})

    all_rows: list[dict[str, str]] = []
    for index, query in enumerate(queries, start=1):
        params = {"query": query} if args.engine == "sogou" else {"q": query}
        base_url = "https://www.sogou.com/web" if args.engine == "sogou" else "https://www.so.com/s"
        search_url = requests.Request("GET", base_url, params=params).prepare().url
        response = session.get(search_url, timeout=30)
        response.raise_for_status()
        html_path = raw_dir / f"{args.engine}_{args.tag}_{index:02d}_{collected_at}.html"
        html_path.write_text(response.text, encoding="utf-8")
        parser_fn = parse_sogou if args.engine == "sogou" else parse_so360
        rows = parser_fn(response.text, query, search_url)
        for row in rows:
            row["collected_at"] = collected_at
            row["raw_file"] = str(html_path.relative_to(project))
        all_rows.extend(rows)
        print(f"[{index}/{len(queries)}] {query} -> {len(rows)} snippets")
        if index < len(queries):
            time.sleep(max(0.5, args.delay))

    json_path = raw_dir / f"search_snippets_{args.tag}_{collected_at}.json"
    csv_path = raw_dir / f"search_snippets_{args.tag}_{collected_at}.csv"
    json_path.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = [
        "query", "title", "snippet", "display_url", "url", "published_at",
        "search_url", "raw_file", "collected_at",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"wrote: {csv_path} ({len(all_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
