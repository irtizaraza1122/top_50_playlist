"""Runs the full analysis, writes figures/ and stats.json for the report."""
import json, warnings
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from scipy import stats
import analytics as A

warnings.filterwarnings("ignore")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 10.5,
                     "figure.dpi": 100, "savefig.dpi": 170, "savefig.bbox": "tight"})
C1, C2, C3, GREY = "#1B4F72", "#E67E22", "#7F8C8D", "#BDC3C7"
FIG = "figures/"

df, q = A.load_and_clean("data/Atlantic_United_States.csv")
df = A.add_popularity_trend(df)
sf = A.song_features(df)
af = A.artist_features(df)
d = df.dropna(subset=["popularity"])
S = {"quality": {k: (str(v) if isinstance(v, pd.Timestamp) else v) for k, v in q.items()}}

# ---------------- longevity ----------------
S["days_dist"] = sf.days_on_chart.describe().round(1).to_dict()
S["share_songs_le7"] = float((sf.days_on_chart <= 7).mean() * 100)
S["n_ge100"] = int((sf.days_on_chart >= 100).sum())
S["share_songs_ge100"] = float((sf.days_on_chart >= 100).mean() * 100)
S["share_slots_from_ge100"] = float(df.song_id.isin(sf[sf.days_on_chart >= 100].song_id).mean() * 100)
S["peak_vs_longevity_spearman"] = float(stats.spearmanr(sf.best_rank, sf.days_on_chart)[0])
S["n1_songs"] = int((sf.best_rank == 1).sum())
S["n1_median_days"] = float(sf[sf.best_rank == 1].days_on_chart.median())
S["non_n1_median_days"] = float(sf[sf.best_rank > 1].days_on_chart.median())
S["top10_peak_median_days"] = float(sf[sf.best_rank <= 10].days_on_chart.median())
S["never_top10_median_days"] = float(sf[sf.best_rank > 10].days_on_chart.median())
S["n_never_top10"] = int((sf.best_rank > 10).sum())
S["top_songs"] = (sf.sort_values("days_on_chart", ascending=False).head(10)
                  [["song", "artist", "days_on_chart", "avg_rank", "best_rank", "rank_volatility", "avg_popularity"]]
                  .round(1).to_dict("records"))
S["top_pop_songs"] = (sf[sf.days_on_chart >= 30].sort_values("avg_popularity", ascending=False).head(8)
                      [["song", "artist", "days_on_chart", "avg_popularity", "avg_rank"]].round(1).to_dict("records"))
S["most_stable"] = (sf[sf.days_on_chart >= 100].sort_values("rank_volatility").head(5)
                    [["song", "artist", "days_on_chart", "avg_rank", "rank_volatility"]].round(1).to_dict("records"))
S["most_volatile"] = (sf[sf.days_on_chart >= 100].sort_values("rank_volatility", ascending=False).head(5)
                      [["song", "artist", "days_on_chart", "avg_rank", "rank_volatility"]].round(1).to_dict("records"))
S["vol_median_long"] = float(sf[sf.days_on_chart >= 100].rank_volatility.median())

# ---------------- movement ----------------
mv = A.daily_movement(df)
m = mv.move.dropna()
S["mean_abs_move"] = float(m.abs().mean()); S["median_abs_move"] = float(m.abs().median())
S["pct_no_change"] = float((m == 0).mean() * 100); S["pct_move_le3"] = float((m.abs() <= 3).mean() * 100)
S["pct_move_ge10"] = float((m.abs() >= 10).mean() * 100)
bands = [(1, 5), (6, 10), (11, 20), (21, 35), (36, 50)]
S["absmove_by_band"] = {f"{a}-{b}": float(mv[(mv.prev_pos >= a) & (mv.prev_pos <= b)].move.abs().mean()) for a, b in bands}
ee = A.entries_exits(df)
S["avg_new_entries"] = float(ee.new_entries.mean()); S["median_new_entries"] = float(ee.new_entries.median())
big = ee.sort_values("new_entries", ascending=False).head(3)
S["big_turnover_days"] = [{"date": r.date.strftime("%d %b %Y"), "entries": int(r.new_entries)} for r in big.itertuples()]
S["days_entries_ge10"] = int((ee.new_entries >= 10).sum()); S["days_entries_le3"] = int((ee.new_entries <= 3).sum())
first = df.sort_values(["song_id", "date"]).groupby("song_id").first()
last = df.sort_values(["song_id", "date"]).groupby("song_id").last()
S["entry_rank_median"] = float(first.position.median())
S["pct_enter_top10"] = float((first.position <= 10).mean() * 100)
S["pct_enter_lower25"] = float((first.position > 25).mean() * 100)
S["pct_exit_from_lower25"] = float((last.position > 25).mean() * 100)
S["pct_exit_from_top10"] = float((last.position <= 10).mean() * 100)
fr = A.fast_risers(df).head(8).reset_index().merge(sf[["song_id", "song", "artist"]], on="song_id")
S["fast_risers"] = fr[["song", "artist", "entry_rank", "rank_day_7", "climb"]].to_dict("records")
sd = A.slow_decliners(sf, df, 100)
slow = sd[(sd.rank_slope_per_day > 0) & (sd.rank_slope_per_day < 0.1)].sort_values("days_on_chart", ascending=False)
S["n_slow_decliners"] = len(slow)
S["slow_decliners"] = slow.head(6)[["song", "artist", "days_on_chart", "rank_slope_per_day", "best_rank", "avg_rank"]].round(3).to_dict("records")

