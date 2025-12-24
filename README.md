# Restify

Backend + минимальный UI для рекомендаций мест отдыха

Restify — небольшой сервис на FastAPI, который хранит места в базе данных, позволяет пользователям оставлять отзывы, строит простые рекомендации и предоставляет чат‑помощника, который **опирается на реальные места из БД** (grounding)

---

## Что реализовано

### Основные функции
- Регистрация и вход пользователей по JWT
- Rate limiting на auth эндпоинтах
  - `/auth/register` — 3 запроса за 60 секунд на IP
  - `/auth/token` — 10 запросов за 60 секунд на IP
- API мест с фильтрами и пагинацией
  - поиск по названию `q`
  - фильтры `city`, `category`, `min_rating`
  - пагинация `limit` и `offset`
- Отзывы к местам (оценка 1–5 + опциональный текст)
- Агрегаты по месту
  - `avg_rating`
  - `reviews_count`
- Рекомендации на основе профиля пользователя (предпочитаемые категории)
- Чат‑помощник
  - grounding: бэкенд выбирает top‑N мест из БД и передаёт модели как список кандидатов
  - модель получает явное правило предлагать **только** из кандидатов
- Суммаризация отзывов

### Импорт мест (Geoapify)
- Места **не создаются через API**
- На старте, если таблица `places` пустая, приложение может импортировать места из Geoapify
- Импорт выполняется только если задан `GEOAPIFY_KEY`

---

## Технологии

- Python 3.11+
- FastAPI
- SQLAlchemy (ORM)
- Pydantic (схемы и настройки)
- Passlib (хеширование паролей)
- aiohttp (импортер Geoapify)
- Hugging Face Transformers (локальная LLM)
- UI на Vanilla HTML/CSS/JS, раздаётся со страницы `/ui`

---

## Структура проекта

```
app/
  core/              настройки, auth‑хелперы, rate limiting
  db/                SQLAlchemy engine, session, CRUD‑хелперы
  models/            SQLAlchemy модели
  parsers/           импорт из Geoapify
  routers/           FastAPI роутеры (auth, places, reviews, recs, chat)
  schemas/           Pydantic модели запросов/ответов
  services/          фасад LLM, кеширование, рекомендации
  static/            минимальный UI (index.html, styles.css, app.js)
tests/               pytest тесты
docker-compose.yml   app + postgres
Dockerfile           сборка контейнера
.env.example         пример переменных окружения
```

---

## Быстрый старт (локально, uvicorn)

### 1) Создать venv и поставить зависимости

Windows PowerShell:

```bash
python -m venv .venv
source ./.venv/Scripts/activate
pip install -r requirements.txt
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Настроить переменные окружения

Скопировать пример:

Windows:

```powershell
copy .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Минимальная dev‑конфигурация:

```
ENV=dev
DATABASE_URL=sqlite:///./app.db
APP_SECRET_KEY=dev-secret-change-me
GEOAPIFY_KEY=4cdf4771ad1f49a1b85f1bf4e104eceb
LLM_PROVIDER=disabled
```

### 3) Запустить сервер

Рекомендуемая команда для разработки:

```bash
uvicorn app.main:app --reload --reload-dir app
```

Флаг `--reload-dir app` важен, если включать локальную LLM  
Hugging Face скачивает файлы модели, и если reloader следит за всей папкой проекта, он может непредсказуемо перезапускать сервер во время скачивания

Открыть:
- UI: http://127.0.0.1:8000/ui/
- Swagger: http://127.0.0.1:8000/docs

---

## Postgres

Есть два варианта

### Вариант A запуск полностью через docker compose

```bash
docker compose up --build
```

Открыть:
- UI: http://127.0.0.1:8000/ui/
- Docs: http://127.0.0.1:8000/docs

По умолчанию в compose LLM выключена, чтобы не скачивать большую модель внутри контейнера

### Вариант B Postgres в Docker, бэкенд локально через uvicorn

Запустить Postgres:

