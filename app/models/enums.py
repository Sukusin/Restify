from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    user = "user"
    # Kept for backwards compatibility with existing DB/users.
    moderator = "moderator"
    admin = "admin"