# ---------------- popularity ----------------
S["pop_rank_spearman"] = float(stats.spearmanr(d.position, d.popularity)[0])
S["pop_by_band"] = d.groupby("rank_band", observed=True).popularity.agg(["mean", "median", "std"]).round(2).to_dict("index")
sp = sf.dropna(subset=["avg_popularity"])
S["pop_vs_days_spearman"] = float(stats.spearmanr(sp.avg_popularity, sp.days_on_chart)[0])
v = sf[sf.days_on_chart >= 14].dropna(subset=["avg_popularity"]).copy()
v["pop_std"] = v.song_id.map(d.groupby("song_id").popularity.std()).fillna(0)
S["pop_vs_rankvol_spearman"] = float(stats.spearmanr(v.avg_popularity, v.rank_volatility)[0])
S["popstd_vs_rankvol_spearman"] = float(stats.spearmanr(v.pop_std, v.rank_volatility)[0])
S["median_pop_std"] = float(v.pop_std.median())
S["median_rank_vol"] = float(v.rank_volatility.median())
S["avg_pop"] = float(d.popularity.mean()); S["pct_pop_ge80"] = float((d.popularity >= 80).mean() * 100)
S["pop_pct_zero_rows"] = float(q["popularity_zero_rows"] / q["clean_rows"] * 100)
mon = d.assign(m=d.date.dt.to_period("M").dt.to_timestamp()).groupby("m").popularity.mean()
S["pop_month_min"] = [mon.idxmin().strftime("%b %Y"), float(mon.min())]; S["pop_month_max"] = [mon.idxmax().strftime("%b %Y"), float(mon.max())]

# ---------------- attributes ----------------
S["explicit_share"] = float(df.is_explicit.mean() * 100)
def rowtab(col):
    return df.groupby(col).agg(rows=("position", "size"), avg_rank=("position", "mean"), avg_pop=("popularity", "mean"),
                               top10=("position", lambda x: (x <= 10).mean() * 100)).round(2).to_dict("index")
S["explicit_rows"] = {str(k): v_ for k, v_ in rowtab("is_explicit").items()}
S["album_rows"] = rowtab("album_type")
S["explicit_songs"] = {str(k): v_ for k, v_ in sf.groupby("is_explicit").agg(songs=("song_id", "size"), med_days=("days_on_chart", "median"),
                       mean_days=("days_on_chart", "mean"), avg_rank=("avg_rank", "mean")).round(2).to_dict("index").items()}
S["album_songs"] = sf.groupby("album_type").agg(songs=("song_id", "size"), med_days=("days_on_chart", "median"),
                       mean_days=("days_on_chart", "mean"), avg_rank=("avg_rank", "mean"), avg_pop=("avg_popularity", "mean")).round(2).to_dict("index")
S["explicit_by_band"] = df.groupby("rank_band", observed=True).is_explicit.mean().mul(100).round(1).to_dict()
exq = df.assign(q=df.date.dt.to_period("Q").astype(str)).groupby("q").is_explicit.mean().mul(100).round(1)
S["explicit_by_quarter"] = exq.to_dict()
S["explicit_mw"] = float(stats.mannwhitneyu(sf[sf.is_explicit].days_on_chart, sf[~sf.is_explicit].days_on_chart)[1])
S["explicit_pop_diff"] = float(d[d.is_explicit].popularity.mean() - d[~d.is_explicit].popularity.mean())
S["single_vs_album_mw"] = float(stats.mannwhitneyu(sf[sf.album_type == "single"].days_on_chart, sf[sf.album_type == "album"].days_on_chart)[1])
S["dur_stats"] = sf.duration_min.describe().round(2).to_dict()
S["dur_pop_spearman"] = float(stats.spearmanr(d.duration_min, d.popularity)[0])
S["dur_rank_spearman"] = float(stats.spearmanr(df.duration_min, df.position)[0])
S["dur_days_spearman"] = float(stats.spearmanr(sf.duration_min, sf.days_on_chart)[0])
sf["dur_bin"] = pd.cut(sf.duration_min, [0, 2.5, 3, 3.5, 4, 5, 20], labels=["<2.5", "2.5-3", "3-3.5", "3.5-4", "4-5", "5+"])
S["dur_bins"] = sf.groupby("dur_bin", observed=True).agg(songs=("song_id", "size"), med_days=("days_on_chart", "median"),
                avg_rank=("avg_rank", "mean"), avg_pop=("avg_popularity", "mean")).round(2).to_dict("index")
