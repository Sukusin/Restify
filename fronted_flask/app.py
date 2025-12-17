from __future__ import annotations
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from dotenv import load_dotenv

from config import Config
from api import RestifyAPI, APIError

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

def get_token() -> str | None:
    return session.get("access_token")

api = RestifyAPI(app.config["API_BASE_URL"], token_getter=get_token)

@app.before_request
def load_current_user():
    g.me = None
    if session.get("access_token"):
        # кэшируем /me в сессии, чтобы не дёргать каждый раз
        if session.get("me_cache"):
            g.me = session["me_cache"]
            return
        try:
            me = api.me()
            session["me_cache"] = me
            g.me = me
        except APIError:
            session.pop("access_token", None)
            session.pop("me_cache", None)
            g.me = None

def require_login():
    if not session.get("access_token"):
        flash("Нужно войти.", "warning")
        return redirect(url_for("login"))
    return None

@app.get("/")
def index():
    # фильтры из README: категория/город/рейтинг :contentReference[oaicite:4]{index=4}
    q = request.args.get("q", "")
    city = request.args.get("city", "")
    category = request.args.get("category", "")
    min_rating = request.args.get("min_rating", "")

    try:
        places = api.places(q=q, city=city, category=category, min_rating=min_rating)
    except APIError as e:
        places = []
        flash(f"Ошибка загрузки мест: {e.message}", "danger")

    return render_template("index.html", places=places, q=q, city=city, category=category, min_rating=min_rating)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        try:
            api.register(email=email, password=password, full_name=full_name or None)
            flash("Аккаунт создан. Теперь войдите.", "success")
            return redirect(url_for("login"))
        except APIError as e:
            flash(f"Регистрация не удалась: {e.message}", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            token = api.token(username_or_email=user, password=password)
            if not token:
                flash("Не удалось получить JWT токен.", "danger")
                return render_template("login.html")
            session["access_token"] = token
            session.pop("me_cache", None)
            flash("Вы вошли.", "success")
            return redirect(url_for("index"))
        except APIError as e:
            flash(f"Логин не удался: {e.message}", "danger")
    return render_template("login.html")

@app.get("/logout")
def logout():
    session.pop("access_token", None)
    session.pop("me_cache", None)
    flash("Вы вышли.", "info")
    return redirect(url_for("index"))

@app.route("/profile", methods=["GET", "POST"])
def profile():
    r = require_login()
    if r: return r

    me = g.me or {}
    if request.method == "POST":
        raw = request.form.get("preferred_categories", "")
        cats = [c.strip() for c in raw.split(",") if c.strip()]
        try:
            api.update_profile(preferred_categories=cats)
            session.pop("me_cache", None)
            flash("Профиль обновлён.", "success")
            return redirect(url_for("profile"))
        except APIError as e:
            flash(f"Не удалось обновить профиль: {e.message}", "danger")

    preferred = ""
    if isinstance(me, dict):
        pc = me.get("preferred_categories") or me.get("profile", {}).get("preferred_categories")
        if isinstance(pc, list):
            preferred = ", ".join(pc)

    return render_template("profile.html", me=me, preferred=preferred)

@app.route("/places/new", methods=["GET", "POST"])
def place_new():
    r = require_login()
    if r: return r

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        city = request.form.get("city", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        try:
            created = api.create_place(name=name, city=city, category=category, description=description)
            flash("Место отправлено (возможно, на модерацию).", "success")
            # если backend вернул id — прыгнем в карточку
            if isinstance(created, dict) and created.get("id") is not None:
                return redirect(url_for("place_detail", place_id=created["id"]))
            return redirect(url_for("index"))
        except APIError as e:
            flash(f"Не удалось создать место: {e.message}", "danger")

    return render_template("place_new.html")

@app.route("/places/<place_id>", methods=["GET", "POST"])
def place_detail(place_id: str):
    # POST здесь — добавление отзыва
    if request.method == "POST":
        r = require_login()
        if r: return r
        rating = int(request.form.get("rating", "5"))
        text = request.form.get("text", "").strip()
        try:
            api.add_review(place_id=place_id, rating=rating, text=text)
            flash("Отзыв отправлен (возможно, на модерацию).", "success")
        except APIError as e:
            flash(f"Не удалось добавить отзыв: {e.message}", "danger")
        return redirect(url_for("place_detail", place_id=place_id))

    # GET — карточка
    place = None
    reviews = []
    detail_error = None

    try:
        place = api.place_detail(place_id)
    except APIError as e:
        detail_error = f"Нет /places/{{id}} в backend или ошибка: {e.message}"

    try:
        reviews = api.list_reviews(place_id)
    except APIError:
        reviews = []

    return render_template("place_detail.html", place=place, place_id=place_id, reviews=reviews, detail_error=detail_error)

@app.get("/places/<place_id>/summary")
def place_summary(place_id: str):
    r = require_login()
    if r: return r
    try:
        s = api.reviews_summary(place_id)
        # ожидаем {summary: "..."} но не требуем
        summary = s.get("summary") if isinstance(s, dict) else str(s)
        flash(summary, "info")
    except APIError as e:
        flash(f"Не удалось получить summary: {e.message}", "danger")
    return redirect(url_for("place_detail", place_id=place_id))

@app.get("/recommendations")
def recommendations():
    r = require_login()
    if r: return r
    try:
        recs = api.recommendations()
    except APIError as e:
        recs = []
        flash(f"Не удалось получить рекомендации: {e.message}", "danger")
    return render_template("recommendations.html", recs=recs)

@app.route("/chat", methods=["GET", "POST"])
def chat():
    r = require_login()
    if r: return r

    answer = None
    raw = None
    if request.method == "POST":
        msg = request.form.get("message", "").strip()
        try:
            raw = api.chat(msg)
            if isinstance(raw, dict):
                answer = raw.get("answer") or raw.get("message") or raw.get("response")
            if answer is None:
                answer = str(raw)
        except APIError as e:
            flash(f"Чат недоступен: {e.message}", "danger")

    return render_template("chat.html", answer=answer, raw=raw)

@app.get("/moderation/places")
def moderation_places():
    r = require_login()
    if r: return r
    try:
        items = api.pending_places()
    except APIError as e:
        items = []
        flash(f"Не удалось загрузить pending places: {e.message}", "danger")
    return render_template("moderation_places.html", items=items)

@app.post("/moderation/places/<place_id>/<action>")
def moderation_places_action(place_id: str, action: str):
    r = require_login()
    if r: return r
    try:
        if action == "approve":
            api.approve_place(place_id)
        elif action == "reject":
            api.reject_place(place_id)
        else:
            flash("Неизвестное действие.", "warning")
            return redirect(url_for("moderation_places"))
        flash("Готово.", "success")
    except APIError as e:
        flash(f"Ошибка модерации: {e.message}", "danger")
    return redirect(url_for("moderation_places"))

@app.get("/moderation/reviews")
def moderation_reviews():
    r = require_login()
    if r: return r
    try:
        items = api.pending_reviews()
    except APIError as e:
        items = []
        flash(f"Не удалось загрузить pending reviews: {e.message}", "danger")
    return render_template("moderation_reviews.html", items=items)

@app.post("/moderation/reviews/<review_id>/<action>")
def moderation_reviews_action(review_id: str, action: str):
    r = require_login()
    if r: return r
    try:
        if action == "approve":
            api.approve_review(review_id)
        elif action == "reject":
            api.reject_review(review_id)
        else:
            flash("Неизвестное действие.", "warning")
            return redirect(url_for("moderation_reviews"))
        flash("Готово.", "success")
    except APIError as e:
        flash(f"Ошибка модерации: {e.message}", "danger")
    return redirect(url_for("moderation_reviews"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
