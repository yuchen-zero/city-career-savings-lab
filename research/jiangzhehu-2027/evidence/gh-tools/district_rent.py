# -*- coding: utf-8 -*-
"""District-level rent and shared-rent levels from creprice city pages."""

import json
import re
import sys
import time
import urllib.parse
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"

CITIES = {
    "上海": "sh", "南京": "nj", "苏州": "su", "杭州": "hz", "宁波": "nb",
    "无锡": "wx", "常州": "cz", "南通": "nt", "温州": "wz", "嘉兴": "jx",
    "绍兴": "sx", "金华": "jh", "台州": "tz", "湖州": "huzhou",
    "扬州": "yz", "镇江": "zhenjiang", "泰州": "taizhoujs", "徐州": "xz",
    "盐城": "yancheng", "淮安": "ha", "连云港": "lyg", "宿迁": "sq",
    "衢州": "quzhou", "舟山": "zs", "丽水": "ls",
}

ROW = re.compile(r"([\u4e00-\u9fa5]{2,10}区|[\u4e00-\u9fa5]{2,10}县|[\u4e00-\u9fa5]{2,10}市)\t([\d.]+)")


def http_json(path, method="GET"):
    request = urllib.request.Request(CDP + path, method=method)
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


class Session:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=90)
        self.counter = 0

    def send(self, method, params=None):
        self.counter += 1
        self.ws.send(json.dumps({"id": self.counter, "method": method, "params": params or {}}))
        deadline = time.time() + 90
        while time.time() < deadline:
            raw = self.ws.recv()
            if not raw:
                continue
            data = json.loads(raw)
            if data.get("id") == self.counter:
                return data
        raise TimeoutError(method)


def page_text(url, wait=12.0):
    tab = http_json("/json/new?" + urllib.parse.quote("about:blank", safe=""), method="PUT")
    session = Session(tab["webSocketDebuggerUrl"])
    try:
        session.send("Page.enable")
        session.send("Runtime.enable")
        session.send("Page.navigate", {"url": url})
        time.sleep(wait)
        result = session.send(
            "Runtime.evaluate",
            {"expression": "document.body.innerText", "returnByValue": True},
        )
        return result["result"]["result"].get("value") or ""
    finally:
        try:
            session.ws.close()
        except Exception:
            pass
        try:
            http_json("/json/close/" + tab["id"])
        except Exception:
            pass


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else "lease"
    cities = sys.argv[2:] if len(sys.argv) > 2 else list(CITIES)
    rows = []
    for city in cities:
        code = CITIES.get(city)
        if not code:
            print("SKIP %s（未知城市码）" % city)
            continue
        url = "https://www.creprice.cn/urban/%s.html?type=%s" % (code, kind)
        try:
            text = page_text(url)
        except Exception as exc:
            print("FAIL %-4s %r" % (city, exc))
            continue
        header = "房租" if kind == "lease" else "合租"
        marker = "区市县%s平均单价" % header
        idx = text.find(marker)
        body = text[idx : idx + 1200] if idx >= 0 else text
        found = ROW.findall(body)
        for name, value in found:
            rows.append({"城市": city, "区县": name, "元每平米每月" if kind == "lease" else "元每月": float(value), "类型": header})
        print("%-4s %-4s 命中 %d 个区县" % (city, header, len(found)))
        time.sleep(2.5)

    out = "ee-yzj-research/gh-tools/district_%s.json" % kind
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
    print()
    print("已写入 %s，共 %d 条" % (out, len(rows)))
    for row in rows:
        print("   %-4s %-10s %8.2f" % (row["城市"], row["区县"], list(row.values())[2]))


if __name__ == "__main__":
    main()
