"""
Filter hikes with multiple criteria (AND between dimensions).
"""

from __future__ import annotations

from rando_scrapper.scraper import (
    CANTONS,
    DENIVELE_RANGES,
    DIFFICULTES,
    DUREE_RANGES,
    ENVIRONNEMENTS,
    KM_RANGES,
    SEASONS,
    TYPE_PARCOURS,
)

# Canonical season names (capitalization as displayed)
_CANONICAL_SEASONS = {"Printemps", "Été", "Automne", "Hiver"}


def _parse_saison(saison_str: str | None) -> set[str]:
    """Parse saison string into set of canonical season names. 'Toute l'année' -> all 4."""
    if not saison_str or not saison_str.strip():
        return set()
    s = saison_str.strip().lower().replace("\u2019", "'")  # unicode apostrophe
    if "toute l'année" in s:
        return _CANONICAL_SEASONS.copy()
    result = set()
    for part in saison_str.split(","):
        part = part.strip().lower()
        if not part:
            continue
        if "printemps" in part:
            result.add("Printemps")
        elif "été" in part or "ete" in part:
            result.add("Été")
        elif "automne" in part:
            result.add("Automne")
        elif "hiver" in part:
            result.add("Hiver")
    return result


def filter_hikes(
    hikes: list[dict],
    *,
    cantons: list[str] | None = None,
    types_parcours: list[str] | None = None,
    km_ranges: list[str] | None = None,
    duree_ranges: list[str] | None = None,
    environnements: list[str] | None = None,
    difficultes: list[str] | None = None,
    denivele_ranges: list[str] | None = None,
    saisons: list[str] | None = None,
) -> list[dict]:
    """
    Return hikes that match ALL selected filter groups.
    Within each group, a hike matches if it matches ANY of the selected values.
    For environnements: hike must have at least one of the selected environnements
    (in its environnements list or single environnement field).
    """
    if not hikes:
        return []

    result = hikes
    if cantons:
        result = [h for h in result if (h.get("canton") or "").strip() in cantons]
    if types_parcours:
        result = [
            h
            for h in result
            if (h.get("type_parcours") or "").strip() in types_parcours
        ]
    if km_ranges:
        result = [h for h in result if (h.get("km_range") or "").strip() in km_ranges]
    if duree_ranges:
        result = [
            h for h in result if (h.get("duree_range") or "").strip() in duree_ranges
        ]
    if difficultes:
        result = [
            h for h in result if (h.get("difficulte") or "").strip() in difficultes
        ]
    if denivele_ranges:
        result = [
            h
            for h in result
            if (h.get("denivele_range") or "").strip() in denivele_ranges
        ]
    if saisons:
        selected_s = set(saisons)

        def matches_saison(h: dict) -> bool:
            raw = (h.get("saison") or "").strip().lower().replace("\u2019", "'")
            if "toute l'année" in raw and "Toute l'année" in selected_s:
                return True
            hike_seasons = _parse_saison(h.get("saison"))
            if "Toute l'année" in selected_s and _CANONICAL_SEASONS <= hike_seasons:
                return True
            return bool(hike_seasons & (selected_s - {"Toute l'année"}))

        result = [h for h in result if matches_saison(h)]
    if environnements:

        def has_all_envs(h: dict, selected: list[str]) -> bool:
            single = (h.get("environnement") or "").strip()
            multi = (h.get("environnements") or "").strip()
            hike_envs = {single} if single else set()
            if multi:
                hike_envs.update(e.strip() for e in multi.split(",") if e.strip())
            return set(selected) <= hike_envs  # hike must have all selected envs

        result = [h for h in result if has_all_envs(h, environnements)]

    return result


def filter_options() -> dict[str, list[str]]:
    """Return labels for each filter dimension (for UI)."""
    return {
        "Canton": CANTONS,
        "Type de parcours": TYPE_PARCOURS,
        "Kilomètres": KM_RANGES,
        "Durée": DUREE_RANGES,
        "Environnement": ENVIRONNEMENTS,
        "Difficulté": DIFFICULTES,
        "Dénivelé positif": DENIVELE_RANGES,
        "Saison": SEASONS,
    }
