# Rando Romandie — Multi-Filter Browser

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Same hike data as [randoromandie.com](https://randoromandie.com/), with **multiple filters at once** (Canton + distance + duration + difficulty + environment + elevation, season, etc.).

## Why this project?

On [randoromandie.com](https://randoromandie.com/) you can only apply **one filter at a time** (e.g. either Canton, or distance, or duration). To find e.g. “a 5–10 km hike in Vaud, under 3h, T1” you’d have to try each filter separately and compare by hand. This project scrapes the same data into a local DB and provides a small app where you can combine **several filters** and see only the hikes that match all your criteria.

- **Scraper**: fetches all hike posts from the site and parses details into a SQLite DB.
- **Streamlit app**: browse and filter hikes with several criteria combined.

## ⚙️ Installation & Setup

To install, run the following command in an environment with [Poetry](https://python-poetry.org/docs/) installed:

```bash
poetry install --with dev --all-extras --no-cache
```

> ⚠️ Ensure your Poetry version is at least 1.8.0.

To update dependencies:

```bash
poetry update
```

## 📂 Project Structure

```text
📂 RandoScrapper/
├── 📂 rando_scrapper/           # Main Python package
│   ├── 🐍 __init__.py
│   ├── 🐍 scraper.py            # Fetch posts, parse hike pages, SQLite save/load
│   └── 🐍 filtering.py          # Multi-criteria filter logic
├── 📂 scripts/
│   └── 🐍 run_scraper.py       # CLI to run the scraper
├── 📂 data/
│   ├── .gitkeep
│   └── hikes.db                 # SQLite DB (tracked for deployment)
├── 🐍 app.py                    # Streamlit UI and multi-select filters
├── 📄 pyproject.toml
├── 📄 CHANGELOG.md
└── 📄 LICENSE
```

## 1. Scrape the site (first time)

**Full scrape** (all hikes):

```bash
poetry run python scripts/run_scraper.py
```

**Sample only** (e.g. 2 pages, 15 hikes — useful for testing):

```bash
poetry run python scripts/run_scraper.py --max-pages 2 --max-hikes 15
```

Adjust `--max-pages` and `--max-hikes` as you like; omit both for a full scrape.

The scraper will:

- Paginate through the main blog feed and collect every hike URL.
- Fetch each hike page and parse the info table (canton, distance, duration, difficulty, etc.).
- Normalize values into the same filter categories as the original site.
- Save everything to `data/hikes.db`.

Run it again anytime to refresh the database.

## 2. Run the app

```bash
poetry run streamlit run app.py
```

Open the URL shown in the terminal (usually http://localhost:8501). Use the sidebar to select one or more values per filter; only hikes matching **all** selected criteria are shown.

## Filter logic

- **Between dimensions**: AND (e.g. Canton = Vaud **and** Distance = 5–10 km).
- **Within a dimension**: if you select several values (e.g. “Montagne” and “Hivernal”), a hike must match **all** of them (e.g. both Montagne and Hivernal).
- No selection for a dimension = no filter on that dimension.

Data and filter categories (Canton, Type de parcours, Kilomètres, Durée, Environnement, Difficulté, Dénivelé, Saison) mirror the original site.

## 🛠️ Linting & Formatting

Run these in your local clone to lint and format with [Ruff](https://docs.astral.sh/ruff/):

```bash
# Format with ruff
poetry run ruff format .

# Lint & auto-fix
poetry run ruff check . --fix

# Both at once
poetry run ruff format .; poetry run ruff check . --fix
```

## Pre-commit Hooks

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run all pre-commit checks on every file
pre-commit run --all-files
```

Hooks run [pre-commit-hooks](https://github.com/pre-commit/pre-commit-hooks) (check TOML/YAML) and [ruff-pre-commit](https://github.com/astral-sh/ruff-pre-commit) (lint + format with `--fix`).

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
