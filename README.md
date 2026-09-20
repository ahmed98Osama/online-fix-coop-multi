# Online-Fix Co-op & Multiplayer Scraper & Dataset

A modular Python web scraping framework and dataset generator targeting [Online-Fix.me](https://online-fix.me/coop/). It identifies, extracts, and enriches all games that support **both** Cooperative and Multiplayer modes (indicated by `fa fa-check` on both modes), extracts individual game session limits, view counts, release dates, categories, and downloads local poster art.

---

## Features

- **Double-Check Filtering**: Accurately filters game listings requiring `fa fa-check` for **both** Cooperative and Multiplayer modes (skipping entries marked with `fa-times`).
- **Deep Metadata Extraction**:
  - `title`: Clean game title
  - `url`: Direct game link
  - `category`: Extracted from URL path (e.g., `strategy`, `shooter`, `rpg`, `horror`, `arcade`)
  - `coop`: Cooperative player capacity (e.g., `4`, `2`)
  - `multiplayer`: Dedicated multiplayer capacity (e.g., `8`, `1 vs 4`)
  - `views`: Community view / popularity count
  - `post_date` & `post_datetime`: Publication timestamp
  - `release_date`: Official game launch date
  - `play_via`: Network routing platform (e.g., `Steam`, `Epic Games`, `LAN`)
  - `image`: URL to the official poster
- **Direct Image Downloader**: Built-in HTTP downloader with rate limiting, retry backoff, resume capability, and clean Windows-safe naming (`{title} - {category}.jpg`). No external scraping services required for images.
- **Unified CLI (`main.py`)**: Intuitive command-line interface to inspect statistics, run scraping stages independently, or execute the full pipeline.

---

## Dataset Overview

The dataset currently contains **456 games** scraped across 78 listing pages:

| Category | Games Count | Sample Titles |
| :--- | :--- | :--- |
| `strategy` | 68 | R.U.S.E., Age of Empires, Northgard |
| `shooter` | 63 | Sniper Elite, Borderlands, Dying Light |
| `adventures` | 43 | No Man's Sky, Raft, Grounded |
| `arcade` | 38 | Overcooked, Gang Beasts, Cuphead |
| `rpg` | 25 | Remnant II, Elden Ring, Outward |
| `racing` | 20 | GRID 2, Forza Horizon, Dirt Rally |
| `horror` | 13 | Phasmophobia, The Forest, Lethal Company |
| `fighting` | 11 | Mortal Kombat, Tekken |
| `simulation` | 10 | Farming Simulator, Satisfactory |
| *Other / Misc* | 165 | Additional verified co-op & multiplayer titles |

---

## Project Structure

```text
online-fix-coop-multi/
├── data/
│   ├── online-fix-game-details.csv       # Complete CSV dataset (Excel & Pandas ready)
│   ├── online-fix-game-details.json      # Structured JSON dataset
│   ├── online-fix-game-details.md        # Formatted Markdown catalog
│   ├── online-fix-coop-multi-both.json   # Raw listing scrape result
│   ├── online-fix-coop-multi-both.md     # Listing summary table
│   └── _download_log.csv                 # Detailed status log of image downloads
├── images/                               # Local folder containing all 456 poster images
│   └── {Game Title} - {category}.jpg
├── src/
│   ├── __init__.py
│   ├── config.py                         # Path constants, headers, and environment loader
│   ├── utils.py                          # Filename sanitization, category regex, text cleaner
│   ├── listing_scraper.py                # Listing crawler for /coop/ pages (fa-check filter)
│   ├── detail_scraper.py                 # Individual game detail page parser & data exporter
│   └── image_downloader.py               # Robust direct HTTP downloader for game art
├── main.py                               # CLI entrypoint
├── .env.example                          # Environment configuration template
├── .gitignore                            # Standard ignores (keeps .env and images local)
├── requirements.txt                      # Python dependencies
└── README.md                             # Documentation
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- Git

### Installation

1. Clone or navigate to the repository directory:
   ```bash
   cd C:\Users\AhmedOsama\Documents\online-fix-coop-multi
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. *(Optional)* Configure your `.env` file for Firecrawl batch scraping:
   ```bash
   copy .env.example .env
   # Edit .env and enter your FIRECRAWL_API_KEY if desired
   ```

---

## CLI Usage

The project includes a command-line interface through `main.py`:

### 1. View Summary & Stats
Displays dataset breakdown, category distribution, and local images count:
```bash
python main.py summary
```

### 2. Download Images
Downloads all posters directly via HTTP, skipping already downloaded files:
```bash
python main.py download-images --delay 0.5
```

### 3. Scrape Listings
Crawls `/coop/` listing pages and filters for games with both checks:
```bash
python main.py scrape-listings --pages 78
```

### 4. Scrape Game Details
Visits individual game pages to extract player capacities, views, and dates:
```bash
python main.py scrape-details
```

### 5. Run Entire Pipeline
Runs all steps in sequence:
```bash
python main.py run-all --pages 78
```

---

## Data Schema

The primary output file `data/online-fix-game-details.csv` contains the following fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `title` | `string` | Game name |
| `url` | `string` | URL to the game's page on Online-Fix.me |
| `category` | `string` | Game genre parsed from the URL path |
| `coop` | `string` | Maximum cooperative players supported |
| `multiplayer` | `string` | Maximum multiplayer players supported |
| `views` | `integer` | Community view count |
| `post_date` | `string` | Human-readable publication date |
| `post_datetime`| `string` | ISO 8601 publication datetime |
| `image` | `string` | Remote URL of the game poster |
| `release_date` | `string` | Official release date of the game |
| `play_via` | `string` | Network platform used for online play |

---

## Notes & Best Practices

- **Image Download Rate Limits**: When downloading hundreds of images directly from Online-Fix.me, keep the delay at `0.5s` or higher to prevent HTTP 429 rate-limiting.
- **Git Tracking**: Per project configuration, binary poster images (`images/`) and private `.env` files are kept local and excluded from Git commits via `.gitignore`.
