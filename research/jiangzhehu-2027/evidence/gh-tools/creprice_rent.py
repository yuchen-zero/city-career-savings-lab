# -*- coding: utf-8 -*-
"""Scrape city and district rent levels from creprice.cn through CDP."""

import json
import re
import sys
import time
import urllib.parse
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"

SCROLL_JS = """
(async () => {
  for (let i = 0; i < 25; i++) {
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(r => setTimeout(r, 900));
  }
  return document.body.innerText;
})()
"""

# 先点掉「查看更多」展开完整榜单，再滚动加载
EXPAND_SCROLL_JS = """
(async () => {
  const clickMore = () => {
    let clicked = 0;
    document.querySelectorAll('a,button,span,div').forEach(el => {
      const t = (el.textContent || '').trim();
      if (t === '查看更多' || t === '展开' || t === '加载更多') {
        try { el.click(); clicked++; } catch (e) {}
      }
    });
    return clicked;
  };
  for (let i = 0; i < 12; i++) {
    clickMore();
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(r => setTimeout(r, 1200));
  }
  return document.body.innerText;
})()
"""


def http_json(path, method="GET"):
    request = urllib.request.Request(CDP + path, method=method)
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


class Session:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=120)
        self.counter = 0

    def send(self, method, params=None):
        self.counter += 1
        self.ws.send(json.dumps({"id": self.counter, "method": method, "params": params or {}}))
        deadline = time.time() + 120
        while time.time() < deadline:
            raw = self.ws.recv()
            if not raw:
                continue
            data = json.loads(raw)
            if data.get("id") == self.counter:
                return data
        raise TimeoutError(method)


def render_scrolled(url, wait=9.0, expand=False):
    tab = http_json("/json/new?" + urllib.parse.quote("about:blank", safe=""), method="PUT")
    session = Session(tab["webSocketDebuggerUrl"])
    try:
        session.send("Page.enable")
        session.send("Runtime.enable")
        session.send("Page.navigate", {"url": url})
        time.sleep(wait)
        result = session.send(
            "Runtime.evaluate",
            {
                "expression": EXPAND_SCROLL_JS if expand else SCROLL_JS,
                "returnByValue": True,
                "awaitPromise": True,
            },
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


TARGET = [
    "上海", "南京", "无锡", "徐州", "常州", "苏州", "南通", "连云港", "淮安",
    "盐城", "扬州", "镇江", "泰州", "宿迁", "杭州", "宁波", "温州", "嘉兴",
    "湖州", "绍兴", "金华", "衢州", "舟山", "台州", "丽水",
]

ROW_RE = re.compile(
    r"(?m)^(\d{1,4})\s+([\u4e00-\u9fa5]{2,8})\s+([\u4e00-\u9fa5]{2,8})\s+(\d+(?:\.\d+)?)\s*$"
)


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.creprice.cn/rankprice/rent/11.html"
    out_name = sys.argv[2] if len(sys.argv) > 2 else "creprice_city_rent.json"
    text = render_scrolled(url, expand=("rentjoin" in url))
    print("渲染正文 %d 字" % len(text))

    rows = []
    for match in ROW_RE.finditer(text):
        rank, city, province, rent = match.groups()
        if city in TARGET:
            rows.append(
                {"城市": city, "省份": province, "排名": int(rank), "租金元每平米每月": float(rent)}
            )

    seen = set()
    unique = []
    for row in rows:
        if row["城市"] in seen:
            continue
        seen.add(row["城市"])
        unique.append(row)

    path = "ee-yzj-research/gh-tools/" + out_name
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(unique, fh, ensure_ascii=False, indent=2)

    print("命中江浙沪城市 %d / %d" % (len(unique), len(TARGET)))
    missing = [c for c in TARGET if c not in seen]
    print("未命中:", "、".join(missing) if missing else "无")
    print()
    for row in sorted(unique, key=lambda r: -r["租金元每平米每月"]):
        print(
            "  #%-4d %-4s %-4s %6.2f 元/㎡/月   30㎡约 %5.0f 元   20㎡约 %5.0f 元"
            % (
                row["排名"],
                row["城市"],
                row["省份"],
                row["租金元每平米每月"],
                row["租金元每平米每月"] * 30,
                row["租金元每平米每月"] * 20,
            )
        )
    print()
    print("已写入", path)


if __name__ == "__main__":
    main()