S["tracks_days_spearman"] = float(stats.spearmanr(sf.total_tracks, sf.days_on_chart)[0])
S["tracks_rank_spearman"] = float(stats.spearmanr(sf.total_tracks, sf.avg_rank)[0])
sf["tr_bin"] = pd.cut(sf.total_tracks, [0, 1, 3, 10, 15, 20, 200], labels=["1", "2-3", "4-10", "11-15", "16-20", "21+"])
S["tracks_bins"] = sf.groupby("tr_bin", observed=True).agg(songs=("song_id", "size"), med_days=("days_on_chart", "median"),
                avg_rank=("avg_rank", "mean"), avg_pop=("avg_popularity", "mean")).round(2).to_dict("index")
S["single_share_songs"] = float((sf.album_type == "single").mean() * 100)
S["single_share_slots"] = float((df.album_type == "single").mean() * 100)

# ---------------- artists ----------------
S["n_artists"] = len(af)
S["top_artists"] = af.head(10)[["primary_artist", "unique_songs", "chart_days", "appearances", "avg_rank", "dominance_index", "avg_popularity"]].round(2).to_dict("records")
S["top3_share"] = float(af.head(3).dominance_index.sum()); S["top10_share"] = float(af.head(10).dominance_index.sum())
S["artists_one_song"] = int((af.unique_songs == 1).sum())
S["top_unique_songs"] = af.sort_values("unique_songs", ascending=False).head(5)[["primary_artist", "unique_songs", "chart_days"]].to_dict("records")
S["multi_credit_rows_pct"] = float((df.artist != df.primary_artist).mean() * 100)
top5 = af.head(5).primary_artist.tolist()
ds = A.daily_artist_share(df, top5)
peak = ds.sort_values("share_pct", ascending=False).head(3)
S["artist_peak_months"] = [{"artist": r.primary_artist, "month": r.period.strftime("%b %Y"), "share": float(r.share_pct)} for r in peak.itertuples()]
S["avg_taylor_slots_when_present"] = float(af.iloc[0].appearances / af.iloc[0].chart_days)
S["rows_by_month_ts"] = {}
S["kpis"] = A.kpis(df)

# ============================ FIGURES ============================
# F1 longevity distribution
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
ax[0].hist(sf.days_on_chart, bins=np.logspace(0, np.log10(sf.days_on_chart.max() + 1), 28), color=C1, edgecolor="white")
ax[0].set_xscale("log"); ax[0].set_xlabel("Days on chart (log scale)"); ax[0].set_ylabel("Number of songs")
ax[0].set_title("Most songs are short-lived")
bins = pd.cut(sf.days_on_chart, [0, 7, 30, 99, 600], labels=["1-7", "8-30", "31-99", "100+"])
tab = pd.DataFrame({"songs": bins.value_counts(normalize=True).sort_index() * 100,
                    "slots": df.merge(sf[["song_id"]].assign(b=bins), on="song_id").b.value_counts(normalize=True).sort_index() * 100})
x = np.arange(4); ax[1].bar(x - .2, tab.songs, .4, color=C1, label="% of songs"); ax[1].bar(x + .2, tab.slots, .4, color=C2, label="% of chart slots")
ax[1].set_xticks(x); ax[1].set_xticklabels(tab.index); ax[1].set_xlabel("Days on chart"); ax[1].yaxis.set_major_formatter(PercentFormatter())
ax[1].legend(frameon=False); ax[1].set_title("A few long-runners hold half the chart")
S["longevity_bucket_table"] = tab.round(1).to_dict("index")
fig.tight_layout(); fig.savefig(FIG + "f1_longevity.png"); plt.close()

