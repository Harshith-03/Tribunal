"""Builds the authoritative reference links the deliverable cites.

References are derived from the client's GROUND-TRUTH constraints plus the
recommended vendor's attested certifications, so the client can independently
verify every compliance claim (e.g. the HIPAA link for Meridian).
"""
from __future__ import annotations

from .data_loader import _load


def _refs() -> dict:
    return _load("references.json")


def references_for(constraints: list[dict], vendor_meta: dict | None) -> list[dict]:
    refs = _refs()
    out: list[dict] = []
    seen: set[str] = set()

    def add(category: str, item: dict):
        key = item.get("title", "")
        if key in seen:
            return
        seen.add(key)
        out.append({"category": category, **item})

    for c in constraints:
        ctype, value = c.get("type"), c.get("value")
        if ctype == "compliance" and value in refs.get("compliance", {}):
            add("Compliance", refs["compliance"][value])
        elif ctype == "data_residency" and value in refs.get("data_residency", {}):
            add("Data residency", refs["data_residency"][value])

    # Vendor attestation (text-only, no external link)
    if vendor_meta:
        certs = ", ".join(vendor_meta.get("compliance_certs", [])) or "none listed"
        add("Vendor attestation", {
            "title": f"{vendor_meta['name']} — attested certifications",
            "url": None,
            "note": (
                f"Deploys {vendor_meta['deployment']}; holds {certs}; "
                f"data residency {', '.join(vendor_meta.get('data_residency', []))}."
            ),
        })

    # Governance frameworks always apply.
    for f in refs.get("frameworks", []):
        add("Governance", f)

    return out
