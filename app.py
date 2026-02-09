"""
Streamlit app: browse Rando Romandie hikes with multiple filters.
Run: poetry run streamlit run app.py
"""

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from rando_scrapper.filtering import filter_hikes, filter_options
from rando_scrapper.scraper import load_hikes_from_db

# Order of keys as on the site (for consistent display)
INFO_TABLE_KEYS = [
    "Canton",
    "Environnement",
    "Temps de marche",
    "Distance",
    "Montée",
    "Descente",
    "Saison",
    "Difficulté",
    "Lieu de départ",
    "Accès transports publics",
    "Lieu d'arrivée",
    "Retour transports publics",
]


def _hike_info_table(hike: dict) -> list[tuple[str, str]]:
    """Build (key, value) rows for the info table. Prefer raw_table from site, else from fields."""
    raw = hike.get("raw_table")
    if isinstance(raw, dict) and raw:
        ordered = [(k, raw[k]) for k in INFO_TABLE_KEYS if k in raw]
        for k, v in raw.items():
            if k not in INFO_TABLE_KEYS:
                ordered.append((k, v))
        return ordered
    rows = []
    if hike.get("canton"):
        rows.append(("Canton", hike["canton"]))
    if hike.get("environnement"):
        rows.append(("Environnement", hike["environnement"]))
    if hike.get("temps_marche"):
        rows.append(("Temps de marche", hike["temps_marche"]))
    if hike.get("distance_km") is not None:
        rows.append(("Distance", f"{hike['distance_km']} km"))
    if hike.get("montee_m") is not None:
        rows.append(("Montée", f"{hike['montee_m']} m"))
    if hike.get("descente_m") is not None:
        rows.append(("Descente", f"{hike['descente_m']} m"))
    if hike.get("saison"):
        rows.append(("Saison", hike["saison"]))
    if hike.get("difficulte"):
        rows.append(("Difficulté", hike["difficulte"]))
    if hike.get("lieu_depart"):
        rows.append(("Lieu de départ", hike["lieu_depart"]))
    if hike.get("acces_tp"):
        rows.append(("Accès transports publics", hike["acces_tp"]))
    if hike.get("lieu_arrivee"):
        rows.append(("Lieu d'arrivée", hike["lieu_arrivee"]))
    if hike.get("retour_tp"):
        rows.append(("Retour transports publics", hike["retour_tp"]))
    return rows


# Default DB path
DEFAULT_DB = Path(__file__).resolve().parent / "data" / "hikes.db"

st.set_page_config(
    page_title="Randonnées Romandie",
    page_icon="🥾",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Load data
@st.cache_data
def load_data(db_path: Path):
    if not db_path.exists():
        return None
    return load_hikes_from_db(db_path)


db_path = DEFAULT_DB
data = load_data(db_path)

if data is None:
    st.error(
        f"Aucune base de données trouvée dans `{db_path}`. "
        "Exécutez d’abord le scraper : `poetry run python scripts/run_scraper.py`"
    )
    st.stop()

# Sidebar: multi-select filters (expanded by default so mobile users see it)
st.sidebar.title("🥾 Filtres")

options = filter_options()

# Map UI key -> (db field, selected list)
selected = {}
selected["Canton"] = st.sidebar.multiselect(
    "Canton",
    options=options["Canton"],
    default=[],
    key="canton",
)
selected["Type de parcours"] = st.sidebar.multiselect(
    "Type de parcours",
    options=options["Type de parcours"],
    default=[],
    key="type_parcours",
)
selected["Kilomètres"] = st.sidebar.multiselect(
    "Kilomètres",
    options=options["Kilomètres"],
    default=[],
    key="km",
)
selected["Durée"] = st.sidebar.multiselect(
    "Durée",
    options=options["Durée"],
    default=[],
    key="duree",
)
selected["Environnement"] = st.sidebar.multiselect(
    "Environnement",
    options=options["Environnement"],
    default=[],
    key="env",
)
selected["Difficulté"] = st.sidebar.multiselect(
    "Difficulté",
    options=options["Difficulté"],
    default=[],
    key="difficulte",
)
selected["Dénivelé positif"] = st.sidebar.multiselect(
    "Dénivelé positif",
    options=options["Dénivelé positif"],
    default=[],
    key="denivele",
)
selected["Saison"] = st.sidebar.multiselect(
    "Saison",
    options=options["Saison"],
    default=[],
    key="saison",
)

# Apply filters
filtered = filter_hikes(
    data,
    cantons=selected["Canton"] or None,
    types_parcours=selected["Type de parcours"] or None,
    km_ranges=selected["Kilomètres"] or None,
    duree_ranges=selected["Durée"] or None,
    environnements=selected["Environnement"] or None,
    difficultes=selected["Difficulté"] or None,
    denivele_ranges=selected["Dénivelé positif"] or None,
    saisons=selected["Saison"] or None,
)

# Main area
st.title("Randonnées en Suisse romande")
st.caption("Source : [randoromandie.com](https://randoromandie.com/)")

st.sidebar.metric("Randonnées affichées", len(filtered))
st.sidebar.metric("Total en base", len(data))

if not filtered:
    st.info(
        "Aucune randonnée ne correspond aux filtres. Essayez d’en désactiver quelques-uns."
    )
    st.stop()

# Table + expandable details
df = pd.DataFrame(filtered)
columns_display = [
    "title",
    "canton",
    "km_range",
    "duree_range",
    "difficulte",
    "environnement",
    "type_parcours",
]
cols_available = [c for c in columns_display if c in df.columns]
df_display = df[cols_available].copy()
df_display = df_display.rename(
    columns={
        "title": "Randonnée",
        "canton": "Canton",
        "km_range": "Distance",
        "duree_range": "Durée",
        "difficulte": "Difficulté",
        "environnement": "Environnement",
        "type_parcours": "Type",
    }
)

for i, _row in df_display.iterrows():
    hike = filtered[i]
    title = hike.get("title") or "Sans titre"
    url = hike.get("url") or ""
    montee = hike.get("montee_m")
    d_plus = f" · D+ {montee} m" if montee is not None else ""
    dist = hike.get("distance_km")
    dist_str = f"{dist} km" if dist is not None else (hike.get("km_range") or "-")
    with st.expander(
        f"**{title}** — {hike.get('canton') or '-'} · {dist_str} · {hike.get('difficulte') or '-'}{d_plus}"
    ):
        st.markdown(f"[📄 Voir sur randoromandie.com]({url})")
        if hike.get("suisse_mobile_url"):
            st.markdown(f"[🗺 Carte SuisseMobile]({hike['suisse_mobile_url']})")
        table_rows = _hike_info_table(hike)
        if table_rows:
            rows_html = "".join(
                f"<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>"
                for k, v in table_rows
            )
            st.markdown(f"<table>{rows_html}</table>", unsafe_allow_html=True)
