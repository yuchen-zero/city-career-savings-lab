# -*- coding: utf-8 -*-
"""Extract income, consumption and wage figures from statistics documents."""

import json
import re
import sys
import time

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# 每项为 (关键词, 前文必须包含, 前文禁止包含, 前文查看长度, 紧邻前一个字符禁止)
SPECS = [
    ("居民人均可支配收入", [], ["城镇", "农村", "城市", "乡村", "市区"], 6, []),
    ("居民人均可支配收入", ["城镇"], [], 6, []),
    ("居民人均可支配收入", ["农村"], [], 6, []),
    ("居民人均消费支出", [], ["城镇", "农村", "城市", "乡村", "市区"], 6, []),
    ("居民人均消费支出", ["城镇"], [], 6, []),
    ("居民人均消费支出", ["农村"], [], 6, []),
    ("居民人均生活消费支出", [], ["城镇", "农村"], 6, []),
    ("单位就业人员年平均工资", [], ["非私营", "私营"], 6, []),
    ("单位就业人员年平均工资", ["非私营"], [], 6, []),
    ("单位就业人员年平均工资", ["私营"], [], 6, ["非私营"]),
    ("单位就业人员年平均工资", ["全口径"], [], 6, []),
]

LABELS = [
    "全体居民人均可支配收入",
    "城镇居民人均可支配收入",
    "农村居民人均可支配收入",
    "全体居民人均消费支出",
    "城镇居民人均消费支出",
    "农村居民人均消费支出",
    "全体居民人均生活消费支出",
    "全口径单位就业人员年均工资",
    "非私营单位年均工资",
    "私营单位年均工资",
    "全口径年均工资",
]


def extract_text(url):
    response = requests.get(
        url,
        headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"},
        timeout=30,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    html = response.text
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", body)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    return re.sub(r"\s+", " ", text)


VALUE_RE = re.compile(r"(?:为|达|是|到)?\s*([0-9][0-9,\.]*)\s*元")


def _collect(text, keyword, must, forbid, window, immediate_forbid):
    values = []
    for match in re.finditer(re.escape(keyword), text):
        prefix = text[max(0, match.start() - window) : match.start()]
        if any(word in prefix for word in forbid):
            continue
        if must and not all(word in prefix for word in must):
            continue
        if immediate_forbid and any(prefix.endswith(word) for word in immediate_forbid):
            continue
        tail = text[match.end() : match.end() + 20]
        value_match = VALUE_RE.match(tail)
        if not value_match:
            continue
        try:
            values.append(float(value_match.group(1).replace(",", "")))
        except ValueError:
            continue
    return values


def parse(text):
    found = {}
    for label, spec in zip(LABELS, SPECS):
        keyword, must, forbid, window, immediate_forbid = spec
        values = _collect(text, keyword, must, forbid, window, immediate_forbid)
        if values:
            # 统计公报惯例是首次出现即为本年度头号数据，取首个而非最大值
            found[label] = values[0]
    return found


def main():
    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        targets = json.load(handle)

    merged_path = "ee-yzj-research/gh-tools/tj_values.json"
    out = {}
    if len(sys.argv) > 2 and sys.argv[2] == "--merge":
        try:
            with open(merged_path, "r", encoding="utf-8") as handle:
                out = json.load(handle)
        except (OSError, ValueError):
            out = {}

    for city, docs in targets.items():
        out.setdefault(city, {})
        for kind, url in docs.items():
            if not url:
                continue
            try:
                text = extract_text(url)
                values = parse(text)
                out[city][kind] = {"url": url, "values": values}
                print(
                    "%-5s %-10s %s"
                    % (
                        city,
                        kind,
                        "  ".join("%s=%s" % (k, int(v)) for k, v in values.items())
                        or "未提取到数值",
                    )
                )
            except Exception as exc:
                out[city][kind] = {"url": url, "error": repr(exc)}
                print("%-5s %-10s ERROR %r" % (city, kind, exc))
            time.sleep(0.8)

    with open("ee-yzj-research/gh-tools/tj_values.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print()
    print("已写入 tj_values.json")


if __name__ == "__main__":
    main()
