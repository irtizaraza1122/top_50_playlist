"""US Top 50 Playlist Performance & Song Popularity Trend Analysis
Streamlit dashboard for Atlantic Recording Corporation.

Run:  streamlit run app.py
"""
import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analytics as A

st.set_page_config(page_title="US Top 50 Playlist Analytics", page_icon="🎵", layout="wide")
DATA_PATH = Path(__file__).parent / "data" / "Atlantic_United_States.csv"
BLUE, ORANGE, GREY = "#1B4F72", "#E67E22", "#95A5A6"


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading and validating data...")
def load(src):
    if isinstance(src, bytes):
        src = io.BytesIO(src)
    df, quality = A.load_and_clean(src)
    df = A.add_popularity_trend(df)
    return df, quality


st.sidebar.title("🎵 Filters")
upload = st.sidebar.file_uploader("Use a different CSV (optional)", type="csv")
try:
    df_all, quality = load(upload.getvalue() if upload else str(DATA_PATH))
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not load the data: {exc}")
    st.stop()

dmin, dmax = df_all["date"].min().date(), df_all["date"].max().date()
date_range = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Pick both a start and an end date in the sidebar.")
    st.stop()
rank_lo, rank_hi = st.sidebar.slider("Rank range", 1, 50, (1, 50))
album_opts = sorted(df_all["album_type"].unique())
album_sel = st.sidebar.multiselect("Album type", album_opts, default=album_opts)
explicit_sel = st.sidebar.radio("Explicit content", ["All", "Explicit only", "Non-explicit only"])
artist_opts = A.artist_features(df_all)["primary_artist"].tolist()   # most frequent first
artist_sel = st.sidebar.multiselect("Artist (primary credit)", artist_opts)
song_query = st.sidebar.text_input("Song title contains")

f = df_all[(df_all["date"].dt.date >= date_range[0]) & (df_all["date"].dt.date <= date_range[1])
           & df_all["position"].between(rank_lo, rank_hi) & df_all["album_type"].isin(album_sel)]
if explicit_sel == "Explicit only":
    f = f[f["is_explicit"]]
elif explicit_sel == "Non-explicit only":
    f = f[~f["is_explicit"]]
if artist_sel:
    f = f[f["primary_artist"].isin(artist_sel)]
if song_query:
    f = f[f["song"].str.contains(song_query, case=False, regex=False)]
if f.empty:
    st.warning("No rows match the current filters.")
    st.stop()

sf = A.song_features(f)
af = A.artist_features(f)
fp = f.dropna(subset=["popularity"])

st.title("US Top 50 Playlist Performance & Song Popularity Trends")
st.caption(f"{len(f):,} chart slots · {f['date'].nunique()} daily snapshots · "
           f"{f['date'].min():%d %b %Y} to {f['date'].max():%d %b %Y} · Atlantic Recording Corporation")

k = A.kpis(f)
c = st.columns(6)
c[0].metric("Median days on chart", f"{k['median_days_on_chart']:.0f}")
c[1].metric("Average rank", f"{k['avg_rank_overall']:.1f}")
c[2].metric("Rank volatility index", f"{k['avg_rank_volatility']:.1f}",
            help="Mean std. deviation of rank, songs with 7+ days on chart")
c[3].metric("Avg popularity", f"{k['avg_popularity']:.1f}")
c[4].metric("Explicit share", f"{k['explicit_share_pct']:.1f}%")
c[5].metric("Top artist dominance", f"{k['top_artist_dominance_pct']:.1f}%", help=f"{k['top_artist']}: share of chart slots")

tabs = st.tabs(["Playlist timeline", "Song trends", "Artist dominance", "Popularity vs rank",
                "Explicit vs non-explicit", "Content attributes", "Data & quality"])

