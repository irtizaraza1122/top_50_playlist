"""Data loading, validation, feature engineering and KPI helpers for the
US Top 50 Playlist project (Atlantic Recording Corporation).

Used by both the Streamlit dashboard (app.py) and the report generator
(run_analysis.py) so every number in the report matches the dashboard.
"""
import re
import numpy as np
import pandas as pd

PROTECTED_ACTS = ["Earth, Wind & Fire", "Simon & Garfunkel", "Brooks & Dunn",
                  "Hall & Oates", "Tyler, The Creator"]
JUNK_CREDITS = {"sped up + slowed", "sped up", "slowed"}


# --------------------------------------------------------------------------
# 1. Ingestion & validation
# --------------------------------------------------------------------------
def standardize_artist(name: str) -> str:
    name = re.sub(r"\s+", " ", str(name)).strip()
    return name


def primary_artist(name: str) -> str:
    """First credited artist, keeping band names that contain '&' or ','."""
    for act in PROTECTED_ACTS:
        if name.startswith(act):
            return act
    return name.split(" & ")[0].strip()


def all_credits(name: str) -> list:
    """Every credited artist in an 'A & B & C' string (protected acts kept whole)."""
    tmp = name
    keep = {}
    for i, act in enumerate(PROTECTED_ACTS):
        if act in tmp:
            tmp = tmp.replace(act, f"@@{i}@@")
            keep[f"@@{i}@@"] = act
    parts = [p.strip() for p in tmp.split(" & ")]
    parts = [keep.get(p, p) for p in parts]
    return [p for p in parts if p and p.lower() not in JUNK_CREDITS]


# The dates are used exactly as supplied in the file. If you decide the file's
# dates are offset (see README, "Date check"), set this to -1 to shift them.
DATE_SHIFT_YEARS = 0


def load_and_clean(path: str):
    """Returns (clean_df, quality_report_dict)."""
    raw = pd.read_csv(path)
    q = {"raw_rows": len(raw)}
    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    if DATE_SHIFT_YEARS:
        df["date"] = df["date"] + pd.DateOffset(years=DATE_SHIFT_YEARS)
    q["date_min"], q["date_max"] = df["date"].min(), df["date"].max()
    q["snapshot_days"] = df["date"].nunique()
    full = pd.date_range(q["date_min"], q["date_max"])
    q["missing_days"] = [d.date().isoformat() for d in sorted(set(full) - set(df["date"]))]
    q["calendar_days"] = len(full)

    # rank range
    q["rank_out_of_range"] = int((~df["position"].between(1, 50)).sum())

    # exact duplicates and days with more than 50 rows
    q["exact_duplicate_rows"] = int(df.duplicated().sum())
    per_day = df.groupby("date").size()
    q["days_with_extra_rows"] = {d.date().isoformat(): int(n) for d, n in per_day[per_day != 50].items()}
    # keep the first snapshot block for a date that was loaded twice
    before = len(df)
    df = df.drop_duplicates(subset=["date", "position"], keep="first")
    q["rows_dropped_duplicate_position"] = before - len(df)
    df = df.drop_duplicates(subset=["date", "song", "artist"], keep="first")

    # artist standardization
    df["artist"] = df["artist"].map(standardize_artist)
    canon = (df.groupby(df["artist"].str.lower())["artist"]
               .agg(lambda s: s.value_counts().index[0]))
    q["artist_case_variants_merged"] = int(
        (df.groupby(df["artist"].str.lower())["artist"].nunique() > 1).sum())
    df["artist"] = df["artist"].str.lower().map(canon)
    df["primary_artist"] = df["artist"].map(primary_artist)
    df["song_id"] = df["song"] + " \u2014 " + df["artist"]

    # popularity = 0 is an API gap, not a real score
    q["popularity_zero_rows"] = int((df["popularity"] == 0).sum())
    df["popularity_raw"] = df["popularity"]
    df["popularity"] = df["popularity"].where(df["popularity"] > 0)

    df["duration_min"] = df["duration_ms"] / 60000.0
    df["rank_band"] = pd.cut(df["position"], [0, 10, 20, 50],
                             labels=["Top 10", "Top 11-20", "Top 21-50"])
    df["is_explicit"] = df["is_explicit"].astype(bool)
    df = df.sort_values(["date", "position"]).reset_index(drop=True)
    q["clean_rows"] = len(df)
    q["unique_songs"] = df["song_id"].nunique()
    q["unique_artists_full"] = df["artist"].nunique()
    q["unique_primary_artists"] = df["primary_artist"].nunique()
    return df, q