# F2 peak vs longevity
fig, ax = plt.subplots(figsize=(6.2, 3.6))
ax.scatter(sf.best_rank, sf.days_on_chart, s=14, alpha=.45, color=C1, edgecolor="none")
med = sf.groupby("best_rank").days_on_chart.median()
ax.plot(med.index, med.values, color=C2, lw=2, label="Median days at each peak rank")
ax.set_yscale("log"); ax.set_xlabel("Best rank achieved (1 = top)"); ax.set_ylabel("Days on chart (log)")
ax.set_title(f"Peak rank vs longevity (Spearman = {S['peak_vs_longevity_spearman']:.2f})"); ax.legend(frameon=False)
fig.savefig(FIG + "f2_peak_vs_longevity.png"); plt.close()

# F3 rank movement
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
mm = m.clip(-15, 15)
ax[0].hist(mm, bins=np.arange(-15.5, 16.5, 1), color=C1, edgecolor="white")
ax[0].set_xlabel("Day-over-day rank change (+ = climbed; clipped at ±15)"); ax[0].set_ylabel("Song-days"); ax[0].set_title("Most days, a song barely moves")
ax[1].bar(list(S["absmove_by_band"].keys()), list(S["absmove_by_band"].values()), color=C2)
ax[1].set_xlabel("Previous-day rank band"); ax[1].set_ylabel("Mean absolute move (places)"); ax[1].set_title("Movement grows down the chart")
fig.tight_layout(); fig.savefig(FIG + "f3_movement.png"); plt.close()

# F4 entries per day
fig, ax = plt.subplots(figsize=(9, 3.2))
ax.bar(ee.date, ee.new_entries, width=1.0, color=GREY)
ax.plot(ee.date, ee.new_entries.rolling(14, min_periods=3).mean(), color=C1, lw=2, label="14-day average")
ax.set_ylabel("New entries per day"); ax.set_title("Entry behaviour: steady trickle with occasional waves"); ax.legend(frameon=False)
fig.savefig(FIG + "f4_entries.png"); plt.close()

# F5 top songs by days
t = sf.sort_values("days_on_chart", ascending=False).head(12).iloc[::-1]
fig, ax = plt.subplots(figsize=(7.2, 4))
lab = [f"{s[:34]} - {a[:20]}" for s, a in zip(t.song, t.artist)]
ax.barh(lab, t.days_on_chart, color=C1)
for i, (dd, ar) in enumerate(zip(t.days_on_chart, t.avg_rank)):
    ax.text(dd + 4, i, f"{dd}d (avg rank {ar:.0f})", va="center", fontsize=8)
ax.set_xlim(0, t.days_on_chart.max() * 1.28); ax.set_xlabel("Days on chart"); ax.set_title("Songs with the longest playlist presence")
fig.savefig(FIG + "f5_top_songs.png"); plt.close()

# F6 artist dominance
t = af.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(7, 4.2))
ax.barh(t.primary_artist, t.dominance_index, color=C1)
for i, (a, u) in enumerate(zip(t.dominance_index, t.unique_songs)): ax.text(a + .08, i, f"{a:.1f}%  ({u} songs)", va="center", fontsize=8)
ax.set_xlim(0, t.dominance_index.max() * 1.3); ax.set_xlabel("Artist Dominance Index (% of all chart slots)"); ax.set_title("Artist dominance leaderboard")
fig.savefig(FIG + "f6_artists.png"); plt.close()

# F7 monthly share top5
ds2 = A.daily_artist_share(df, top5)
pv = ds2.pivot(index="period", columns="primary_artist", values="share_pct").fillna(0)[top5]
pv = pv.iloc[1:-1] if len(pv) > 2 else pv  # drop partial first/last months
fig, ax = plt.subplots(figsize=(9, 3.6))
for a, c in zip(top5, [C1, C2, "#27AE60", "#8E44AD", "#C0392B"]): ax.plot(pv.index, pv[a], marker="o", ms=3, lw=1.8, label=a, color=c)
ax.yaxis.set_major_formatter(PercentFormatter()); ax.set_ylabel("Share of monthly chart slots"); ax.legend(ncol=5, frameon=False, loc="upper center", bbox_to_anchor=(.5, -.12))
ax.set_title("Artist dominance over time (top 5 artists, full months)")
fig.savefig(FIG + "f7_artist_trend.png"); plt.close()

