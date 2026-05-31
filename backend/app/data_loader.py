"""Loads the synthetic /data catalog and exposes lookup helpers."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from . import config


@lru_cache(maxsize=1)
def _load(name: str) -> Any:
    with open(config.DATA_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def clients() -> list[dict]:
    return _load("clients.json")["clients"]


# user-uploaded briefs become custom clients, registered at runtime
CUSTOM_CLIENTS: dict[str, dict] = {}


def register_custom_client(profile: dict) -> None:
    CUSTOM_CLIENTS[profile["id"]] = profile


def client_by_id(client_id: str) -> dict | None:
    if client_id in CUSTOM_CLIENTS:
        return CUSTOM_CLIENTS[client_id]
    return next((c for c in clients() if c["id"] == client_id), None)


def vendors() -> list[dict]:
    return _load("vendors.json")["vendors"]


def vendor_by_id(vendor_id: str) -> dict | None:
    return next((v for v in vendors() if v["id"] == vendor_id), None)


def required_roles() -> dict:
    return _load("required_roles.json")


def risk_bank() -> dict:
    return _load("risk_bank.json")


def risks_for_client(client_id: str) -> list[str]:
    bank = risk_bank()
    return bank.get("by_client", {}).get(client_id, []) + bank.get("generic", [])
