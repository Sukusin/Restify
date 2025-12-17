from __future__ import annotations


from dataclasses import dataclass


@dataclass
class ParsedPlace:
    name: str
    category: str
    city: str
    description: str | None = None
    address: str | None = None
    source: str | None = None

