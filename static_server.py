#!/usr/bin/env python3
"""Практика 2: статический HTTP/1.1-сервер на сокетах.

Запуск: python3 static_server.py [каталог] [порт]
Отдаёт файлы с 200, 404 (нет файла), 405 (метод не GET/HEAD),
400 (кривой запрос / нет Host). Content-Type выбирается по расширению.
"""
import mimetypes
import os
import socket
import sys
import threading

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "www")
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
REASONS = {200: "OK", 400: "Bad Request", 404: "Not Found",
           405: "Method Not Allowed", 505: "HTTP Version Not Supported"}
KNOWN = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}


def build(status, body=b"", ctype="text/plain; charset=utf-8", extra=None,
          close=False, head=False):
    """Собирает ответ. Content-Length считаем в БАЙТАХ, а не в символах."""
    lines = [f"HTTP/1.1 {status} {REASONS[status]}",
             f"Content-Type: {ctype}",
             f"Content-Length: {len(body)}",
             f"Connection: {'close' if close else 'keep-alive'}"]
    lines += [f"{k}: {v}" for k, v in (extra or {}).items()]
    raw = ("\r\n".join(lines) + "\r\n\r\n").encode("ascii")
    return raw if head else raw + body


def read_head(conn, buf):
    """Читает из сокета, пока не встретится пустая строка (конец заголовков)."""
    while b"\r\n\r\n" not in buf:
        chunk = conn.recv(4096)
        if not chunk:
            return None, buf
        buf += chunk
        if len(buf) > 65536:          # защита от бесконечных заголовков
            return None, buf
    head, _, rest = buf.partition(b"\r\n\r\n")
    return head.decode("iso-8859-1"), rest


def resolve(path):
    """URL-путь -> файл внутри ROOT или None (защита от ../)."""
    path = path.split("?", 1)[0].split("#", 1)[0]
    if path.endswith("/"):
        path += "index.html"
    full = os.path.abspath(os.path.join(ROOT, path.lstrip("/")))
    if full != ROOT and not full.startswith(ROOT + os.sep):
        return None
    return full if os.path.isfile(full) else None


def handle(conn, addr):
    conn.settimeout(10)               # keep-alive не должен висеть вечно
    buf = b""
    try:
        while True:                   # несколько запросов в одном соединении
            head, buf = read_head(conn, buf)
            if head is None:
                break
            lines = head.split("\r\n")
            parts = lines[0].split(" ")
            headers = {}
            for ln in lines[1:]:
                if ":" in ln:
                    k, v = ln.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            if len(parts) != 3 or not parts[2].startswith("HTTP/"):
                conn.sendall(build(400, b"Bad request line\n", close=True))
                break
            method, target, version = parts
            close = (headers.get("connection", "").lower() == "close"
                     or version == "HTTP/1.0")

            if version not in ("HTTP/1.1", "HTTP/1.0"):
                resp = build(505, b"Use HTTP/1.1\n", close=True)
            elif version == "HTTP/1.1" and "host" not in headers:
                resp = build(400, b"Host header required\n", close=True)
                close = True
            elif method not in ("GET", "HEAD"):
                # знаем метод, но для статики он не разрешён -> 405 + Allow
                resp = build(405, b"Method not allowed\n",
                             extra={"Allow": "GET, HEAD"}, close=close)
            else:
                path = resolve(target)
                if path is None:
                    resp = build(404, b"Not found\n", close=close,
                                 head=(method == "HEAD"))
                else:
                    with open(path, "rb") as f:
                        body = f.read()
                    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
                    if ctype.startswith("text/") or ctype in ("application/json", "application/javascript"):
                        ctype += "; charset=utf-8"
                    resp = build(200, body, ctype, close=close,
                                 head=(method == "HEAD"))
            conn.sendall(resp)
            print(f"{addr[0]} {method} {target} -> {resp.split(b' ', 2)[1].decode()}")
            if close:
                break
    except socket.timeout:
        pass
    finally:
        conn.close()


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(16)
    print(f"Serving {ROOT} on http://0.0.0.0:{PORT}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
