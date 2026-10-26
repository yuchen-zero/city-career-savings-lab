# -*- coding: utf-8 -*-
"""Extract links from JavaScript-rendered pages through Chrome DevTools Protocol."""

import json
import re
import sys
import time
import urllib.parse
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"

JS = """
(() => {
  const out = [];
  document.querySelectorAll('a').forEach(a => {
    const t = (a.textContent || '').replace(/\\s+/g, ' ').trim();
    if (t && a.href) out.push({text: t.slice(0, 90), href: a.href});
  });
  return JSON.stringify(out);
})()
"""


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


def page_links(url, wait=8.0):
    tab = http_json("/json/new?" + urllib.parse.quote("about:blank", safe=""), method="PUT")
    session = Session(tab["webSocketDebuggerUrl"])
    try:
        session.send("Page.enable")
        session.send("Runtime.enable")
        session.send("Page.navigate", {"url": url})
        time.sleep(wait)
        result = session.send(
            "Runtime.evaluate",
            {"expression": JS, "returnByValue": True, "awaitPromise": True},
        )
        payload = result["result"]["result"].get("value") or "[]"
        return json.loads(payload)
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
    keywords = sys.argv[1]
    urls = sys.argv[2:]
    pattern = re.compile(keywords)
    out = {}
    for url in urls:
        try:
            links = page_links(url)
        except Exception as exc:
            print("ERROR %s : %r" % (url, exc))
            continue
        hits = []
        seen = set()
        for link in links:
            if not (pattern.search(link["text"]) or pattern.search(link["href"])):
                continue
            if link["href"] in seen:
                continue
            seen.add(link["href"])
            hits.append(link)
        out[url] = hits
        print("=== %s  (共 %d 链接，命中 %d) ===" % (url, len(links), len(hits)))
        for link in hits[:14]:
            print("   %-50s %s" % (link["text"][:48], link["href"][:115]))
    with open("ee-yzj-research/gh-tools/cdp_links.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
