# Website development

The website is a static HTML, CSS and JavaScript application. **Node.js and `npm install` are not required.**

## Run locally

From the repository root:

```bash
python -m http.server 8000 --directory docs
```

Then open <http://localhost:8000>. A local web server is required because browsers block CSV and JSON `fetch` requests when `index.html` is opened directly from disk.

The page loads Leaflet, Papa Parse and Chart.js from public CDNs, so the browser needs an internet connection on first load.

## Refresh the analysis

After replacing `docs/data/points.csv`, regenerate the analysis payload with:

```bash
python scripts/generate_eda.py
```

This writes `docs/data/eda_summary.json`, which powers the summary statistics and charts.

## Main website files

- `index.html` — page structure and dataset documentation
- `styles.css` — responsive visual design
- `app.js` — map, filters, observation cards and charts
- `data/points.csv` — curated observation data
- `data/eda_summary.json` — generated exploratory-analysis results