# ----------------------------------------------------------------------------
# 1. Playlist timeline explorer
# ----------------------------------------------------------------------------
with tabs[0]:
    st.subheader("Playlist timeline explorer")
    days = sorted(f["date"].dt.date.unique())
    if len(days) > 1:
        pick = st.select_slider("Snapshot date", options=days, value=days[-1], format_func=lambda d: d.strftime("%d %b %Y"))
    else:
        pick = days[0]
    snap = f[f["date"].dt.date == pick].sort_values("position")
    prev_days = [d for d in days if d < pick]
    if prev_days:
        prev = f[f["date"].dt.date == prev_days[-1]].set_index("song_id")["position"]
        snap = snap.assign(change=snap["song_id"].map(prev).sub(snap["position"]))
    cols = ["position", "album_cover_url", "song", "artist", "popularity", "duration_min", "album_type", "is_explicit"]
    if "change" in snap:
        cols.insert(1, "change")
    st.dataframe(snap[cols], hide_index=True, column_config={
        "album_cover_url": st.column_config.ImageColumn("Cover"),
        "change": st.column_config.NumberColumn("Move vs prev. snapshot", help="+ = climbed, blank = new entry"),
        "duration_min": st.column_config.NumberColumn("Minutes", format="%.2f"),
        "is_explicit": st.column_config.CheckboxColumn("Explicit")})

    st.markdown("#### Rank distribution of the longest-running songs")
    top = sf.sort_values("days_on_chart", ascending=False).head(15)
    band = (f[f["song_id"].isin(top["song_id"])].groupby(["song_id", "rank_band"], observed=True)
            .size().rename("days").reset_index().merge(top[["song_id", "song"]], on="song_id"))
    fig = px.bar(band, y="song", x="days", color="rank_band", orientation="h",
                 category_orders={"song": top["song"].tolist()[::-1], "rank_band": ["Top 10", "Top 11-20", "Top 21-50"]},
                 color_discrete_sequence=[BLUE, ORANGE, GREY], labels={"days": "Days", "song": ""})
    fig.update_layout(height=480, legend_title="")
    st.plotly_chart(fig)

    left, right = st.columns(2)
    with left:
        st.markdown("#### Entries and exits")
        ee = A.entries_exits(f)
        if ee.empty:
            st.caption("Not enough consecutive snapshots in the current selection.")
        else:
            e = ee.set_index("date").rolling(7, min_periods=1).mean().reset_index().melt("date", var_name="type", value_name="songs per day")
            st.plotly_chart(px.line(e, x="date", y="songs per day", color="type", color_discrete_sequence=[BLUE, ORANGE]))
            st.caption("7-day average. Computed on the filtered view, so rank/artist filters change what counts as an entry or exit.")
    with right:
        st.markdown("#### Rank movement")
        mv = A.daily_movement(f)["move"].dropna()
        if mv.empty:
            st.caption("No consecutive-day movements in the current selection.")
        else:
            st.plotly_chart(px.histogram(mv.clip(-15, 15), nbins=31, labels={"value": "Day-over-day change (+ = climbed)"},
                                         color_discrete_sequence=[BLUE]).update_layout(showlegend=False))

    st.markdown("#### Fast risers and slow decliners")
    a, b = st.columns(2)
    window = a.slider("Fast risers: days after entry", 3, 14, 7)
    fr = A.fast_risers(f, window=window).head(10).reset_index().merge(sf[["song_id", "song", "artist"]], on="song_id")
    a.dataframe(fr[["song", "artist", "entry_rank", f"rank_day_{window}", "climb"]], hide_index=True)
    min_days = b.slider("Slow decliners: minimum days on chart", 30, 200, 100)
    sd = A.slow_decliners(sf, f, min_days)
    sd = sd[(sd["rank_slope_per_day"] > 0)].sort_values("rank_slope_per_day").head(10)
    b.dataframe(sd[["song", "artist", "days_on_chart", "rank_slope_per_day"]], hide_index=True,
                column_config={"rank_slope_per_day": st.column_config.NumberColumn("Places lost / day", format="%.3f")})
    b.caption("Songs that lose rank most gradually after a long run.")