# F8 popularity vs rank
fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
dd_ = d[d.popularity >= 50]
hb = ax[0].hexbin(dd_.position, dd_.popularity, gridsize=(25, 20), cmap="Blues", mincnt=1, bins="log")
g = d.groupby("position").popularity.mean(); ax[0].plot(g.index, g.values, color=C2, lw=2, label="Mean popularity")
ax[0].invert_xaxis(); ax[0].set_xlabel("Playlist position (left = #50, right = #1)"); ax[0].set_ylabel("Popularity score"); ax[0].legend(frameon=False, loc="lower left")
ax[0].set_title(f"Popularity vs rank (rho = {S['pop_rank_spearman']:.2f})")
data = [d[d.rank_band == b].popularity for b in ["Top 10", "Top 11-20", "Top 21-50"]]
bp = ax[1].boxplot(data, labels=["Top 10", "Top 11-20", "Top 21-50"], patch_artist=True, showfliers=False)
for p in bp["boxes"]: p.set_facecolor("#AED6F1")
for med_ in bp["medians"]: med_.set_color(C2); med_.set_linewidth(2)
ax[1].set_ylabel("Popularity score"); ax[1].set_title("Popularity distribution by rank band")
fig.tight_layout(); fig.savefig(FIG + "f8_pop_rank.png"); plt.close()

# F9 stability
fig, ax = plt.subplots(figsize=(6.2, 3.8))
sc = ax.scatter(v.pop_std, v.rank_volatility, s=np.clip(v.days_on_chart, 14, 300) / 4, alpha=.5, color=C1, edgecolor="none")
ax.set_xlabel("Popularity std. dev. within song"); ax.set_ylabel("Rank volatility index (std. dev. of rank)")
ax.set_title(f"Popularity stability vs chart volatility (rho = {S['popstd_vs_rankvol_spearman']:.2f})")
fig.savefig(FIG + "f9_stability.png"); plt.close()

# F10 explicit
fig, ax = plt.subplots(1, 2, figsize=(9, 3.3))
ax[0].bar(exq.index, exq.values, color=C1); ax[0].axhline(S["explicit_share"], color=C2, ls="--", label=f"Overall {S['explicit_share']:.0f}%")
ax[0].yaxis.set_major_formatter(PercentFormatter()); ax[0].set_title("Explicit share of chart slots by quarter"); ax[0].legend(frameon=False); ax[0].tick_params(axis="x", labelsize=8)
cmp_ = pd.DataFrame(S["explicit_rows"]).T
ax[1].bar(["Non-explicit", "Explicit"], [cmp_.loc["False", "top10"], cmp_.loc["True", "top10"]], color=[GREY, C1])
ax[1].yaxis.set_major_formatter(PercentFormatter()); ax[1].set_title("Share of slots in Top 10"); ax[1].set_ylim(0, 30)
for i, val in enumerate([cmp_.loc["False", "top10"], cmp_.loc["True", "top10"]]): ax[1].text(i, val + .6, f"{val:.1f}%", ha="center")
fig.tight_layout(); fig.savefig(FIG + "f10_explicit.png"); plt.close()

# F11 album type
alb = pd.DataFrame(S["album_songs"]).T.loc[["single", "album"]]
albr = pd.DataFrame(S["album_rows"]).T.loc[["single", "album"]]
fig, ax = plt.subplots(1, 3, figsize=(9, 3.2))
ax[0].bar(["Single", "Album"], albr.avg_pop, color=[C2, C1]); ax[0].set_ylim(80, 95); ax[0].set_title("Avg popularity (per slot)")
ax[1].bar(["Single", "Album"], albr.top10, color=[C2, C1]); ax[1].set_title("% of slots in Top 10"); ax[1].yaxis.set_major_formatter(PercentFormatter())
ax[2].bar(["Single", "Album"], alb.med_days, color=[C2, C1]); ax[2].set_title("Median days on chart (per song)")
for a_ in ax:
    for p in a_.patches: a_.text(p.get_x() + p.get_width() / 2, p.get_height(), f"{p.get_height():.1f}", ha="center", va="bottom", fontsize=8)
fig.tight_layout(); fig.savefig(FIG + "f11_album_type.png"); plt.close()

# F12 duration & album size
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
db = pd.DataFrame(S["dur_bins"]).T; tb = pd.DataFrame(S["tracks_bins"]).T
ax[0].bar(db.index, db.med_days.astype(float), color=C1); ax[0].set_xlabel("Song duration (minutes)"); ax[0].set_ylabel("Median days on chart"); ax[0].set_title("Duration barely changes longevity")
ax[1].bar(tb.index, tb.med_days.astype(float), color=C2); ax[1].set_xlabel("Tracks on the release"); ax[1].set_title("Smaller releases last longer")
fig.tight_layout(); fig.savefig(FIG + "f12_duration_tracks.png"); plt.close()

json.dump(S, open("stats.json", "w"), indent=1, default=str)
print("done", len(S))
