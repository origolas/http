#!/usr/bin/env python3
"""Учебный REST API /users в памяти (для проверки клиента без интернета).
Запуск: python3 mock_api.py [порт]   (по умолчанию 8000)
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

USERS = {1: {"id": 1, "name": "Ada", "email": "ada@ex.com"},
         2: {"id": 2, "name": "Linus", "email": "linus@ex.com"}}
NEXT_ID = [3]


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def reply(self, code, obj=None, headers=None):
        body = b"" if obj is None else json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        if obj is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def uid(self):
        p = self.path.rstrip("/").split("/")
        if p[:2] != ["", "users"] or len(p) > 3:
            return "bad"
        if len(p) == 2:
            return None
        return int(p[2]) if p[2].isdigit() else "bad"

    def body(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
            return data if isinstance(data, dict) else None
        except ValueError:
            return None

    def do_GET(self):
        u = self.uid()
        if u == "bad":
            return self.reply(404, {"error": "not found"})
        if u is None:
            return self.reply(200, list(USERS.values()))
        self.reply(200, USERS[u]) if u in USERS else self.reply(404, {"error": "user not found"})

    def do_POST(self):
        if self.uid() is not None:
            return self.reply(404, {"error": "not found"})
        d = self.body()
        if not d or "name" not in d or "email" not in d:
            return self.reply(400, {"error": "name and email required"})
        if any(x["email"] == d["email"] for x in USERS.values()):
            return self.reply(409, {"error": "email already exists"})
        i = NEXT_ID[0]; NEXT_ID[0] += 1
        USERS[i] = {"id": i, "name": d["name"], "email": d["email"]}
        self.reply(201, USERS[i], {"Location": f"/users/{i}"})

    def do_PUT(self):
        u = self.uid()
        if u in (None, "bad") or u not in USERS:
            return self.reply(404, {"error": "user not found"})
        d = self.body()
        if not d or "name" not in d or "email" not in d:
            return self.reply(400, {"error": "PUT needs full resource"})
        USERS[u] = {"id": u, "name": d["name"], "email": d["email"]}
        self.reply(200, USERS[u])

    def do_PATCH(self):
        u = self.uid()
        if u in (None, "bad") or u not in USERS:
            return self.reply(404, {"error": "user not found"})
        d = self.body()
        if d is None:
            return self.reply(400, {"error": "invalid JSON"})
        USERS[u].update({k: v for k, v in d.items() if k in ("name", "email")})
        self.reply(200, USERS[u])

    def do_DELETE(self):
        u = self.uid()
        if u in (None, "bad") or u not in USERS:
            return self.reply(404, {"error": "user not found"})
        del USERS[u]
        self.reply(204)

    def log_message(self, fmt, *a):
        print(f"{self.command} {self.path} -> {a[1]}")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Mock API on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