# ----------------------------------------------------------------------------
# 2. Song trends
# ----------------------------------------------------------------------------
with tabs[1]:
    st.subheader("Song ranking trend charts")
    labels = sf.sort_values("days_on_chart", ascending=False)
    options = labels["song_id"].tolist()
    names = dict(zip(labels["song_id"], labels["song"] + " - " + labels["artist"]))
    chosen = st.multiselect("Songs", options, default=options[:5], format_func=lambda s: names[s])
    if chosen:
        sel = f[f["song_id"].isin(chosen)].copy()
        sel["label"] = sel["song_id"].map(names)
        fig = px.line(sel, x="date", y="position", color="label", labels={"position": "Rank", "label": ""})
        fig.update_yaxes(autorange="reversed", range=[50.5, 0.5])
        fig.update_layout(height=420, legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig)
        fig2 = px.line(sel.dropna(subset=["popularity_trend"]), x="date", y="popularity_trend", color="label",
                       labels={"popularity_trend": "Popularity (7-day rolling avg)", "label": ""})
        fig2.update_layout(height=360, legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig2)
    st.markdown("#### Song scorecard")
    show = sf.sort_values("days_on_chart", ascending=False)[
        ["song", "artist", "days_on_chart", "avg_rank", "best_rank", "rank_volatility", "avg_popularity", "days_in_top10"]]
    st.dataframe(show, hide_index=True, column_config={
        "avg_rank": st.column_config.NumberColumn(format="%.1f"), "rank_volatility": st.column_config.NumberColumn("Volatility", format="%.1f"),
        "avg_popularity": st.column_config.NumberColumn(format="%.1f")})
    st.markdown("#### Peak rank vs longevity")
    fig = px.scatter(sf, x="best_rank", y="days_on_chart", hover_data=["song", "artist"], log_y=True, opacity=0.5,
                     labels={"best_rank": "Best rank achieved", "days_on_chart": "Days on chart (log)"}, color_discrete_sequence=[BLUE])
    st.plotly_chart(fig)

# ----------------------------------------------------------------------------
# 3. Artist dominance
# ----------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Artist dominance leaderboard")
    n_top = st.slider("Artists to show", 5, 30, 15)
    credit = st.radio("Count artists by", ["Primary credit", "Full credit string"], horizontal=True)
    af2 = A.artist_features(f, "primary_artist" if credit == "Primary credit" else "artist")
    key = af2.columns[0]
    top = af2.head(n_top).iloc[::-1]
    fig = px.bar(top, y=key, x="dominance_index", orientation="h", hover_data=["unique_songs", "chart_days", "appearances"],
                 labels={"dominance_index": "Artist Dominance Index (% of chart slots)", key: ""}, color_discrete_sequence=[BLUE])
    fig.update_layout(height=max(380, 24 * n_top))
    st.plotly_chart(fig)
    st.dataframe(af2.head(n_top), hide_index=True, column_config={
        "dominance_index": st.column_config.NumberColumn("Dominance %", format="%.2f"),
        "avg_rank": st.column_config.NumberColumn(format="%.1f"), "avg_popularity": st.column_config.NumberColumn(format="%.1f")})
    st.markdown("#### Dominance over time")
    default_artists = af["primary_artist"].head(5).tolist()
    pick = st.multiselect("Artists", af["primary_artist"].tolist(), default=default_artists)
    if pick:
        ds = A.daily_artist_share(f, pick)
        st.plotly_chart(px.line(ds, x="period", y="share_pct", color="primary_artist", markers=True,
                                labels={"share_pct": "Share of monthly slots (%)", "period": "", "primary_artist": ""}))
        st.caption("Share is measured within the filtered view; first and last months may be partial.")
    st.markdown("#### Repeat appearances")
    st.plotly_chart(px.scatter(af.head(60), x="unique_songs", y="chart_days", size="appearances", hover_name="primary_artist",
                               labels={"unique_songs": "Unique songs charted", "chart_days": "Days on chart"}, color_discrete_sequence=[ORANGE]))

