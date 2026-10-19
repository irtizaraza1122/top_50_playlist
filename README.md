# US Top 50 Playlist Performance and Song Popularity Trend Analysis

Unified Mentor project for Atlantic Recording Corporation. Contents:

| File | Purpose |
|---|---|
| `app.py` | Streamlit dashboard (7 tabs, sidebar filters) |
| `analytics.py` | Data loading, validation, feature engineering, KPIs (shared by everything) |
| `run_analysis.py` | Regenerates every chart in `figures/` and the numbers in `stats.json` |
| `build_report.js` | Builds the two Word documents in `report/` from `stats.json` and `figures/` |
| `data/Atlantic_United_States.csv` | The dataset |
| `report/` | Research report and one-page executive summary (.docx) |

## Run the dashboard (first time)

1. Install Python 3.10 or newer from python.org (tick "Add Python to PATH" on Windows).
2. Open a terminal (Command Prompt / PowerShell on Windows, Terminal on Mac) **inside this folder**.
3. Install the libraries (one time only):
   ```
   pip install -r requirements.txt
   ```
4. Start the app:
   ```
   streamlit run app.py
   ```
5. Your browser opens at http://localhost:8501. Press `Ctrl+C` in the terminal to stop it.

If `pip` or `streamlit` is not found, try `python -m pip install -r requirements.txt` and `python -m streamlit run app.py`.

## Data cleaning (what `analytics.py` does)

- Rank range 1-50 checked (no violations).
- 1 March 2025 contains two different 50-song lists (100 rows, 10 exact duplicates). The first block is kept.
- 4 calendar days are missing (14 Mar, 25 Mar, 11 Jul, 13 Aug 2025). They are left as gaps; day-over-day movement is only measured across consecutive days.
- `popularity = 0` (189 rows) is treated as missing, not as a real score.
- Artist names trimmed; one case variant merged (Charli XCX / Charli xcx). Primary artist = first credit, keeping band names such as "Earth, Wind & Fire".
- A song is identified by title + artist.

## Date check (please read)

The dates are used exactly as in the file (18 May 2024 to 27 Nov 2025), but several real-world events appear one year late.
For example, Tyler, The Creator's CHROMAKOPIA (released late Oct 2024) tops the 31 Oct 2025 snapshot, and "Die With A Smile"
shows 103 days on chart, which matches Aug-Nov 2024. Ask the data provider to confirm. If the dates are offset, set
`DATE_SHIFT_YEARS = -1` in `analytics.py`, then re-run:

```
python run_analysis.py
node build_report.js     # needs Node.js and: npm install docx
```

The dashboard picks up the change automatically. Rankings, longevity, artist and attribute results do not change; only the calendar labels do.
