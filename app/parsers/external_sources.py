from __future__ import annotations

"""Stub module for future automatic parsing from external sources.

Planned sources:
- Telegram channels
- Web portals

This project intentionally keeps it empty for now.
"""

from dataclasses import dataclass


@dataclass
class ParsedPlace:
    name: str
    category: str
    city: str
    description: str | None = None
    address: str | None = None
    source: str | None = None


def parse_telegram_channels() -> list[ParsedPlace]:
    """TODO: implement Telegram parsing."""
    return []


def parse_web_portals() -> list[ParsedPlace]:
    """TODO: implement web portal parsing."""
    return []