# ----------------------------------------------------------------------------
# 4. Popularity vs rank
# ----------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Popularity vs rank")
    if fp.empty:
        st.info("No popularity data in this selection.")
    else:
        rho = fp["position"].corr(fp["popularity"], method="spearman")
        st.metric("Spearman correlation (rank vs popularity)", f"{rho:.2f}", help="Negative = better (lower) rank numbers go with higher popularity")
        samp = fp.sample(min(6000, len(fp)), random_state=1)
        fig = px.scatter(samp, x="position", y="popularity", opacity=0.25, hover_data=["song", "artist", "date"], color_discrete_sequence=[BLUE],
                         labels={"position": "Playlist position", "popularity": "Popularity score"})
        mean_line = fp.groupby("position")["popularity"].mean().reset_index()
        fig.add_trace(go.Scatter(x=mean_line["position"], y=mean_line["popularity"], mode="lines", name="Mean popularity", line=dict(color=ORANGE, width=3)))
        st.plotly_chart(fig)
        l, r = st.columns(2)
        l.markdown("#### Distribution by rank band")
        l.plotly_chart(px.box(fp, x="rank_band", y="popularity", category_orders={"rank_band": ["Top 10", "Top 11-20", "Top 21-50"]},
                              color_discrete_sequence=[BLUE], labels={"rank_band": "", "popularity": "Popularity"}))
        r.markdown("#### Popularity stability vs chart volatility")
        stab = sf[sf["days_on_chart"] >= 14].copy()
        stab["popularity_std"] = stab["song_id"].map(fp.groupby("song_id")["popularity"].std()).fillna(0)
        r.plotly_chart(px.scatter(stab, x="popularity_std", y="rank_volatility", size="days_on_chart", hover_data=["song", "artist"],
                                  color_discrete_sequence=[ORANGE], labels={"popularity_std": "Popularity std. dev.", "rank_volatility": "Rank volatility index"}))
        st.caption("Popularity scores of 0 are treated as missing (API gaps) and excluded here.")

# ----------------------------------------------------------------------------
# 5. Explicit vs non-explicit
# ----------------------------------------------------------------------------
def group_panel(frame, songs, col, labels):
    rows = frame.groupby(col).agg(slots=("position", "size"), avg_rank=("position", "mean"), avg_popularity=("popularity", "mean"),
                                  top10_share=("position", lambda x: (x <= 10).mean() * 100)).reset_index()
    sg = songs.groupby(col).agg(songs=("song_id", "size"), median_days=("days_on_chart", "median"), mean_days=("days_on_chart", "mean")).reset_index()
    out = rows.merge(sg, on=col)
    out[col] = out[col].map(labels).fillna(out[col].astype(str))
    return out


with tabs[4]:
    st.subheader("Explicit vs non-explicit performance")
    panel = group_panel(f, sf, "is_explicit", {True: "Explicit", False: "Non-explicit"})
    st.dataframe(panel, hide_index=True, column_config={c_: st.column_config.NumberColumn(format="%.2f") for c_ in
                                                        ["avg_rank", "avg_popularity", "top10_share", "median_days", "mean_days"]})
    l, r = st.columns(2)
    l.plotly_chart(px.bar(panel, x="is_explicit", y="top10_share", color_discrete_sequence=[BLUE], labels={"is_explicit": "", "top10_share": "% of slots in Top 10"}))
    r.plotly_chart(px.bar(panel, x="is_explicit", y="median_days", color_discrete_sequence=[ORANGE], labels={"is_explicit": "", "median_days": "Median days on chart"}))
    trend = f.assign(month=f["date"].dt.to_period("M").dt.to_timestamp()).groupby("month")["is_explicit"].mean().mul(100).reset_index()
    st.markdown("#### Explicit Content Share over time")
    st.plotly_chart(px.line(trend, x="month", y="is_explicit", markers=True, labels={"is_explicit": "Explicit share of slots (%)", "month": ""}, color_discrete_sequence=[BLUE]))
    by_band = f.groupby("rank_band", observed=True)["is_explicit"].mean().mul(100).reset_index()
    st.markdown("#### Explicit share by rank band")
    st.plotly_chart(px.bar(by_band, x="rank_band", y="is_explicit", color_discrete_sequence=[ORANGE], labels={"rank_band": "", "is_explicit": "Explicit share (%)"}))

