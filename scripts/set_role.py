from __future__ import annotations

import sys

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.users import UserAuth
from app.models.enums import UserRole


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/set_role.py <email> <role: user|moderator|admin>")
        return 2

    email, role = sys.argv[1], sys.argv[2]
    if role not in {r.value for r in UserRole}:
        print(f"Unknown role: {role}")
        return 2

    db = SessionLocal()
    try:
        user = db.scalar(select(UserAuth).where(UserAuth.email == email))
        if not user:
            print("User not found")
            return 1
        user.role = role
        db.add(user)
        db.commit()
        print(f"Role updated: {email} -> {role}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
