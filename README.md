# Leisure Recommender (minimal)

Монолитный backend на **Python 3.13** для диалоговых рекомендаций мест отдыха/развлечений.

Что есть (минимальный функционал из условия):
- UGC: пользователи добавляют места и отзывы
- Рейтинги (1–5), агрегированный рейтинг места
- Ролевая модель доступа: `user` / `moderator` / `admin`
- Модерация UGC (места и отзывы): `pending/approved/rejected`
- Быстрый поиск/фильтрация мест по **категории/городу/рейтингу**
- Рекомендации по предпочтительным категориям пользователя
- Интеграция с **локальной бесплатной LLM** через **Ollama** (чат + суммаризация отзывов)
- Кэширование ответов LLM (TTL, in-memory)
- Логирование (console + `logs/app.log`)
- Заготовка модуля парсинга внешних источников (пока пустой)

## Быстрый старт

### 1) Установка зависимостей

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Запуск

```bash
uvicorn app.main:app --reload
```

Swagger/OpenAPI: `http://127.0.0.1:8000/docs`

### 3) Локальная LLM (Ollama)

1. Установите Ollama.
2. Запустите сервер (обычно он стартует автоматически; иначе):

```bash
ollama serve
```

3. Скачайте маленькую модель (пример):

```bash
ollama pull llama3.2:1b
```

По умолчанию приложение обращается к `http://localhost:11434`.

### Переменные окружения

- `DATABASE_URL` (по умолчанию: `sqlite:///./app.db`)
- `APP_SECRET_KEY` (обязательно в проде)
- `LLM_PROVIDER` = `ollama` или `disabled` (по умолчанию: `ollama`)
- `OLLAMA_BASE_URL` (по умолчанию: `http://localhost:11434`)
- `OLLAMA_MODEL` (по умолчанию: `llama3.2:1b`)

Пример:

```bash
export APP_SECRET_KEY='change-me'
export LLM_PROVIDER='ollama'
export OLLAMA_MODEL='llama3.2:1b'
uvicorn app.main:app --reload
```

## Основные эндпоинты

- `POST /auth/register` — регистрация
- `POST /auth/token` — логин (JWT)
- `GET /me` — текущий пользователь
- `PUT /me/profile` — обновить профиль (предпочтительные категории)
- `POST /places` — создать место (для обычных пользователей уходит в `pending`)
- `GET /places` — поиск/фильтры
- `POST /places/{place_id}/reviews` — добавить отзыв (по умолчанию `pending`)
- `GET /places/{place_id}/reviews/summary` — суммаризация отзывов (LLM)
- `GET /recommendations` — рекомендации
- `POST /chat` — диалоговый ответ с учётом профиля + кандидатов мест

### Модерация (роль `moderator`/`admin`)
- `GET /moderation/places/pending`
- `POST /moderation/places/{place_id}/approve|reject`
- `GET /moderation/reviews/pending`
- `POST /moderation/reviews/{review_id}/approve|reject`

## Примечания

- Таблицы БД: `users_auth`, `users_profile`, `places`, `reviews`.
- Для простоты используется SQLite; можно заменить на Postgres через `DATABASE_URL`.

### Как быстро получить модератора

После регистрации можно выдать роль через скрипт:

```bash
python scripts/set_role.py user@example.com moderator
```
