"""Gemeinsame Hilfsfunktionen."""
from __future__ import annotations


def slugify_name(name: str) -> str:
    """Konvertiert einen Namen in einen Entity-ID-tauglichen Slug."""
    return (
        name.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