# --------------------------------------------------------------------------
# 2. Feature engineering
# --------------------------------------------------------------------------
def song_features(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("song_id")
    s = g.agg(song=("song", "first"), artist=("artist", "first"),
              primary_artist=("primary_artist", "first"),
              days_on_chart=("date", "nunique"),
              first_seen=("date", "min"), last_seen=("date", "max"),
              avg_rank=("position", "mean"), best_rank=("position", "min"),
              worst_rank=("position", "max"),
              rank_volatility=("position", "std"),
              avg_popularity=("popularity", "mean"),
              duration_min=("duration_min", "first"),
              is_explicit=("is_explicit", "first"),
              album_type=("album_type", "first"),
              total_tracks=("total_tracks", "first")).reset_index()
    s["rank_volatility"] = s["rank_volatility"].fillna(0.0)
    s["span_days"] = (s["last_seen"] - s["first_seen"]).dt.days + 1
    s["days_in_top10"] = s["song_id"].map(df[df.position <= 10].groupby("song_id")["date"].nunique()).fillna(0).astype(int)
    return s


def add_popularity_trend(df: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    """Popularity Trend Score = rolling mean of a song's popularity (per song, by date)."""
    out = df.sort_values(["song_id", "date"]).copy()
    out["popularity_trend"] = (out.groupby("song_id")["popularity"]
                               .transform(lambda x: x.rolling(window, min_periods=1).mean()))
    return out.sort_values(["date", "position"])


def artist_features(df: pd.DataFrame, by: str = "primary_artist") -> pd.DataFrame:
    total_slots = len(df)
    a = df.groupby(by).agg(unique_songs=("song_id", "nunique"),
                           chart_days=("date", "nunique"),
                           appearances=("position", "size"),
                           avg_rank=("position", "mean"),
                           best_rank=("position", "min"),
                           avg_popularity=("popularity", "mean")).reset_index()
    a["dominance_index"] = a["appearances"] / total_slots * 100  # % of all chart slots
    return a.sort_values("appearances", ascending=False).reset_index(drop=True)


def daily_artist_share(df: pd.DataFrame, artists, freq="MS") -> pd.DataFrame:
    d = df[df["primary_artist"].isin(artists)].copy()
    d["period"] = d["date"].dt.to_period("M").dt.to_timestamp()
    share = d.groupby(["period", "primary_artist"]).size().rename("slots").reset_index()
    tot = df.assign(period=df["date"].dt.to_period("M").dt.to_timestamp()).groupby("period").size()
    share["share_pct"] = share["slots"] / share["period"].map(tot) * 100
    return share


# --------------------------------------------------------------------------
# 3. Rank movement
# --------------------------------------------------------------------------
def daily_movement(df: pd.DataFrame) -> pd.DataFrame:
    """Day-over-day rank change per song (only on consecutive snapshots),
    plus entry / exit counts per date."""
    d = df[["date", "song_id", "position"]].sort_values(["song_id", "date"]).copy()
    d["prev_date"] = d.groupby("song_id")["date"].shift()
    d["prev_pos"] = d.groupby("song_id")["position"].shift()
    d["gap"] = (d["date"] - d["prev_date"]).dt.days
    d["move"] = d["prev_pos"] - d["position"]          # +ve = climbed
    d.loc[d["gap"] != 1, "move"] = np.nan
    return d.sort_values(["date", "position"])


def entries_exits(df: pd.DataFrame) -> pd.DataFrame:
    days = sorted(df["date"].unique())
    sets = {d: set(df.loc[df["date"] == d, "song_id"]) for d in days}
    rows = []
    for prev, cur in zip(days[:-1], days[1:]):
        if (cur - prev).days != 1:
            continue
        rows.append({"date": cur, "new_entries": len(sets[cur] - sets[prev]),
                     "exits": len(sets[prev] - sets[cur])})
    return pd.DataFrame(rows)


def fast_risers(df: pd.DataFrame, min_days: int = 5, window: int = 7) -> pd.DataFrame:
    """Songs with biggest average daily climb over their first `window` days (entry momentum)."""
    d = df.sort_values(["song_id", "date"]).copy()
    d["n"] = d.groupby("song_id").cumcount()
    first = d[d["n"] == 0].set_index("song_id")["position"]
    early = d[(d["n"] == window - 1)].set_index("song_id")["position"]
    r = pd.concat([first.rename("entry_rank"), early.rename(f"rank_day_{window}")], axis=1).dropna()
    r["climb"] = r["entry_rank"] - r[f"rank_day_{window}"]
    return r.sort_values("climb", ascending=False)


def slow_decliners(sf: pd.DataFrame, df: pd.DataFrame, min_days: int = 60) -> pd.DataFrame:
    """Long-running songs ordered by how gradually their rank worsens (slope of rank vs time)."""
    rows = []
    for sid, g in df.groupby("song_id"):
        if len(g) < min_days:
            continue
        x = (g["date"] - g["date"].min()).dt.days.values
        slope = np.polyfit(x, g["position"].values, 1)[0]
        rows.append((sid, slope, len(g)))
    o = pd.DataFrame(rows, columns=["song_id", "rank_slope_per_day", "days_on_chart"])
    return o.merge(sf[["song_id", "song", "artist", "best_rank", "avg_rank"]], on="song_id")


# --------------------------------------------------------------------------
# 4. KPIs
# --------------------------------------------------------------------------
def kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    sf = song_features(df)
    af = artist_features(df)
    return {
        "snapshots": df["date"].nunique(),
        "unique_songs": df["song_id"].nunique(),
        "unique_artists": df["primary_artist"].nunique(),
        "median_days_on_chart": float(sf["days_on_chart"].median()),
        "avg_rank_overall": float(df["position"].mean()),
        "avg_rank_volatility": float(sf.loc[sf.days_on_chart >= 7, "rank_volatility"].mean()),
        "avg_popularity": float(df["popularity"].mean()),
        "explicit_share_pct": float(df["is_explicit"].mean() * 100),
        "top_artist": af.iloc[0]["primary_artist"],
        "top_artist_dominance_pct": float(af.iloc[0]["dominance_index"]),
    }
