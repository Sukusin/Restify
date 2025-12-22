# Restify (minimal)

Монолитный backend на **Python** (FastAPI) для подбора мест отдыха/развлечений.

## Что есть

- Регистрация/логин (JWT)
- Места в БД + поиск/фильтры: **название / категория / город / минимальный рейтинг**
- Пользователи оставляют отзывы (1–5)
- У места хранятся агрегаты: `avg_rating`, `reviews_count`
- Рекомендации по предпочтительным категориям пользователя
- Чат и суммаризация отзывов через локальную LLM (Hugging Face) — опционально

## Что изменено по твоему требованию

- **Пользователи не добавляют места** (эндпоинта `POST /places` нет)
- Места **импортируются скриптом из Geoapify автоматически при запуске приложения**
- **Минимальная схема `places`** (только:
  `id, name, category, city, address, description, created_at, avg_rating, reviews_count`)
- Без `status`, `created_by`, и прочих служебных столбцов

## Быстрый старт

### 1) Установка зависимостей

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Переменные окружения

Создай `.env` (или экспортируй переменные) по примеру `.env.example`.

Главные:
- `APP_SECRET_KEY` — секрет для JWT
- `DATABASE_URL` — строка подключения (по умолчанию `sqlite:///./app.db`)
- `GEOAPIFY_KEY` — ключ Geoapify (если пустой, используется fallback-ключ в коде импортера)

### 3) Запуск

```bash
uvicorn app.main:app --reload
```

Swagger/OpenAPI: `http://127.0.0.1:8000/docs`

Минимальный UI: `http://127.0.0.1:8000/ui/`

> На первом запуске приложение создаст таблицы и, если таблица `places` пуста, автоматически импортирует места из Geoapify.

## Основные эндпоинты

- `POST /auth/register` — регистрация
- `POST /auth/token` — логин (JWT)
- `GET /me` — текущий пользователь
- `PUT /me/profile` — профиль (предпочтительные категории)
- `GET /places` — поиск/фильтры
- `GET /places/{place_id}` — карточка места
- `POST /places/{place_id}/reviews` — добавить отзыв
- `GET /places/{place_id}/reviews/summary` — суммаризация отзывов (LLM)
- `GET /recommendations` — рекомендации
- `POST /chat` — чат
