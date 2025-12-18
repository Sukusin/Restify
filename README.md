# Leisure Recommender (minimal)

Монолитный backend на **Python 3.13** для диалоговых рекомендаций мест отдыха/развлечений.

Что есть (минимальный функционал из условия):
- UGC: пользователи добавляют места и отзывы
- Рейтинги (1–5), агрегированный рейтинг места
- Ролевая модель доступа: `user` / `moderator` / `admin`
- Модерация UGC (места и отзывы): `pending/approved/rejected`
- Быстрый поиск/фильтрация мест по **категории/городу/рейтингу**
- Рекомендации по предпочтительным категориям пользователя
- Интеграция с **локальной бесплатной LLM** через **Hugging Face Transformers** (чат + суммаризация отзывов)
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

Минимальный веб-интерфейс (HTML/JS): `http://127.0.0.1:8000/ui/`

### 3) Локальная LLM (Hugging Face)

По умолчанию используется небольшая бесплатная модель `Qwen/Qwen2.5-0.5B-Instruct`.
Она будет скачана автоматически при первом обращении к `/chat` или `/places/{id}/reviews/summary`.

Если хотите другую модель — поменяйте `HF_MODEL_ID` в `.env`.

### Переменные окружения

- `DATABASE_URL` (по умолчанию: `sqlite:///./app.db`)
- `APP_SECRET_KEY` (обязательно в проде)
- `LLM_PROVIDER` = `hf_local` или `disabled` (по умолчанию: `hf_local`)
- `HF_MODEL_ID` (по умолчанию: `Qwen/Qwen2.5-0.5B-Instruct`)
- `HF_DEVICE` = `auto` | `cpu` | `cuda` (по умолчанию: `auto`)
- `HF_MAX_NEW_TOKENS` (по умолчанию: `256`)
- `HF_TEMPERATURE` (по умолчанию: `0.7`)
- `HF_TOP_P` (по умолчанию: `0.9`)

Пример:

```bash
export APP_SECRET_KEY='change-me'
export LLM_PROVIDER='hf_local'
export HF_MODEL_ID='Qwen/Qwen2.5-0.5B-Instruct'
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

### UI (статические файлы)

Фронтенд лежит в `app/static/` и отдаётся FastAPI по пути `/ui/`.
Также включён CORS (`allow_origins=['*']`) для удобного локального запуска (например, через Live Server).

### Как быстро получить модератора

После регистрации можно выдать роль через скрипт:

```bash
python scripts/set_role.py user@example.com moderator
```
