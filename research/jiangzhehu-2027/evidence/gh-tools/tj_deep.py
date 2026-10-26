# -*- coding: utf-8 -*-
"""Second pass: follow channel pages to locate statistical communiques."""

import json
import re
import time
from urllib.parse import urljoin

import requests

from tj_sites import SITES

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

CHANNEL_WORDS = ["统计公报", "统计数据", "统计分析", "数据发布", "统计年鉴", "数据"]
ARTICLE_WORDS = [
    "统计公报",
    "年平均工资",
    "居民收入",
    "消费支出",
    "人民生活",
    "人均可支配收入",
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
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()


def links_of(html, base):
    out = []
    seen = set()
    for match in LINK_RE.finditer(html):
        href = match.group(1).strip()
        text = clean(match.group(2))
        if not text or not href or href.lower().startswith("javascript"):
            continue
        url = urljoin(base, href)
        if url in seen:
            continue
        seen.add(url)
        out.append((text, url))
    return out


def main():
    result = {}
    for city, base in SITES.items():
        entry = {"base": base, "channels": [], "articles": [], "errors": []}
        try:
            html, final = fetch(base)
        except Exception as exc:
            entry["errors"].append("home: %r" % (exc,))
            result[city] = entry
            print("FAIL %-4s 首页 %r" % (city, exc))
            continue

        all_links = links_of(html, final)

        # 首页直接命中的文章
        for text, url in all_links:
            if any(w in text for w in ARTICLE_WORDS):
                entry["articles"].append({"text": text[:90], "url": url, "from": "home"})

        # 找到频道页
        channels = []
        for text, url in all_links:
            if any(w in text for w in CHANNEL_WORDS) and len(text) <= 12:
                channels.append((text, url))
        entry["channels"] = [{"text": t, "url": u} for t, u in channels[:6]]

        for text, url in channels[:6]:
            try:
                sub_html, sub_final = fetch(url, timeout=20)
            except Exception as exc:
                entry["errors"].append("%s: %r" % (url, exc))
                continue
            for sub_text, sub_url in links_of(sub_html, sub_final):
                if any(w in sub_text for w in ARTICLE_WORDS):
                    entry["articles"].append(
                        {"text": sub_text[:90], "url": sub_url, "from": text}
                    )
            time.sleep(0.6)

        result[city] = entry
        print(
            "%-4s 频道 %d 篇候选文章 %d"
            % (city, len(entry["channels"]), len(entry["articles"]))
        )
        time.sleep(0.8)

    with open("ee-yzj-research/gh-tools/tj_deep.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print("已写入 tj_deep.json")


if __name__ == "__main__":
    main()
