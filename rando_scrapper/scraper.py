"""
Scraper for randoromandie.com — collects all hike posts and parses their details.
"""

import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://randoromandie.com"
# Match WordPress date-based post URLs: /2026/02/09/slug/
POST_URL_PATTERN = re.compile(r"^/\d{4}/\d{2}/\d{2}/[^/]+/?$")


@dataclass
class Hike:
    """Single hike with normalized filter fields."""

    url: str
    title: str
    canton: str | None = None
    type_parcours: str | None = None  # "Linéaire" | "En boucle"
    km_range: str | None = None  # "Moins de 5 km", "5-10 km", ...
    duree_range: str | None = None  # "Moins de 3h", "De 3h à 5h", "Plus de 5h"
    environnement: str | None = None  # Montagne, Campagne, ...
    difficulte: str | None = None  # "Difficulté T1", "T2", "T3"
    denivele_range: str | None = None  # "Moins de 500 m", ...
    # Raw for display
    distance_km: float | None = None
    temps_marche: str | None = None
    montee_m: int | None = None
    descente_m: int | None = None
    saison: str | None = None
    lieu_depart: str | None = None
    lieu_arrivee: str | None = None
    acces_tp: str | None = None
    retour_tp: str | None = None
    suisse_mobile_url: str | None = None
    # Multi-value: a hike can have several env or tags (e.g. Hivernal)
    environnements: list[str] = field(default_factory=list)
    raw_table: dict = field(default_factory=dict)


def _normalize_km(km: float) -> str | None:
    if km is None:
        return None
    if km < 5:
        return "Moins de 5 km"
    if km <= 10:
        return "5-10 km"
    if km <= 15:
        return "10-15 km"
    if km <= 20:
        return "15-20 km"
    return "Plus de 20 km"


