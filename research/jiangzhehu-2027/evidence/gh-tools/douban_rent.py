# -*- coding: utf-8 -*-
"""Extract rent listings (district, price, layout) from Douban rent groups."""

import html
import json
import re
import time

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

GROUPS = {
    "上海": ["shanghaizufang", "364511"],
    "苏州": ["364511", "85743", "551329"],
    "南京": ["145583", "585224", "352686"],
    "杭州": ["340633", "578360", "467221"],
    "宁波": ["228862", "605039"],
}

# 显式带单位的价格
EXPLICIT_PATTERNS = [
    r"(\d{3,6})\s*元\s*/?\s*月",
    r"(\d{3,6})\s*元",
    r"月租\s*(\d{3,6})",
    r"租金\s*(\d{3,6})",
    r"💰\s*(\d{3,6})",
    r"价格\s*(\d{3,6})",
    r"(\d{3,6})\s*(?:一)?个月",
    r"(\d{3,6})\s*块",
    r"[¥￥]\s*(\d{3,6})",
    r"(\d{3,6})\s*(?:/|每)?\s*月",
    r"(\d{3,6})\s*(?:一个月|每月|月)",
]
# k 写法，例如 3.7k / 3K
K_PATTERN = r"(\d(?:\.\d)?)\s*[kK](?![a-zA-Z])"

# 需求方帖子，不是房源，必须剔除
EXCLUDE_TITLE = re.compile(
    r"求租|找房|求合租|想租|寻找|预算|求租|找室友$|转租还是|租房求助|有没有.*租"
)
# 含联系方式的标题，裸数字极可能是电话号码
CONTACT_TITLE = re.compile(r"电话|微信|手机|📱|☎|联系")

DISTRICTS = {
    "上海": ["浦东", "闵行", "徐汇", "静安", "黄浦", "长宁", "普陀", "虹口", "杨浦",
             "宝山", "嘉定", "松江", "青浦", "奉贤", "金山", "崇明", "临港", "张江",
             "陆家嘴", "漕河泾", "莘庄", "七宝", "五角场", "虹桥", "南翔", "三林"],
    "苏州": ["姑苏", "虎丘", "吴中", "相城", "吴江", "园区", "新区", "昆山", "常熟",
             "张家港", "太仓", "独墅湖", "湖东", "湖西", "甪直"],
    "南京": ["玄武", "秦淮", "建邺", "鼓楼", "浦口", "栖霞", "雨花台", "江宁", "六合",
             "溧水", "高淳", "仙林", "河西", "新街口", "江北"],
    "杭州": ["上城", "拱墅", "西湖", "滨江", "萧山", "余杭", "临平", "钱塘", "富阳",
             "临安", "桐庐", "建德", "未来科技城", "钱江新城", "下沙", "城西"],
    "宁波": ["海曙", "江北", "北仑", "镇海", "鄞州", "奉化", "余姚", "慈溪", "象山",
             "宁海", "东部新城", "高新区"],
}

LAYOUT_PATTERNS = [
    (r"一室户|单间|独厨独卫|独卫|独立厨卫", "单间/一室户"),
    (r"一室一厅|一房一厅|1室1厅", "一室一厅"),
    (r"两室|二室|两房|二房|2室", "两室"),
    (r"三室|三房|3室", "三室"),
    (r"主卧", "主卧"),
    (r"次卧", "次卧"),
    (r"合租|室友|找室友", "合租"),
    (r"整租", "整租"),
]

LINK_RE = re.compile(
    r'<td class="title">\s*<a href="([^"]+)"\s*title="([^"]*)"', re.S
)


def parse_price(title):
    """Return (price, confidence) where confidence is explicit or inferred."""
    if EXCLUDE_TITLE.search(title):
        return None, "demand_side"
    for pattern in EXPLICIT_PATTERNS:
        for match in re.finditer(pattern, title):
            value = int(match.group(1))
            if 300 <= value <= 50000:
                return value, "explicit"
    match = re.search(K_PATTERN, title)
    if match:
        value = int(float(match.group(1)) * 1000)
        if 300 <= value <= 50000:
            return value, "explicit"
    if CONTACT_TITLE.search(title):
        return None, "has_contact"
    # 兜底：裸数字，只认标题末尾 12 字内的数字，避免误抓地铁线号和电话
    tail_start = max(0, len(title) - 12)
    for match in re.finditer(r"(?<![\d])(\d{3,5})(?![\d])", title):
        start, end = match.span(1)
        if start < tail_start:
            continue
        after = title[end : end + 3]
        before = title[max(0, start - 3) : start]
        if re.match(r"号线|号|年|月|室|楼|层", after):
            continue
        if re.search(r"号线|号$|第|预算|电话", before):
            continue
        value = int(match.group(1))
        if 500 <= value <= 30000:
            return value, "inferred"
    return None, None


def parse_district(title, city):
    for name in DISTRICTS.get(city, []):
        if name in title:
            return name
    return ""


def parse_layout(title):
    for pattern, label in LAYOUT_PATTERNS:
        if re.search(pattern, title):
            return label
    return ""


def fetch_group(session, group, pages=1):
    items = []
    for page in range(1, pages + 1):
        url = "https://www.douban.com/group/%s/discussion?start=%d" % (group, (page - 1) * 25)
        try:
            response = session.get(url, timeout=25)
        except Exception:
            continue
        if response.status_code != 200:
            continue
        for href, raw_title in LINK_RE.findall(response.text):
            items.append((href, html.unescape(raw_title).strip()))
        time.sleep(1.2)
    return items


def main():
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})

    rows = []
    for city, groups in GROUPS.items():
        seen = set()
        for group in groups:
            for href, title in fetch_group(session, group, pages=5):
                if href in seen:
                    continue
                seen.add(href)
                price, confidence = parse_price(title)
                if confidence in ("demand_side", "has_contact"):
                    continue
                rows.append(
                    {
                        "城市": city,
                        "小组": group,
                        "话题标题": title,
                        "月租": price,
                        "价格置信度": confidence or "",
                        "区": parse_district(title, city),
                        "户型": parse_layout(title),
                        "链接": href,
                    }
                )
        with_price = [r for r in rows if r["城市"] == city and r["月租"]]
        print(
            "%-4s 抓取 %d 条，其中可解析价格 %d 条"
            % (city, len(set(r["链接"] for r in rows if r["城市"] == city)), len(with_price))
        )

    out_path = "ee-yzj-research/gh-tools/douban_rent.json"
    if not rows:
        print("本次抓取 0 条，判定为被限流，保留原有文件不覆盖")
        return
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)
    print("已写入 %s，共 %d 条" % (out_path, len(rows)))


if __name__ == "__main__":
    main()
