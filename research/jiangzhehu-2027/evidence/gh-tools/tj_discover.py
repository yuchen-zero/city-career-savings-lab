# -*- coding: utf-8 -*-
"""Find income and consumption-expenditure pages on city statistics sites."""

import json
import re
import sys
import time
from urllib.parse import urljoin

import requests

from tj_sites import SITES

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

KEYWORDS = [
    "居民收入",
    "消费支出",
    "人均可支配收入",
    "人民生活",
    "统计公报",
    "人均消费",
]

LINK_RE = re.compile(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)


def fetch(url, timeout=25):
    response = requests.get(
        url,
        headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"},
        timeout=timeout,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text, response.url


def clean(text):
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else list(SITES)
    out_path = "ee-yzj-research/gh-tools/tj_pages.json"
    results = {}

    for city in only:
        base = SITES.get(city)
        if not base:
            print("SKIP %s" % city)
            continue
        entry = {"base": base, "home_status": "", "candidates": []}
        try:
            html, final_url = fetch(base)
            entry["home_status"] = "ok"
            seen = set()
            for match in LINK_RE.finditer(html):
                href = match.group(1).strip()
                text = clean(match.group(2))
                if not text or len(text) < 4:
                    continue
                if not any(k in text for k in KEYWORDS):
                    continue
                url = urljoin(final_url, href)
                if url in seen:
                    continue
                seen.add(url)
                entry["candidates"].append({"text": text[:80], "url": url})
            print(
                "OK   %-4s %-34s 命中 %d 条"
                % (city, base, len(entry["candidates"]))
            )
        except Exception as exc:
            entry["home_status"] = "error: %r" % (exc,)
            print("FAIL %-4s %-34s %r" % (city, base, exc))
        results[city] = entry
        time.sleep(1.0)

    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=False, indent=2)
    print()
    print("已写入 %s" % out_path)


if __name__ == "__main__":
    main()