Windows cmd(разделитель ^)/PowerShell(разделитель `):

```bat
docker run --name restify-db ^
  -e POSTGRES_USER=restify ^
  -e POSTGRES_PASSWORD=restify ^
  -e POSTGRES_DB=restify ^
  -p 5432:5432 ^
  -v restify_pgdata:/var/lib/postgresql/data ^
  -d postgres:16-alpine
```

Задать в `.env`:

```
DATABASE_URL=postgresql+psycopg2://restify:restify@localhost:5432/restify
```

Поставить драйвер Postgres в venv:

```bash
pip install psycopg2-binary
```

Далее запускать uvicorn как обычно

---

## Переменные окружения

Основные переменные из `.env`

- `ENV` `dev` или `prod`
  - в `dev` статика `/ui` отдаётся с `Cache-Control: no-store`, чтобы правки UI подхватывались сразу
- `DATABASE_URL`
  - sqlite пример `sqlite:///./app.db`
  - postgres пример `postgresql+psycopg2://user:pass@host:5432/db`
- `APP_SECRET_KEY` секрет для подписи JWT
- `ACCESS_TOKEN_EXP_MINUTES` TTL access токена в минутах
- `LOG_LEVEL` по умолчанию `INFO`
- `LOG_DIR` по умолчанию `./logs`

Geoapify:
- `GEOAPIFY_URL` по умолчанию `https://api.geoapify.com/v2/places`
- `GEOAPIFY_KEY` если пустой, импорт пропускается

LLM:
- `LLM_PROVIDER` `hf_local` или `disabled`
- `HF_MODEL_ID` по умолчанию `Qwen/Qwen3-4B-Instruct-2507`
- `HF_DEVICE` `auto` `cpu` `cuda`
- `HF_MAX_NEW_TOKENS` по умолчанию 256
- `HF_TEMPERATURE` по умолчанию 0.7
- `HF_TOP_P` по умолчанию 0.9
- `LLM_CACHE_TTL_SECONDS` TTL кеша ответов LLM

---

## Примеры использования API

### Регистрация

Windows (curl):

```bat
curl -X POST http://127.0.0.1:8000/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"password\":\"secret123\"}"
```

Ответ содержит `access_token`

### Вход

Логин использует OAuth2 password form

```bat
curl -X POST http://127.0.0.1:8000/auth/token ^
  -H "Content-Type: application/x-www-form-urlencoded" ^
  -d "username=test@example.com&password=secret123"
```

### Текущий пользователь

```bat
curl http://127.0.0.1:8000/me ^
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Обновить профиль

Предпочитаемые категории задаются строкой через запятую

```bat
curl -X PUT http://127.0.0.1:8000/me/profile ^
  -H "Authorization: Bearer YOUR_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"city\":\"Москва\",\"preferred_categories\":\"Кафе, Парк\"}"
```

### Список мест с фильтрами и пагинацией

```bash
curl "http://127.0.0.1:8000/places?city=Москва&category=Кафе&min_rating=4&limit=20&offset=0"
```

### Добавить отзыв

```bat
curl -X POST http://127.0.0.1:8000/places/1/reviews ^
  -H "Authorization: Bearer YOUR_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"rating\":5,\"text\":\"Отличное место\"}"
```

### Рекомендации

```bat
curl http://127.0.0.1:8000/recommendations ^
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Чат с grounding по БД

```bat
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Authorization: Bearer YOUR_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"Хочу уютное кафе\",\"city\":\"Москва\",\"category\":\"Кафе\",\"min_rating\":4.0,\"limit_places\":5}"
```

Ответ:
- `reply` — ответ модели
- `places` — список кандидатов, который использовался для grounding

---

## Тесты

Установить dev‑зависимости:

```bash
pip install -r requirements-dev.txt
```

Запуск:

```bash
pytest
```

Тесты используют временную SQLite БД и по умолчанию отключают Geoapify импорт и LLM

---

### Почему чат grounded
Без grounding модель может галлюцинировать места, которых нет в базе  
Здесь бэкенд всегда выбирает реальные места из БД и передаёт модели явный список допустимых кандидатов

### Rate limiting
Реализован маленький in‑process лимитер  
Он подходит для локальной разработки и single‑process запуска  

### Кеширование UI в dev
В `ENV=dev` приложение отдаёт `/ui` с `Cache-Control: no-store`  
Это предотвращает проблемы, когда браузер не подхватывает изменения `styles.css` или `app.js`

