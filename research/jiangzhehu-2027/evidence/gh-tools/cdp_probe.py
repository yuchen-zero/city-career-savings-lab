# -*- coding: utf-8 -*-
"""Probe a URL through the already-running Chrome DevTools Protocol endpoint."""

import json
import sys
import time
import urllib.parse
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"


def http_json(path, method="GET"):
    request = urllib.request.Request(CDP + path, method=method)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def new_tab(url):
    quoted = urllib.parse.quote(url, safe="")
    try:
        return http_json("/json/new?" + quoted, method="PUT")
    except Exception:
        return http_json("/json/new?" + quoted)


class Session:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=40)
        self.counter = 0

    def send(self, method, params=None, session_id=None):
        self.counter += 1
        message = {"id": self.counter, "method": method, "params": params or {}}
        if session_id:
            message["sessionId"] = session_id
        self.ws.send(json.dumps(message))
        deadline = time.time() + 40
        while time.time() < deadline:
            raw = self.ws.recv()
            if not raw:
                continue
            data = json.loads(raw)
            if data.get("id") == self.counter:
                return data
        raise TimeoutError(method)

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def probe(url, wait_seconds=9):
    tab = new_tab("about:blank")
    session = Session(tab["webSocketDebuggerUrl"])
    try:
        session.send("Page.enable")
        session.send("Runtime.enable")
        session.send("Page.navigate", {"url": url})
        time.sleep(wait_seconds)
        title = session.send(
            "Runtime.evaluate",
            {"expression": "document.title", "returnByValue": True},
        )
        body = session.send(
            "Runtime.evaluate",
            {
                "expression": "document.body ? document.body.innerText.slice(0, 1200) : ''",
                "returnByValue": True,
            },
        )
        html_len = session.send(
            "Runtime.evaluate",
            {"expression": "document.documentElement.outerHTML.length", "returnByValue": True},
        )
        return {
            "url": url,
            "title": title["result"]["result"].get("value"),
            "html_length": html_len["result"]["result"].get("value"),
            "text": body["result"]["result"].get("value"),
        }
    finally:
        session.close()
        try:
            http_json("/json/close/" + tab["id"])
        except Exception:
            pass


def main():
    for target in sys.argv[1:]:
        try:
            result = probe(target)
            print("=" * 60)
            print("URL   : %s" % result["url"])
            print("TITLE : %s" % result["title"])
            print("HTML  : %s chars" % result["html_length"])
            text = (result["text"] or "").strip().replace("\n", " | ")
            print("TEXT  : %s" % text[:700])
        except Exception as exc:
            print("=" * 60)
            print("URL   : %s" % target)
            print("ERROR : %r" % (exc,))


if __name__ == "__main__":
    main()
