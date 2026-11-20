# Пара 5 · Практика: HTTP/1.1 и REST API

Файлы: `static_server.py` (задание 2), `rest_client.py` (задание 3), `mock_api.py` (учебный API для проверки без интернета), `www/` (тестовый сайт). Нужен Python 3 и `pip install requests`.

## 1. HTTP вручную через netcat

Запустите сервер из задания 2 (`python3 static_server.py www 8080`) и в другом окне:

```
$ nc localhost 8080
GET / HTTP/1.1
Host: localhost
Connection: close
<пустая строка + Enter>
```

Ответ:

```
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 254
Connection: close

<!doctype html> ...
```

Эксперименты (проверены на сервере из задания 2):

| Что изменить | Что придёт | Почему |
|---|---|---|
| убрать `Host` | `400 Bad Request` | в HTTP/1.1 `Host` обязателен |
| путь `/nope` | `404 Not Found` | файла нет |
| метод `POST /` | `405 Method Not Allowed` + `Allow: GET, HEAD` | метод известен, но не разрешён |
| путь `/../static_server.py` | `404 Not Found` | выход из каталога сайта заблокирован |
| `/style.css`, `/data.json` | `200`, `text/css`, `application/json` | `Content-Type` по расширению |

Если ответа нет, проверьте пустую строку в конце запроса. Если `nc` не установлен: `curl -v http://localhost:8080/` покажет тот же обмен.

## 2. Статический сервер

`python3 static_server.py [каталог] [порт]`: по умолчанию `www` и порт 8080.

- 200: файл найден; `Content-Type` по расширению (`mimetypes`), `Content-Length` считается в байтах
- 404: файла нет или путь выходит за каталог сайта
- 405: любой метод, кроме GET и HEAD (с заголовком `Allow`)
- 400: нет `Host` или кривая стартовая строка
- keep-alive: несколько запросов в одном TCP-соединении, `Connection: close` закрывает его; таймаут 10 с

## 3. REST-клиент

`python3 rest_client.py` ходит в публичный API (`jsonplaceholder.typicode.com`, нужен интернет).
Локально: `python3 mock_api.py &` и `python3 rest_client.py http://127.0.0.1:8000`.

Клиент делает весь CRUD для `/users`, везде ставит `timeout=5`, проверяет код ответа, разбирает JSON, выводит поля `id`, `name`, `email` и тело ошибки при 4xx/5xx. Сетевые сбои и таймаут не роняют программу.

## 4. Схема вызовов для /users

| Операция | Метод | URL | Тело запроса | Успех | Ошибки |
|---|---|---|---|---|---|
| Список | GET | `/users` | нет | 200 + массив | 500 |
| Один | GET | `/users/42` | нет | 200 + объект | 404 |
| Создать | POST | `/users` | `{"name":"Grace","email":"g@ex.com"}` | 201 + `Location: /users/42` | 400 неверный JSON, 409 дубль email |
| Заменить | PUT | `/users/42` | полный объект `{"name":...,"email":...}` | 200 + объект (или 204) | 400, 404 |
| Изменить часть | PATCH | `/users/42` | `{"email":"new@ex.com"}` | 200 + объект (или 204) | 400, 404 |
| Удалить | DELETE | `/users/42` | нет | 204, тела нет | 404 |

Идемпотентность: GET, PUT, DELETE безопасно повторять; POST при повторе создаст второй ресурс или даст 409. Повторный DELETE вернёт 404, но состояние сервера не изменится.

Типичный сценарий: `POST /users` → 201 и `Location` → `GET /users/42` → 200 → `PUT` → 200 → `PATCH` → 200 → `DELETE` → 204 → `GET /users/42` → 404.
