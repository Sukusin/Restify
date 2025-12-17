from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Dict
import requests


@dataclass
class APIError(Exception):
    status_code: int
    message: str
    details: Any = None


class RestifyAPI:
    def __init__(self, base_url: str, token_getter):
        self.base_url = base_url.rstrip("/")
        self.token_getter = token_getter

    def _headers(self, auth: bool) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if auth:
            token = self.token_getter()
            if token:
                h["Authorization"] = f"Bearer {token}"
        return h

    def request(self, method: str, path: str, *, auth: bool = True,
                params: Optional[dict] = None,
                json: Optional[dict] = None,
                data: Optional[dict] = None) -> Any:
        url = f"{self.base_url}{path}"
        resp = requests.request(
            method=method.upper(),
            url=url,
            headers=self._headers(auth),
            params=params,
            json=json,
            data=data,
            timeout=20,
        )

        # Пытаемся читать JSON, но не требуем его
        try:
            payload = resp.json()
        except Exception:
            payload = resp.text

        if resp.status_code >= 400:
            msg = None
            if isinstance(payload, dict):
                msg = payload.get("detail") or payload.get("message")
            raise APIError(resp.status_code, msg or f"HTTP {resp.status_code}", payload)

        return payload

    # --- Auth ---
    def register(self, email: str, password: str, full_name: str | None = None) -> Any:
        body = {"email": email, "password": password}
        if full_name:
            body["full_name"] = full_name
        return self.request("POST", "/auth/register", auth=False, json=body)

    def token(self, username_or_email: str, password: str) -> str:
        # Часто FastAPI OAuth2PasswordRequestForm ждёт form-data: username/password
        payload = self.request(
            "POST",
            "/auth/token",
            auth=False,
            data={"username": username_or_email, "password": password},
        )
        if isinstance(payload, dict):
            return payload.get("access_token") or payload.get("token") or ""
        return ""

    # --- Profile ---
    def me(self) -> Any:
        return self.request("GET", "/me", auth=True)

    def update_profile(self, preferred_categories: list[str]) -> Any:
        return self.request("PUT", "/me/profile", auth=True, json={"preferred_categories": preferred_categories})

    # --- Places / Reviews ---
    def places(self, **filters) -> Any:
        return self.request("GET", "/places", auth=False, params={k: v for k, v in filters.items() if v not in (None, "", [])})

    def create_place(self, name: str, city: str, category: str, description: str = "") -> Any:
        return self.request("POST", "/places", auth=True, json={
            "name": name, "city": city, "category": category, "description": description
        })

    def place_detail(self, place_id: str | int) -> Any:
        # В README не указан, но часто есть. Если нет — UI покажет ошибку.
        return self.request("GET", f"/places/{place_id}", auth=False)

    def list_reviews(self, place_id: str | int) -> Any:
        # Тоже не в README, но обычно есть.
        return self.request("GET", f"/places/{place_id}/reviews", auth=False)

    def add_review(self, place_id: str | int, rating: int, text: str) -> Any:
        return self.request("POST", f"/places/{place_id}/reviews", auth=True, json={"rating": rating, "text": text})

    def reviews_summary(self, place_id: str | int) -> Any:
        return self.request("GET", f"/places/{place_id}/reviews/summary", auth=True)

    # --- Recommendations / Chat ---
    def recommendations(self) -> Any:
        return self.request("GET", "/recommendations", auth=True)

    def chat(self, message: str) -> Any:
        return self.request("POST", "/chat", auth=True, json={"message": message})

    # --- Moderation ---
    def pending_places(self) -> Any:
        return self.request("GET", "/moderation/places/pending", auth=True)

    def approve_place(self, place_id: str | int) -> Any:
        return self.request("POST", f"/moderation/places/{place_id}/approve", auth=True)

    def reject_place(self, place_id: str | int) -> Any:
        return self.request("POST", f"/moderation/places/{place_id}/reject", auth=True)

    def pending_reviews(self) -> Any:
        return self.request("GET", "/moderation/reviews/pending", auth=True)

    def approve_review(self, review_id: str | int) -> Any:
        return self.request("POST", f"/moderation/reviews/{review_id}/approve", auth=True)

    def reject_review(self, review_id: str | int) -> Any:
        return self.request("POST", f"/moderation/reviews/{review_id}/reject", auth=True)
