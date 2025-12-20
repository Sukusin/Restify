# Restify (minimal)

Backend на **FastAPI** для поиска мест, отзывов и персональных рекомендаций.

Что есть:
- Регистрация/логин (JWT)
- Пользователи добавляют места и отзывы
- Рейтинг места = агрегат по отзывам (1–5)
- Поиск/фильтрация мест по **категории/городу/минимальному рейтингу**
- Рекомендации по предпочтительным категориям пользователя
- Локальная LLM через **Hugging Face Transformers** (чат + суммаризация отзывов)
- Кэширование ответов LLM (TTL, in-memory)
- Логирование (console + `logs/app.log`)
- Минимальная схема БД без «status/created_by/etc.»

## Схема БД (минимум)

Таблица `places` — **только эти поля**:

- `id`
- `name`
- `category`
- `city`
- `address`
- `description`
- `created_at`
- `avg_rating`
- `reviews_count`

Таблица `reviews` (без модерации):

- `id`
- `place_id`
- `user_id`
- `rating`
- `text`
- `created_at`

Таблицы пользователей: `users_auth`, `users_profile`.

## Быстрый старт

### 1) Установка зависимостей

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Переменные окружения

Скопируйте пример и заполните при необходимости:

```bash
cp .env.example .env
```

Минимально важно для продакшена:
- `APP_SECRET_KEY` — секрет для JWT

### 3) Запуск

```bash
uvicorn app.main:app --reload
```

Swagger/OpenAPI: `http://127.0.0.1:8000/docs`  
Минимальный веб-интерфейс: `http://127.0.0.1:8000/ui/`

## Основные эндпоинты

- `POST /auth/register` — регистрация
- `POST /auth/token` — логин (JWT)
- `GET /me` — текущий пользователь
- `PUT /me/profile` — обновить профиль (предпочтительные категории)
- `POST /places` — создать место
- `GET /places` — список + фильтры
- `GET /places/{place_id}` — карточка места
- `POST /places/{place_id}/reviews` — добавить отзыв
- `GET /places/{place_id}/reviews` — список отзывов
- `GET /places/{place_id}/reviews/summary` — суммаризация отзывов (LLM)
- `GET /recommendations` — рекомендации
- `POST /chat` — чат-ответ с учётом профиля + кандидатов мест

## Роли

В коде оставлена простая модель ролей: `user` / `admin`.
Сейчас роли не влияют на UGC (модерации нет), но `admin` пригодится для дальнейших админ-фич.

Выдать роль можно скриптом:

```bash
python scripts/set_role.py user@example.com admin
```
