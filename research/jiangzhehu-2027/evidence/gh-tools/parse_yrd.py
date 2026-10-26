# -*- coding: utf-8 -*-
"""Parse the Yangtze River Delta city table from the Taizhou yearbook."""

import csv
import os
import zipfile

import xlrd

ZIP = "ee-yzj-research/gh-tools/downloads/taizhou_tjnj_2025.zip"
OUT = "ee-yzj-research/gh-tools/长三角各城市2024.csv"

CITIES = [
    "上海市", "南京市", "无锡市", "徐州市", "常州市", "苏州市", "南通市",
    "连云港市", "淮安市", "盐城市", "扬州市", "镇江市", "泰州市", "宿迁市",
    "杭州市", "宁波市", "温州市", "嘉兴市", "湖州市", "绍兴市", "金华市",
    "衢州市", "舟山市", "台州市", "丽水市",
]


def decode(name):
    try:
        return name.encode("cp437").decode("gbk")
    except Exception:
        return name


def cell(sheet, row, col):
    if row >= sheet.nrows or col >= sheet.ncols:
        return ""
    value = sheet.cell_value(row, col)
    if isinstance(value, float):
        return "" if value == 0 else round(value, 1)
    return str(value).replace("\n", "").strip()


def read_table(zip_file, member):
    sheet = xlrd.open_workbook(file_contents=zip_file.read(member)).sheet_by_index(0)
    return sheet


def main():
    archive = zipfile.ZipFile(ZIP)
    members = {os.path.basename(decode(n)): n for n in archive.namelist()}

    rows = []
    sheet = read_table(archive, members["20-03.xls"])
    headers = [cell(sheet, 1, c) or cell(sheet, 0, c) for c in range(sheet.ncols)]
    for r in range(sheet.nrows):
        region = cell(sheet, r, 0)
        if region not in CITIES:
            continue
        rows.append(
            {
                "城市": region.replace("市", ""),
                "年份": 2024,
                "居民人均可支配收入": cell(sheet, r, 2),
                "城镇居民人均可支配收入": cell(sheet, r, 3),
                "农村居民人均可支配收入": cell(sheet, r, 4),
                "市区CPI": cell(sheet, r, 5),
                "来源": "台州统计年鉴2025 表20-3 长江三角洲各城市（原始来源为各市统计局）",
            }
        )

    # 浙江各市消费支出来自同一本年鉴的表19-10
    consume = {}
    sheet19 = read_table(archive, members["19-10.xls"])
    for r in range(sheet19.nrows):
        region = cell(sheet19, r, 0)
        if region in CITIES:
            consume[region.replace("市", "")] = {
                "全体居民人均消费支出": cell(sheet19, r, 2),
                "城镇居民人均消费支出": cell(sheet19, r, 3),
                "农村居民人均消费支出": cell(sheet19, r, 5),
            }

    for row in rows:
        extra = consume.get(row["城市"])
        if extra:
            row.update(extra)

    fields = [
        "城市", "年份", "居民人均可支配收入", "城镇居民人均可支配收入",
        "农村居民人均可支配收入", "全体居民人均消费支出",
        "城镇居民人均消费支出", "农村居民人均消费支出", "市区CPI", "来源",
    ]
    with open(OUT, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(rows, key=lambda x: -float(x["居民人均可支配收入"] or 0)):
            writer.writerow({k: row.get(k, "") for k in fields})

    print("已写入 %s，覆盖 %d 个城市" % (OUT, len(rows)))
    print()
    print("%-6s %10s   %8s %8s %8s" % ("城市", "全体收入", "城镇收入", "农村收入", "全体消费"))
    for row in sorted(rows, key=lambda x: -float(x["居民人均可支配收入"] or 0)):
        print(
            "%-6s %10s   %8s %8s %8s"
            % (
                row["城市"],
                row["居民人均可支配收入"],
                row["城镇居民人均可支配收入"],
                row["农村居民人均可支配收入"],
                row.get("全体居民人均消费支出", "-"),
            )
        )


if __name__ == "__main__":
    main()
