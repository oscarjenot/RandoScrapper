# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1] - 2026-02-09

### Added

- Scraper for [randoromandie.com](https://randoromandie.com/): paginates the blog feed, fetches each hike page, parses the info table (Canton, distance, duration, difficulty, etc.), and stores data in SQLite (`data/hikes.db`).
- Streamlit app with multi-select filters: combine several criteria at once (Canton, type de parcours, kilomètres, durée, environnement, difficulté, dénivelé positif, saison).
- Filter logic: AND between dimensions; within Environnement and Saison, match any selected value; "Toute l'année" treated as all four seasons.
- Hike detail view in expanders: link to original post and SuisseMobile, info table (same keys as on the site, no header/index).
- Expander title shows: hike name, canton, actual distance (km), difficulty, D+ (montée).
- CLI `scripts/run_scraper.py` with optional `--max-pages`, `--max-hikes`, `--delay`, `-o` for sample or full scrape.
- Poetry-based setup, README with installation and sample scrape commands, LICENSE (MIT), `.gitignore` (venv, pycache, Cython, etc.).
- `data/hikes.db` tracked in git for deployment (e.g. Streamlit Cloud).