def _parse_duree(s: str) -> float | None:
    """Parse '3h06' or '2h30' to hours as float."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip().lower().replace(",", ".")
    # 3h06, 2h30, 1h15
    m = re.match(r"(\d+)\s*h\s*(\d+)?", s)
    if m:
        h = int(m.group(1))
        mn = int(m.group(2) or 0)
        return h + mn / 60.0
    # try just number (hours)
    m = re.match(r"([\d.]+)\s*h?", s)
    if m:
        return float(m.group(1))
    return None


def _normalize_duree(hours: float | None) -> str | None:
    if hours is None:
        return None
    if hours < 3:
        return "Moins de 3h"
    if hours <= 5:
        return "De 3h à 5h"
    return "Plus de 5h"


def _normalize_denivele(m: int | None) -> str | None:
    if m is None:
        return None
    if m < 500:
        return "Moins de 500 m"
    if m <= 1000:
        return "De 500 à 1000 m"
    return "Plus de 1000 m"


def _normalize_difficulte(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip()
    if "T1" in s:
        return "Difficulté T1"
    if "T2" in s:
        return "Difficulté T2"
    if "T3" in s:
        return "Difficulté T3"
    return None


# Canonical filter options (order for UI)
CANTONS = [
    "Genève",
    "France voisine",
    "Vaud",
    "Fribourg",
    "Valais romand",
    "Haut-Valais",
    "Neuchâtel",
    "Jura",
    "Berne",
]
TYPE_PARCOURS = ["Linéaire", "En boucle"]
KM_RANGES = ["Moins de 5 km", "5-10 km", "10-15 km", "15-20 km", "Plus de 20 km"]
DUREE_RANGES = ["Moins de 3h", "De 3h à 5h", "Plus de 5h"]
ENVIRONNEMENTS = [
    "Montagne",
    "Campagne",
    "Bord de rivière",
    "Bord de lac",
    "Bisses",
    "Gorges",
    "Hivernal",
    "Ville",
]
DIFFICULTES = ["Difficulté T1", "Difficulté T2", "Difficulté T3"]
DENIVELE_RANGES = ["Moins de 500 m", "De 500 à 1000 m", "Plus de 1000 m"]
# Saisons: "Toute l'année" = toutes les 4. Certaines randonnées ont plusieurs saisons.
SEASONS = ["Toute l'année", "Printemps", "Été", "Automne", "Hiver"]


def _extract_table(soup: BeautifulSoup) -> dict[str, str]:
    """Extract key-value table from a hike post page."""
    result = {}
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) >= 2:
                key = cells[0].get_text(separator=" ", strip=True)
                value = cells[1].get_text(separator=" ", strip=True)
                if key and value:
                    result[key] = value
    return result


def _parse_number_km(s: str) -> float | None:
    m = re.search(r"([\d.,]+)\s*km", s, re.I)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def _parse_number_m(s: str) -> int | None:
    m = re.search(r"([\d\s]+)\s*m", s, re.I)
    if m:
        return int(m.group(1).replace("\xa0", "").replace(" ", "").strip())
    return None


def parse_hike_page(url: str, html: str) -> Hike:
    """Parse a single hike post HTML into a Hike."""
    soup = BeautifulSoup(html, "html.parser")
    table = _extract_table(soup)

    title = ""
    title_el = soup.find("h1") or soup.find("title")
    if title_el:
        title = title_el.get_text(strip=True)
        # Only remove the site suffix, not the first " – " (e.g. "La Cure – La Givrine, par le Noirmont")
        if title.endswith(" – Randonnées en Suisse romande"):
            title = title[: -len(" – Randonnées en Suisse romande")].strip()

    # Raw fields
    canton = table.get("Canton") or table.get("Canton / Région")
    env_raw = table.get("Environnement") or ""
    distance_km = _parse_number_km(table.get("Distance", ""))
    temps_marche = table.get("Temps de marche") or table.get("Durée")
    montee_m = _parse_number_m(table.get("Montée", ""))
    descente_m = _parse_number_m(table.get("Descente", ""))
    saison = table.get("Saison")
    difficulte_raw = table.get("Difficulté")
    lieu_depart = table.get("Lieu de départ")
    lieu_arrivee = table.get("Lieu d'arrivée") or table.get("Lieu d’arrivée")
    acces_tp = table.get("Accès transports publics")
    retour_tp = table.get("Retour transports publics")

    suisse_mobile_url = None
    for a in soup.find_all("a", href=True):
        if "schweizmobil.ch" in a["href"] or "suissemobile" in a["href"].lower():
            suisse_mobile_url = a["href"]
            break

    # Environnements: can be multiple (e.g. Montagne + Hivernal from Saison)
    environnements = []
    if env_raw:
        for e in [
            "Montagne",
            "Campagne",
            "Bord de rivière",
            "Bord de lac",
            "Bisses",
            "Gorges",
            "Ville",
        ]:
            if e.lower() in env_raw.lower():
                environnements.append(e)
    if saison and "hiver" in (saison or "").lower():
        if "Hivernal" not in environnements:
            environnements.append("Hivernal")
    if not environnements and env_raw:
        environnements = [env_raw.strip()]

    # Type parcours: boucle if same start/end
    type_parcours = None
    if lieu_depart and lieu_arrivee:
        type_parcours = (
            "En boucle" if lieu_depart.strip() == lieu_arrivee.strip() else "Linéaire"
        )

    # Normalized filter fields
    km_range = _normalize_km(distance_km)
    hours = _parse_duree(temps_marche) if temps_marche else None
    duree_range = _normalize_duree(hours)
    denivele_range = _normalize_denivele(montee_m)
    difficulte = _normalize_difficulte(difficulte_raw)

    # Use first env for single-environnement filter if needed
    environnement = environnements[0] if environnements else (env_raw or None)

    return Hike(
        url=url,
        title=title,
        canton=canton,
        type_parcours=type_parcours,
        km_range=km_range,
        duree_range=duree_range,
        environnement=environnement,
        environnements=environnements,
        difficulte=difficulte,
        denivele_range=denivele_range,
        distance_km=distance_km,
        temps_marche=temps_marche,
        montee_m=montee_m,
        descente_m=descente_m,
        saison=saison,
        lieu_depart=lieu_depart,
        lieu_arrivee=lieu_arrivee,
        acces_tp=acces_tp,
        retour_tp=retour_tp,
        suisse_mobile_url=suisse_mobile_url,
        raw_table=table,
    )


def get_post_links_from_page(html: str, base: str) -> list[str]:
    """Extract all hike post URLs from a listing page."""
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        path = urlparse(href).path
        if path.endswith("/"):
            path = path[:-1]
        if path.startswith("/"):
            full = urljoin(base, path)
        else:
            full = href
        if "randoromandie.com" in full and POST_URL_PATTERN.match(path):
            if full not in seen:
                seen.add(full)
                links.append(full)
    return links


def fetch_all_post_urls(session: requests.Session, max_pages: int = 200) -> list[str]:
    """Paginate through the main site and collect all post URLs."""
    all_urls = set()
    page = 1
    while page <= max_pages:
        url = f"{BASE_URL}/page/{page}/" if page > 1 else BASE_URL + "/"
        try:
            r = session.get(url, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            break
        links = get_post_links_from_page(r.text, BASE_URL)
        if not links:
            break
        for u in links:
            all_urls.add(u)
        print(f"Page {page}: found {len(links)} links (total unique: {len(all_urls)})")
        page += 1
        time.sleep(0.5)
    return sorted(all_urls)


def scrape_all(
    session: requests.Session | None = None, delay: float = 0.7
) -> list[Hike]:
    """Scrape the whole site and return list of Hike."""
    session = session or requests.Session()
    session.headers.update(
        {
            "User-Agent": "RandoScrapper/1.0 (hike browser project; contact for any concern)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr,en;q=0.9",
        }
    )
    urls = fetch_all_post_urls(session)
    hikes = []
    for i, url in enumerate(urls):
        try:
            r = session.get(url, timeout=15)
            r.raise_for_status()
            hike = parse_hike_page(url, r.text)
            hikes.append(hike)
            print(f"[{i+1}/{len(urls)}] {hike.title[:50]}...")
        except Exception as e:
            print(f"Error {url}: {e}")
        time.sleep(delay)
    return hikes


def hike_to_row(h: Hike) -> dict:
    """Convert Hike to DB row (flat dict)."""
    return {
        "url": h.url,
        "title": h.title,
        "canton": h.canton,
        "type_parcours": h.type_parcours,
        "km_range": h.km_range,
        "duree_range": h.duree_range,
        "environnement": h.environnement,
        "environnements": ",".join(h.environnements) if h.environnements else None,
        "difficulte": h.difficulte,
        "denivele_range": h.denivele_range,
        "distance_km": h.distance_km,
        "temps_marche": h.temps_marche,
        "montee_m": h.montee_m,
        "descente_m": h.descente_m,
        "saison": h.saison,
        "lieu_depart": h.lieu_depart,
        "lieu_arrivee": h.lieu_arrivee,
        "acces_tp": h.acces_tp,
        "retour_tp": h.retour_tp,
        "suisse_mobile_url": h.suisse_mobile_url,
        "raw_table": json.dumps(h.raw_table, ensure_ascii=False)
        if h.raw_table
        else None,
    }


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS hikes (
        url TEXT PRIMARY KEY,
        title TEXT,
        canton TEXT,
        type_parcours TEXT,
        km_range TEXT,
        duree_range TEXT,
        environnement TEXT,
        environnements TEXT,
        difficulte TEXT,
        denivele_range TEXT,
        distance_km REAL,
        temps_marche TEXT,
        montee_m INTEGER,
        descente_m INTEGER,
        saison TEXT,
        lieu_depart TEXT,
        lieu_arrivee TEXT,
        acces_tp TEXT,
        retour_tp TEXT,
        suisse_mobile_url TEXT,
        raw_table TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_canton ON hikes(canton);
    CREATE INDEX IF NOT EXISTS idx_km_range ON hikes(km_range);
    CREATE INDEX IF NOT EXISTS idx_duree_range ON hikes(duree_range);
    CREATE INDEX IF NOT EXISTS idx_difficulte ON hikes(difficulte);
    CREATE INDEX IF NOT EXISTS idx_denivele_range ON hikes(denivele_range);
    CREATE INDEX IF NOT EXISTS idx_type_parcours ON hikes(type_parcours);
    """)
    try:
        conn.execute("ALTER TABLE hikes ADD COLUMN raw_table TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists


def save_hikes_to_db(hikes: list[Hike], db_path: str | Path) -> None:
    """Write all hikes to SQLite."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    create_schema(conn)
    row_keys = list(hike_to_row(hikes[0]).keys()) if hikes else []
    if not row_keys:
        conn.close()
        return
    placeholders = ",".join("?" * len(row_keys))
    columns = ",".join(row_keys)
    conn.executemany(
        f"INSERT OR REPLACE INTO hikes ({columns}) VALUES ({placeholders})",
        [tuple(hike_to_row(h).values()) for h in hikes],
    )
    conn.commit()
    conn.close()
    print(f"Saved {len(hikes)} hikes to {path}")


def load_hikes_from_db(db_path: str | Path) -> list[dict]:
    """Load all hikes from SQLite as list of dicts. Parses raw_table JSON when present."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM hikes").fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        raw = d.get("raw_table")
        if isinstance(raw, str) and raw:
            try:
                d["raw_table"] = json.loads(raw)
            except json.JSONDecodeError:
                d["raw_table"] = {}
        elif not isinstance(d.get("raw_table"), dict):
            d["raw_table"] = {}
        out.append(d)
    return out
