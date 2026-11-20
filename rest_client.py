#!/usr/bin/env python3
"""Практика 3: REST-клиент (requests).

Запуск: python3 rest_client.py [базовый_URL]
Без аргумента ходит в публичный API https://jsonplaceholder.typicode.com
(нужен интернет). Локально: python3 mock_api.py & python3 rest_client.py http://127.0.0.1:8000
Правила: всегда timeout, проверка кода ответа, разбор JSON, вывод причины ошибки.
"""
import sys

import requests

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://jsonplaceholder.typicode.com").rstrip("/")
TIMEOUT = 5  # секунд на соединение и на ответ


def call(method, path, **kw):
    """Один запрос: печатает метод, URL, статус; возвращает (response | None)."""
    url = BASE + path
    try:
        r = requests.request(method, url, timeout=TIMEOUT, **kw)
    except requests.exceptions.Timeout:
        print(f"{method} {path} -> таймаут ({TIMEOUT} c)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"{method} {path} -> сетевая ошибка: {e}")
        return None
    print(f"{method:6} {path:12} -> {r.status_code} {r.reason}")
    if not r.ok:  # 4xx/5xx: тело ошибки часто содержит причину
        print("         причина:", r.text.strip()[:120] or "(пустое тело)")
    return r


def show(user):
    print(f"         id={user.get('id')}  name={user.get('name')}  email={user.get('email')}")


def main():
    # R: список
    r = call("GET", "/users", headers={"Accept": "application/json"})
    if r is not None and r.ok:
        users = r.json()
        print(f"         получено пользователей: {len(users)}")
        for u in users[:3]:
            show(u)

    # C: создать -> 201 + Location
    r = call("POST", "/users", json={"name": "Grace", "email": "grace@ex.com"})
    new_id = None
    if r is not None and r.status_code == 201:
        print("         Location:", r.headers.get("Location"))
        data = r.json()
        show(data)
        new_id = data.get("id")

    if new_id is None:
        return
    path = f"/users/{new_id}"

    # R: один ресурс
    r = call("GET", path)
    if r is not None and r.ok:
        show(r.json())

    # U: PUT (заменить целиком) и PATCH (частично)
    r = call("PUT", path, json={"name": "Grace Hopper", "email": "grace@ex.com"})
    if r is not None and r.ok:
        show(r.json())
    r = call("PATCH", path, json={"email": "hopper@ex.com"})
    if r is not None and r.ok:
        show(r.json())

    # D: удалить -> 204 без тела, повторный GET -> 404
    r = call("DELETE", path)
    if r is not None:
        print("         тело пустое:", r.content == b"")
    call("GET", path)


if __name__ == "__main__":
    main()
