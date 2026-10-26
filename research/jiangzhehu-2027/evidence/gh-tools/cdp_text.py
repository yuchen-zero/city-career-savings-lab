# -*- coding: utf-8 -*-
"""Render pages through CDP and save the visible text for extraction."""

import json
import sys
import time
import urllib.parse
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"


def http_json(path, method="GET"):
    request = urllib.request.Request(CDP + path, method=method)
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


class Session:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=60)
        self.counter = 0

    def send(self, method, params=None):
        self.counter += 1
        self.ws.send(json.dumps({"id": self.counter, "method": method, "params": params or {}}))
        deadline = time.time() + 60
        while time.time() < deadline:
            raw = self.ws.recv()
            if not raw:
                continue
            data = json.loads(raw)
            if data.get("id") == self.counter:
                return data
        raise TimeoutError(method)


def render_text(url, wait=9.0):
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
                "expression": "document.body ? document.body.innerText : ''",
                "returnByValue": True,
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


def main():
    targets = json.load(open(sys.argv[1], "r", encoding="utf-8"))
    store = {}
    for city, docs in targets.items():
        for kind, url in docs.items():
            try:
                text = render_text(url)
                store.setdefault(city, {})[kind] = {"url": url, "text": text}
                print("%-5s %-14s 渲染 %d 字" % (city, kind, len(text)))
            except Exception as exc:
                print("%-5s %-14s ERROR %r" % (city, kind, exc))
    with open("ee-yzj-research/gh-tools/tj_rendered.json", "w", encoding="utf-8") as fh:
        json.dump(store, fh, ensure_ascii=False, indent=2)
    print("已写入 tj_rendered.json")


if __name__ == "__main__":
    main()