# ----------------------------------------------------------------------------
# 6. Content attributes
# ----------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Single vs album, duration and album size")
    panel = group_panel(f, sf, "album_type", {})
    st.dataframe(panel, hide_index=True, column_config={c_: st.column_config.NumberColumn(format="%.2f") for c_ in
                                                        ["avg_rank", "avg_popularity", "top10_share", "median_days", "mean_days"]})
    l, r = st.columns(2)
    l.plotly_chart(px.bar(panel, x="album_type", y="avg_popularity", color_discrete_sequence=[BLUE], labels={"album_type": "", "avg_popularity": "Avg popularity"}).update_yaxes(range=[70, 100]))
    r.plotly_chart(px.bar(panel, x="album_type", y="median_days", color_discrete_sequence=[ORANGE], labels={"album_type": "", "median_days": "Median days on chart"}))

    st.markdown("#### Song duration")
    sf2 = sf.assign(duration_bin=pd.cut(sf["duration_min"], [0, 2.5, 3, 3.5, 4, 5, 20], labels=["<2.5", "2.5-3", "3-3.5", "3.5-4", "4-5", "5+"]))
    dur = sf2.groupby("duration_bin", observed=True).agg(songs=("song_id", "size"), median_days=("days_on_chart", "median"),
                                                          avg_rank=("avg_rank", "mean"), avg_popularity=("avg_popularity", "mean")).reset_index()
    l, r = st.columns(2)
    l.plotly_chart(px.bar(dur, x="duration_bin", y="median_days", color_discrete_sequence=[BLUE], labels={"duration_bin": "Minutes", "median_days": "Median days on chart"}))
    r.plotly_chart(px.bar(dur, x="duration_bin", y="avg_rank", color_discrete_sequence=[ORANGE], labels={"duration_bin": "Minutes", "avg_rank": "Average rank (lower = better)"}))
    if not fp.empty:
        st.caption(f"Spearman: duration vs popularity {fp['duration_min'].corr(fp['popularity'], method='spearman'):.2f}, "
                   f"duration vs rank {f['duration_min'].corr(f['position'], method='spearman'):.2f}")

    st.markdown("#### Album size (total tracks)")
    sf3 = sf.assign(size_bin=pd.cut(sf["total_tracks"], [0, 1, 3, 10, 15, 20, 200], labels=["1", "2-3", "4-10", "11-15", "16-20", "21+"]))
    tr = sf3.groupby("size_bin", observed=True).agg(songs=("song_id", "size"), median_days=("days_on_chart", "median"),
                                                     avg_rank=("avg_rank", "mean"), avg_popularity=("avg_popularity", "mean")).reset_index()
    l, r = st.columns(2)
    l.plotly_chart(px.bar(tr, x="size_bin", y="median_days", color_discrete_sequence=[BLUE], labels={"size_bin": "Tracks on release", "median_days": "Median days on chart"}))
    r.plotly_chart(px.bar(tr, x="size_bin", y="avg_popularity", color_discrete_sequence=[ORANGE], labels={"size_bin": "Tracks on release", "avg_popularity": "Avg popularity"}).update_yaxes(range=[60, 100]))

# ----------------------------------------------------------------------------
# 7. Data & quality
# ----------------------------------------------------------------------------
with tabs[6]:
    st.subheader("Data validation summary")
    q = quality
    st.markdown(f"""
- **Raw rows:** {q['raw_rows']:,} → **clean rows:** {q['clean_rows']:,}
- **Snapshots:** {q['snapshot_days']} of {q['calendar_days']} calendar days (missing: {', '.join(q['missing_days']) or 'none'})
- **Rank outside 1–50:** {q['rank_out_of_range']}
- **Exact duplicate rows:** {q['exact_duplicate_rows']} · **dates with more than 50 rows:** {q['days_with_extra_rows']} (the first block was kept)
- **Popularity = 0 rows treated as missing:** {q['popularity_zero_rows']}
- **Artist formatting variants merged:** {q['artist_case_variants_merged']}
- **Unique songs (song + artist):** {q['unique_songs']:,} · **unique primary artists:** {q['unique_primary_artists']}
""")
    st.warning("Date check: several well-known release events appear one year later than their real-world dates "
               "(see README). Dates are shown exactly as supplied in the file.")
    st.download_button("Download filtered data (CSV)", f.drop(columns=["popularity_trend"]).to_csv(index=False).encode("utf-8"),
                       file_name="top50_filtered.csv", mime="text/csv")
    st.dataframe(f.drop(columns=["album_cover_url"]).head(500), hide_index=True)
