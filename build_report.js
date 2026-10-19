// Builds the Word research report and one-page executive summary from stats.json + figures/
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, Header, Footer, AlignmentType,
  LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber, PageBreak, TabStopType, TabStopPosition,
} = require("docx");

const S = JSON.parse(fs.readFileSync("stats.json", "utf8"));
const Q = S.quality, K = S.kpis;
const NAVY = "1B4F72", ORANGE = "E67E22", LIGHT = "EAF2F8", GREYTXT = "566573";
const W = 9026; // A4 with 1" margins (DXA)
const n = (x, d = 1) => Number(x).toFixed(d);
const int = (x) => Number(x).toLocaleString("en-US");
const pct = (x, d = 1) => `${Number(x).toFixed(d)}%`;

// ---------- helpers ----------
const run = (t, o = {}) => new TextRun({ text: t, ...o });
function P(parts, o = {}) {
  const kids = (Array.isArray(parts) ? parts : [parts]).map((p) => (typeof p === "string" ? run(p) : p));
  return new Paragraph({ spacing: { after: 120, line: 276 }, children: kids, ...o });
}
const B = (t) => run(t, { bold: true });
const I = (t) => run(t, { italics: true });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [run(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [run(t)] });
const bullet = (parts) => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 70, line: 270 },
  children: (Array.isArray(parts) ? parts : [parts]).map((p) => (typeof p === "string" ? run(p) : p)) });
const numbered = (parts, ref = "num") => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 90, line: 270 },
  children: (Array.isArray(parts) ? parts : [parts]).map((p) => (typeof p === "string" ? run(p) : p)) });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

function png(path) { const b = fs.readFileSync(path); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), data: b }; }
let figNo = 0;
function figure(file, caption, widthPx = 600) {
  const im = png("figures/" + file);
  figNo += 1;
  const h = Math.round((widthPx * im.h) / im.w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: im.data, transformation: { width: widthPx, height: h },
        altText: { title: `Figure ${figNo}`, description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [run(`Figure ${figNo}. `, { bold: true, size: 18, color: GREYTXT }), run(caption, { size: 18, color: GREYTXT, italics: true })] }),
  ];
}

const _unused = 0;
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFC9CA" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(headers, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (txt, w, head, i) =>
    new TableCell({
      width: { size: w, type: WidthType.DXA }, borders,
      shading: head ? { fill: NAVY, type: ShadingType.CLEAR, color: "auto" } : (opts.zebra && opts._r % 2 ? { fill: "F4F6F7", type: ShadingType.CLEAR, color: "auto" } : undefined),
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [new Paragraph({ alignment: i > 0 && opts.numeric !== false && !(opts.leftCols || []).includes(i) ? AlignmentType.RIGHT : AlignmentType.LEFT,
        children: [run(String(txt), { size: 18, bold: head, color: head ? "FFFFFF" : undefined })] })],
    });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, i) => cell(h, widths[i], true, i)) }),
      ...rows.map((r, ri) => { opts._r = ri; return new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, widths[i], false, i)) }); }),
    ],
  });
}
const caption = (t) => new Paragraph({ spacing: { before: 60, after: 200 }, children: [run(t, { size: 17, italics: true, color: GREYTXT })] });
const tcap = (t) => new Paragraph({ spacing: { before: 160, after: 80 }, keepNext: true, children: [run(t, { bold: true, size: 19, color: NAVY })] });

// ---------- derived values ----------
const ex = S.explicit_rows, exs = S.explicit_songs, al = S.album_rows, als = S.album_songs, band = S.pop_by_band;
const dayRange = `${new Date(Q.date_min).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })} to ${new Date(Q.date_max).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}`;
const pctOneSongArtists = (S.artists_one_song / S.n_artists) * 100;
const ts = S.top_artists[0], zb = S.top_artists[1], mw = S.top_artists[2];

const findings = [
  [B("Chart life is short for most songs, and concentrated in a few. "), `The median song stays ${n(S.days_dist["50%"], 0)} days and ${pct(S.share_songs_le7, 0)} are gone within a week, yet the ${S.n_ge100} songs that last 100+ days (${pct(S.share_songs_ge100)} of songs) fill ${pct(S.share_slots_from_ge100, 0)} of all chart slots.`],
  [B("Peak rank is the clearest signal of staying power. "), `Songs that reached #1 (${S.n1_songs} of them) lasted a median ${n(S.n1_median_days)} days versus ${n(S.non_n1_median_days, 0)} for the rest (Spearman rho = ${n(S.peak_vs_longevity_spearman, 2)} between best rank and days on chart).`],
  [B("The top of the chart is stable; the bottom churns. "), `Songs ranked 1-5 move ${n(S.absmove_by_band["1-5"])} place per day on average, against ${n(S.absmove_by_band["21-35"])} in ranks 21-35. ${pct(S.pct_exit_from_lower25, 0)} of songs leave from the lower half, only ${pct(S.pct_exit_from_top10, 0)} from the Top 10.`],
  [B("A few artists own a large share of the chart. "), `The top 3 artists hold ${pct(S.top3_share)} of slots and the top 10 hold ${pct(S.top10_share)}, while ${pct(pctOneSongArtists, 0)} of artists placed a single song. Dominance moves in waves tied to releases.`],
  [B("Singles outperform album tracks. "), `Singles are ${pct(S.single_share_songs)} of songs but ${pct(S.single_share_slots)} of slots, reach the Top 10 in ${pct(al.single.top10)} of their slots (albums: ${pct(al.album.top10)}) and last a median ${n(als.single.med_days, 0)} days versus ${n(als.album.med_days, 0)}.`],
  [B("Explicit content and song length are not levers. "), `Explicit and clean songs sit within one point of each other on Top-10 share (${pct(ex["True"].top10)} vs ${pct(ex["False"].top10)}), and duration shows essentially no relationship with rank (rho = ${n(S.dur_rank_spearman, 2)}) or popularity (rho = ${n(S.dur_pop_spearman, 2)}).`],
];
const recs = [
  [B("Judge a release by its first two weeks, then back it. "), `Half of all songs vanish within a week, while fast risers show momentum quickly (e.g. ${S.fast_risers.filter(r=>!/Monster|Wonderful|Holly/.test(r.song))[0].song} went from #${S.fast_risers.filter(r=>!/Monster|Wonderful|Holly/.test(r.song))[0].entry_rank} to #${n(S.fast_risers.filter(r=>!/Monster|Wonderful|Holly/.test(r.song))[0].rank_day_7, 0)} in seven days). Concentrate marketing spend on songs that are climbing early, because climbers that reach the Top 10 rarely leave from there.`],
  [B("Lead with singles; use albums to feed the catalog. "), `Single releases give the best Top-10 conversion and longevity. Album tracks still matter for artist share, but they dilute attention across many songs.`],
  [B("Plan release windows around turnover waves. "), `Large entry days (${S.big_turnover_days.map(d => `${d.date}: ${d.entries} new songs`).join("; ")}) are when the chart reshuffles. Releasing into those windows means competing for the same slots; releasing in quieter weeks (${S.days_entries_le3} days had three or fewer new entries) gives a new song a clearer path.`],
  [B("Treat seasonal catalog as a recurring asset. "), `Holiday and Halloween songs were among the fastest risers (Monster Mash climbed 44 to 2 in a week). Catalog owners can plan annual re-promotion.`],
  [B("Do not engineer songs for length or explicit flags. "), `Neither shows a meaningful relationship with chart performance in this data, so content decisions should rest on other factors.`],
  [B("Use popularity as a long-run signal, with days-on-chart and volatility beside it. "), `Scores cluster high (${pct(S.pct_pop_ge80, 0)} of slots are 80 or above), so they separate rank bands only modestly (rho = ${n(S.pop_rank_spearman, 2)}), but a song's average popularity tracks its longevity strongly (rho = ${n(S.pop_vs_days_spearman, 2)}).`],
];

// ======================================================================
// REPORT
// ======================================================================
const c = [];
// ---- cover ----
c.push(new Paragraph({ spacing: { before: 2200, after: 120 }, children: [run("UNIFIED MENTOR  |  DATA ANALYTICS PROJECT", { size: 20, color: ORANGE, bold: true, characterSpacing: 40 })] }));
c.push(new Paragraph({ spacing: { after: 160 }, children: [run("United States Top 50 Playlist Performance and Song Popularity Trend Analysis", { size: 52, bold: true, color: NAVY })] }));
c.push(new Paragraph({ spacing: { after: 600 }, border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: ORANGE, space: 8 } }, children: [run("Research paper: exploratory data analysis, insights and recommendations", { size: 26, color: GREYTXT })] }));
c.push(P([B("Prepared for: "), "Atlantic Recording Corporation"], { spacing: { after: 60 } }));
c.push(P([B("Data analysed: "), `Daily US Top 50 playlist snapshots, ${dayRange}`], { spacing: { after: 60 } }));
c.push(P([B("Scope: "), `${int(Q.clean_rows)} chart slots, ${int(Q.unique_songs)} songs, ${int(Q.unique_primary_artists)} primary artists`], { spacing: { after: 60 } }));
c.push(P([B("Date: "), "October 2026"], { spacing: { after: 60 } }));
c.push(new Paragraph({ spacing: { before: 1200 }, children: [run("Companion deliverables: Streamlit dashboard (app.py) and one-page executive summary.", { size: 19, italics: true, color: GREYTXT })] }));
c.push(pageBreak());

// ---- contents ----
c.push(H1("Contents"));
["Executive summary", "1. Background and objectives", "2. Data and methodology", "3. Playlist ranking analysis", "4. Song-level performance",
 "5. Artist performance", "6. Popularity score analytics", "7. Content attribute analysis", "8. Key performance indicators",
 "9. Insights and recommendations", "10. Limitations and next steps", "Appendix: dashboard guide and reproducibility"].forEach((t) => c.push(P(t, { spacing: { after: 70 } })));
c.push(pageBreak());

// ---- exec summary ----
c.push(H1("Executive summary"));
c.push(P(`This study analyses ${Q.snapshot_days} daily snapshots of the US Top 50 playlist (${dayRange}) to explain how songs rise, persist and fade, which artists dominate, and whether content attributes such as explicit flags, release type and duration relate to chart success. It is a historical analysis; it does not forecast or recommend songs.`));
c.push(H2("Key findings"));
findings.forEach((f) => c.push(bullet(f)));
c.push(H2("Recommendations"));
recs.slice(0, 4).forEach((r) => c.push(numbered(r)));
c.push(P([I("The full set of recommendations and the evidence behind each is in Section 9. Two data caveats (a one-year date offset that needs confirming, and a doubled snapshot on 1 March 2025) are explained in Section 2.")], { spacing: { before: 120 } }));
c.push(pageBreak());

// ---- 1 background ----
c.push(H1("1. Background and objectives"));
c.push(P("Music consumption in the streaming era changes daily. Playlist rankings influence streams and revenue, and an artist's visibility depends on how long songs stay on a chart, not only on the peak they reach. For a record label such as Atlantic Recording Corporation, understanding playlist behaviour over time informs artist promotion, release timing, marketing spend and catalog strategy."));
c.push(P("Daily Top 50 data is widely available, but stakeholders often lack a structured view of four things: how stable or volatile rankings are, how long songs stay relevant, which artists dominate and keep reappearing, and how song attributes relate to popularity. Without that structure, playlist insight stays anecdotal."));
c.push(H2("Objectives"));
["Measure ranking stability and volatility using consistent, reproducible metrics.", "Quantify song longevity and compare peak rank with persistence.",
 "Identify artist dominance and repeat-appearance patterns.", "Test how popularity score relates to rank and to chart volatility.",
 "Compare content attributes (explicit flag, single vs album, duration, album size) on performance.",
 "Deliver the findings as a research paper, an interactive Streamlit dashboard and an executive summary."].forEach((t) => c.push(bullet(t)));

// ---- 2 data & method ----
c.push(H1("2. Data and methodology"));
c.push(H2("2.1 Dataset"));
c.push(P(`The file contains one row per playlist position per day. After cleaning it holds ${int(Q.clean_rows)} rows covering ${Q.snapshot_days} daily snapshots.`));
c.push(tcap("Table 1. Dataset fields"));
c.push(table(["Field", "Description"], [
  ["date", "Date of playlist snapshot (dd-mm-yyyy in the file)"], ["position", "Playlist rank, 1 to 50"], ["song", "Song title"], ["artist", "Credited artist(s)"],
  ["popularity", "Popularity score (0-100) from the Atlantic API"], ["duration_ms", "Song duration in milliseconds"], ["album_type", "single, album or compilation"],
  ["total_tracks", "Number of tracks on the release"], ["is_explicit", "Explicit content flag"], ["album_cover_url", "Album artwork URL"],
], [2200, 6826], { numeric: false, zebra: true }));
c.push(H2("2.2 Validation and cleaning"));
c.push(P("Every step in the brief was applied before analysis. The results are summarised below."));
c.push(tcap("Table 2. Data validation results"));
c.push(table(["Check", "Result", "Treatment"], [
  ["Rank range 1-50", `${Q.rank_out_of_range} violations`, "None needed"],
  ["Rows per snapshot", `${Q.snapshot_days - 1} days with 50 rows; 1 March 2025 has 100`, "Kept the first block of 50, dropped the second"],
  ["Duplicate rows", `${Q.exact_duplicate_rows} exact duplicates (all within the doubled day)`, "Removed with the second block"],
  ["Missing calendar days", `${Q.missing_days.length} of ${Q.calendar_days} days absent (${Q.missing_days.join(", ")})`, "Left as gaps; movement is measured only across consecutive days"],
  ["Popularity = 0", `${Q.popularity_zero_rows} rows (${pct(S.pop_pct_zero_rows)})`, "Treated as missing API values and excluded from popularity statistics"],
  ["Artist formatting", `${Q.artist_case_variants_merged} case variant merged (Charli XCX / Charli xcx); whitespace normalised`, "Canonical spelling = most frequent form"],
  ["Song identity", `${int(Q.unique_songs)} unique song + artist pairs`, "Same title by different artists treated as different songs"],
], [2100, 3700, 3226], { numeric: false, zebra: true }));
c.push(caption("The doubled 1 March 2025 snapshot contained two different 50-song lists. Neither matched its neighbouring days clearly enough to call one stale, so the first block was kept. The effect is one day out of 555."));
c.push(P([B("Artist standardisation. "), `Credits are joined with " & " (for example "Post Malone & Morgan Wallen"). The analysis uses the first-listed artist as the primary artist, with exceptions for acts whose names contain the separator (such as Earth, Wind & Fire). ${pct(S.multi_credit_rows_pct)} of chart slots carry more than one credit. The dashboard can switch between primary-artist and full-credit views.`]));
c.push(H2("2.3 Date check"));
c.push(P([B("Please confirm the calendar dates with the data provider. "), "Several well-known release events appear in this file one year later than their real-world dates. For example, Tyler, The Creator's album CHROMAKOPIA (released late October 2024) fills the top of the 31 October 2025 snapshot, and Lady Gaga and Bruno Mars's \"Die With A Smile\" shows 103 days on chart, which matches its release in August 2024 running to the end of November 2024 rather than 2025. A constant one-year offset would not change any ranking, longevity, artist or attribute result in this paper, because those depend on order and duration rather than calendar year. It would change the calendar labels in month-level charts and in the event references below."]));
c.push(P("This paper reports dates exactly as supplied. If the offset is confirmed, set DATE_SHIFT_YEARS = -1 in analytics.py and re-run run_analysis.py; every figure and number will be regenerated."));
c.push(H2("2.4 Feature engineering"));
c.push(tcap("Table 3. Derived metrics"));
c.push(table(["Metric", "Definition"], [
  ["Days on Chart", "Number of distinct snapshot days a song appears (per song + artist)"], ["Average Rank / Best Rank", "Mean and minimum position over the song's chart life"],
  ["Rank Volatility Index", "Standard deviation of the song's daily rank"], ["Popularity Trend Score", "7-day rolling mean of a song's popularity (per song, ordered by date)"],
  ["Duration (minutes)", "duration_ms divided by 60,000"], ["Artist Dominance Index", "An artist's chart slots as a percentage of all chart slots in the selected period"],
  ["Day-over-day move", "Previous rank minus current rank, only when both days are consecutive (positive = climbed)"], ["Explicit Content Share", "Share of chart slots held by explicit songs"],
], [2600, 6426], { numeric: false, zebra: true }));
c.push(P([B("Statistics used. "), "Rank, longevity and popularity are not normally distributed, so relationships are measured with Spearman rank correlation. Group differences in longevity use the Mann-Whitney U test. All results are descriptive and observational: they describe what happened on the chart and do not prove cause."], { spacing: { before: 160 } }));

// ---- 3 ranking ----
c.push(H1("3. Playlist ranking analysis"));
c.push(H2("3.1 Rank movement"));
c.push(P(`Day-to-day movement is small. The median song moves ${n(S.median_abs_move, 0)} place between consecutive days, ${pct(S.pct_no_change, 0)} of song-days show no change at all, and ${pct(S.pct_move_le3, 0)} move by three places or fewer. Only ${pct(S.pct_move_ge10)} of movements are ten places or more.`));
c.push(...figure("f3_movement.png", "Distribution of day-over-day rank change (left) and mean absolute movement by previous-day rank band (right)."));
c.push(P(`Movement is not uniform. Songs in ranks 1-5 shift an average of ${n(S.absmove_by_band["1-5"])} place per day, rising to ${n(S.absmove_by_band["11-20"])} in ranks 11-20 and ${n(S.absmove_by_band["21-35"])} in ranks 21-35 before levelling off. A song that has reached the top of the chart tends to hold its place, while the middle and lower positions are where reshuffling happens.`));
c.push(H2("3.2 Entry and exit behaviour"));
c.push(P(`On an average day ${n(S.avg_new_entries)} songs enter the chart (median ${n(S.median_new_entries, 0)}). ${S.days_entries_le3} days saw three or fewer new songs, while ${S.days_entries_ge10} days saw ten or more. The largest single-day turnover was ${S.big_turnover_days[0].date}, when ${S.big_turnover_days[0].entries} of 50 songs were new, followed by ${S.big_turnover_days[1].date} (${S.big_turnover_days[1].entries}) and ${S.big_turnover_days[2].date} (${S.big_turnover_days[2].entries}).`));
c.push(...figure("f4_entries.png", "New entries per day with a 14-day moving average. Spikes are album-release or seasonal playlist changes."));
c.push(P(`Songs most often debut in the middle of the chart: the median entry rank is ${n(S.entry_rank_median, 0)}, ${pct(S.pct_enter_top10, 0)} debut in the Top 10, and ${pct(S.pct_enter_lower25, 0)} debut in the lower half. Exit tells a sharper story: ${pct(S.pct_exit_from_lower25, 0)} of songs make their last appearance in the lower half and just ${pct(S.pct_exit_from_top10)} leave from the Top 10. Songs drift down before they leave; they rarely fall off from the top.`));
c.push(H2("3.3 Fast risers and slow decliners"));
c.push(P("Fast risers are songs with the biggest climb in their first seven days on the chart. Slow decliners are long-running songs (100+ days) that lose rank gradually, measured as the slope of rank against time."));
c.push(tcap("Table 4. Fastest risers (rank on entry vs rank on day 7)"));
c.push(table(["Song", "Artist", "Entry rank", "Day-7 rank", "Places gained"],
  S.fast_risers.slice(0, 6).map((r) => [r.song.slice(0, 40), r.artist.slice(0, 28), r.entry_rank, int(r.rank_day_7), r.climb]), [3000, 2500, 1100, 1200, 1226], { zebra: true, leftCols: [1] }));
c.push(P(`Several of the fastest risers are seasonal catalog songs (Halloween and Christmas titles re-entering at the bottom and reaching the Top 10 within a week), alongside genuinely new hits. ${S.n_slow_decliners} songs ran 100+ days while losing under 0.1 places per day. "Something in the Orange" (Zach Bryan) lost only ${n(S.slow_decliners[0].rank_slope_per_day, 3)} places a day over ${S.slow_decliners[0].days_on_chart} days, roughly one place every 40 days.`, { spacing: { before: 160 } }));

// ---- 4 song-level ----
c.push(H1("4. Song-level performance"));
c.push(H2("4.1 Longevity"));
c.push(P(`Chart presence is highly skewed. The average song lasts ${n(S.days_dist.mean)} days but the median is ${n(S.days_dist["50%"], 0)}; ${pct(S.share_songs_le7, 0)} of songs last a week or less. At the other end, ${S.n_ge100} songs lasted 100 days or more, and together they occupy ${pct(S.share_slots_from_ge100, 0)} of all chart slots.`));
c.push(...figure("f1_longevity.png", "Left: distribution of days on chart (log scale). Right: share of songs versus share of chart slots by longevity band."));
c.push(tcap("Table 5. Songs with the longest playlist presence"));
c.push(table(["Song", "Artist", "Days", "Avg rank", "Best", "Volatility"],
  S.top_songs.map((r) => [r.song.slice(0, 38), r.artist.slice(0, 22), r.days_on_chart, n(r.avg_rank), r.best_rank, n(r.rank_volatility)]), [3000, 2200, 800, 1000, 800, 1226], { zebra: true, leftCols: [1] }));
c.push(...figure("f5_top_songs.png", "Twelve songs with the longest playlist presence, annotated with average rank.", 520));
c.push(H2("4.2 Peak rank versus longevity"));
c.push(P(`Reaching a high peak goes with staying longer. The Spearman correlation between best rank and days on chart is ${n(S.peak_vs_longevity_spearman, 2)} (a better peak, meaning a lower rank number, goes with more days). The ${S.n1_songs} songs that hit #1 lasted a median ${n(S.n1_median_days)} days, against ${n(S.non_n1_median_days, 0)} for songs that never did. Songs whose best rank was inside the Top 10 lasted a median ${n(S.top10_peak_median_days, 0)} days; the ${S.n_never_top10} songs that never entered the Top 10 lasted ${n(S.never_top10_median_days, 0)}.`));
c.push(...figure("f2_peak_vs_longevity.png", "Best rank achieved versus days on chart (log scale). Each dot is a song; the line is the median at each peak rank.", 470));
c.push(P(`The relationship is not deterministic. Some songs with modest peaks (for example "Thinkin' Bout Me", best rank 21) lasted over 300 days by sitting steadily in the lower-middle of the chart. Longevity is built either by a strong peak or by consistent mid-chart presence.`));
c.push(H2("4.3 Popularity and volatility at song level"));
c.push(P(`Among songs with at least 100 days on chart, the median rank volatility index is ${n(S.vol_median_long)}. The most stable were songs parked near the top: ${S.most_stable.slice(0, 3).map((r) => `"${r.song}" (${n(r.rank_volatility)})`).join(", ")}. The most volatile were songs with sharp peaks and slow decays: ${S.most_volatile.slice(0, 3).map((r) => `"${r.song}" (${n(r.rank_volatility)})`).join(", ")}. The highest average popularity among songs with 30+ days belonged to "${S.top_pop_songs[0].song}" (${n(S.top_pop_songs[0].avg_popularity)}) and "${S.top_pop_songs[1].song}" (${n(S.top_pop_songs[1].avg_popularity)}).`));

// ---- 5 artists ----
c.push(H1("5. Artist performance"));
c.push(P(`${int(S.n_artists)} primary artists appear in the data. ${S.artists_one_song} of them (${pct(pctOneSongArtists, 0)}) placed exactly one song. At the top, ${ts.primary_artist} accounts for ${pct(ts.dominance_index)} of all chart slots across ${ts.unique_songs} different songs, followed by ${zb.primary_artist} (${pct(zb.dominance_index)}) and ${mw.primary_artist} (${pct(mw.dominance_index)}). The top 3 artists together hold ${pct(S.top3_share)} of the chart and the top 10 hold ${pct(S.top10_share)}.`));
c.push(...figure("f6_artists.png", "Artist Dominance Index: share of all chart slots by primary artist, with number of unique songs charted.", 500));
c.push(tcap("Table 6. Artist leaderboard (top 10)"));
c.push(table(["Artist", "Unique songs", "Days on chart", "Slots", "Avg rank", "Dominance"],
  S.top_artists.map((r) => [r.primary_artist, r.unique_songs, r.chart_days, int(r.appearances), n(r.avg_rank), pct(r.dominance_index)]), [2800, 1200, 1300, 1000, 1100, 1626], { zebra: true }));
c.push(H2("Different routes to dominance"));
c.push(P(`The leaderboard hides two distinct patterns. ${ts.primary_artist} dominates through breadth: ${ts.unique_songs} songs appear but each spends few days (about ${n(ts.appearances / ts.unique_songs, 0)} slots per song), and presence is concentrated in a release window. ${mw.primary_artist} takes ${pct(mw.dominance_index)} of slots with only ${mw.unique_songs} songs, so each song is a long-runner. ${zb.primary_artist} combines both: ${zb.unique_songs} songs and presence on ${zb.chart_days} of ${Q.snapshot_days} days, the highest of any artist.`));
c.push(...figure("f7_artist_trend.png", "Monthly share of chart slots for the five most frequent artists (full months only; dates as supplied in the file).", 600));
c.push(P(`Dominance is episodic. The highest monthly shares were ${S.artist_peak_months.slice(0, 3).map((m) => `${m.artist} in ${m.month} (${pct(m.share, 0)})`).join(", ")}, each tied to a release wave, and each later fading as other artists rose. A strong artist presence therefore depends on the release calendar, not just on a long-term audience.`));

// ---- 6 popularity ----
c.push(H1("6. Popularity score analytics"));
c.push(H2("6.1 Popularity versus rank"));
c.push(P(`Popularity scores in the Top 50 are high and compressed: the average is ${n(S.avg_pop)} and ${pct(S.pct_pop_ge80, 0)} of slots score 80 or more. The relationship with rank is negative but modest (Spearman rho = ${n(S.pop_rank_spearman, 2)}), meaning higher-ranked positions tend to carry higher popularity, with lots of overlap.`));
c.push(...figure("f8_pop_rank.png", "Popularity versus playlist position (left, with mean popularity per position) and popularity by rank band (right).", 600));
c.push(tcap("Table 7. Popularity by rank band"));
c.push(table(["Rank band", "Mean", "Median", "Std. dev."], ["Top 10", "Top 11-20", "Top 21-50"].map((b) => [b, n(band[b].mean, 2), n(band[b].median, 0), n(band[b].std, 2)]), [3000, 2000, 2000, 2026], { zebra: true }));
c.push(P(`The Top 10 averages ${n(band["Top 10"].mean)} against ${n(band["Top 21-50"].mean)} for ranks 21-50, a gap of about ${n(band["Top 10"].mean - band["Top 21-50"].mean)} points. The Top 10 also has the widest spread (std. dev. ${n(band["Top 10"].std)}), because a handful of weeks with lower popularity scores sit inside it.`, { spacing: { before: 160 } }));
c.push(H2("6.2 Popularity as a longevity signal"));
c.push(P(`At song level, average popularity is a strong companion to longevity: the correlation between a song's mean popularity and its days on chart is ${n(S.pop_vs_days_spearman, 2)}. Popularity is therefore more informative about how long a song lasts than about its rank on any single day.`));
c.push(H2("6.3 Popularity stability versus chart volatility"));
c.push(P(`For songs with at least 14 days on chart, the median within-song popularity standard deviation is ${n(S.median_pop_std)} points, small next to the median rank volatility of ${n(S.median_rank_vol)} places. The two are modestly linked (rho = ${n(S.popstd_vs_rankvol_spearman, 2)}): songs whose popularity swings more also tend to swing more in rank. A song's average popularity level is unrelated to its rank volatility (rho = ${n(S.pop_vs_rankvol_spearman, 2)}), so popular songs are not necessarily more stable.`));
c.push(...figure("f9_stability.png", "Within-song popularity standard deviation versus rank volatility index (bubble size = days on chart).", 470));

// ---- 7 content ----
c.push(H1("7. Content attribute analysis"));
c.push(H2("7.1 Explicit versus non-explicit"));
c.push(P(`Explicit songs account for ${pct(S.explicit_share)} of all chart slots, with no large difference by rank band (Top 10: ${pct(S.explicit_by_band["Top 10"])}, ranks 21-50: ${pct(S.explicit_by_band["Top 21-50"])}). Explicit songs average rank ${n(ex["True"].avg_rank)} versus ${n(ex["False"].avg_rank)}, and popularity ${n(ex["True"].avg_pop)} versus ${n(ex["False"].avg_pop)}.`));
c.push(tcap("Table 8. Explicit versus non-explicit"));
c.push(table(["Group", "Songs", "Slots", "Avg rank", "Avg popularity", "Top-10 share", "Median days"],
  [["Explicit", exs["True"].songs, int(ex["True"].rows), n(ex["True"].avg_rank, 2), n(ex["True"].avg_pop, 2), pct(ex["True"].top10), n(exs["True"].med_days, 0)],
   ["Non-explicit", exs["False"].songs, int(ex["False"].rows), n(ex["False"].avg_rank, 2), n(ex["False"].avg_pop, 2), pct(ex["False"].top10), n(exs["False"].med_days, 0)]],
  [1500, 900, 1000, 1200, 1500, 1500, 1426], { zebra: true }));
c.push(...figure("f10_explicit.png", "Explicit share of chart slots by quarter (left) and Top-10 share for explicit versus non-explicit songs (right).", 600));
c.push(P(`The difference in longevity between explicit and clean songs is not statistically significant (Mann-Whitney p = ${n(S.explicit_mw, 3)}), and the popularity gap is ${n(Math.abs(S.explicit_pop_diff), 2)} points. The explicit share does vary by quarter, from ${pct(Math.min(...Object.values(S.explicit_by_quarter)), 0)} to ${pct(Math.max(...Object.values(S.explicit_by_quarter)), 0)}, which reflects which albums were on the chart rather than a performance advantage.`));
c.push(H2("7.2 Single versus album tracks"));
c.push(tcap("Table 9. Release type comparison"));
c.push(table(["Type", "Songs", "Slots", "Avg rank", "Avg popularity", "Top-10 share", "Median days"],
  ["single", "album", "compilation"].map((k) => [k[0].toUpperCase() + k.slice(1), als[k].songs, int(al[k].rows), n(al[k].avg_rank, 1), n(al[k].avg_pop, 1), pct(al[k].top10), n(als[k].med_days, 0)]),
  [1500, 900, 1000, 1200, 1500, 1500, 1426], { zebra: true }));
c.push(...figure("f11_album_type.png", "Singles versus album tracks: popularity, Top-10 share and median days on chart.", 600));
c.push(P(`Singles are the strongest performers. They reach the Top 10 in ${pct(al.single.top10)} of their slots versus ${pct(al.album.top10)} for album tracks, carry higher popularity (${n(al.single.avg_pop)} vs ${n(al.album.avg_pop)}) and last twice as long at the median (${n(als.single.med_days, 0)} vs ${n(als.album.med_days, 0)} days; Mann-Whitney p < 0.001). Compilation tracks are too rare (${als.compilation.songs} songs, ${al.compilation.rows} slots) to draw conclusions, though they rank lower on every measure.`));
c.push(P([I("Interpretation: "), "this comparison mixes marketing intent with song quality. Labels typically promote singles harder, so the gap likely reflects release strategy as well as format."]));
c.push(H2("7.3 Duration and album size"));
c.push(P(`Song length averages ${n(S.dur_stats.mean)} minutes (median ${n(S.dur_stats["50%"])}; range ${n(S.dur_stats.min)} to ${n(S.dur_stats.max)}). Duration has almost no association with popularity (rho = ${n(S.dur_pop_spearman, 2)}), rank (rho = ${n(S.dur_rank_spearman, 2)}) or longevity (rho = ${n(S.dur_days_spearman, 2)}). Songs over five minutes have a slightly better average rank but the shortest median chart life, so there is no length that reliably helps.`));
c.push(P(`Album size shows a clearer pattern. Releases with a single track last a median ${n(S.tracks_bins["1"].med_days, 0)} days, against ${n(Math.min(...["2-3","4-10","11-15"].map(k=>S.tracks_bins[k].med_days)), 0)} to ${n(Math.max(...["2-3","4-10","11-15"].map(k=>S.tracks_bins[k].med_days)), 0)} for releases with 2 to 15 tracks and ${n(S.tracks_bins["16-20"].med_days, 0)} for those with 16 to 20 (correlation of total tracks with days on chart: rho = ${n(S.tracks_days_spearman, 2)}). This is largely the singles effect again, as single-track releases are singles by definition. Large albums spread listening across many songs, which shortens each song's stay.`));
c.push(...figure("f12_duration_tracks.png", "Median days on chart by song duration (left) and by number of tracks on the release (right).", 600));

// ---- 8 KPIs ----
c.push(H1("8. Key performance indicators"));
c.push(tcap("Table 10. KPI summary for the full period"));
c.push(table(["KPI", "Value", "How to read it"], [
  ["Days on Chart (median)", n(K.median_days_on_chart, 0), `Typical song lasts a week; the longest, ${S.top_songs[0].days_on_chart} days`],
  ["Average Rank", n(K.avg_rank_overall), "Mid-chart by construction; useful for comparing songs and groups"],
  ["Rank Volatility Index", n(K.avg_rank_volatility), "Mean standard deviation of rank, songs with 7+ days"],
  ["Popularity Score Trend", n(K.avg_popularity), `Average score; range of monthly means ${n(S.pop_month_min[1])} to ${n(S.pop_month_max[1])}`],
  ["Artist Dominance Index (leader)", pct(K.top_artist_dominance_pct), `${K.top_artist}'s share of all chart slots`],
  ["Explicit Content Share", pct(K.explicit_share_pct), "Share of chart slots held by explicit songs"],
], [3000, 1500, 4526], { numeric: false, zebra: true }));

// ---- 9 insights ----
c.push(H1("9. Insights and recommendations"));
c.push(P("The recommendations below follow directly from the evidence in this report. Each describes what the historical data supports; none is a prediction."));
recs.forEach((r) => c.push(numbered(r, "num2")));

// ---- 10 limitations ----
c.push(H1("10. Limitations and next steps"));
["The data covers only the Top 50. Songs that are popular but ranked below 50 are invisible, so days on chart and entry rank are truncated at the 50-position boundary.",
 "There are no stream counts or revenue figures. Findings describe chart behaviour, not financial return, and cannot yet be tied to marketing spend.",
 "The analysis is observational. Differences between singles and album tracks, for example, include marketing intent and artist profile as well as format.",
 "The calendar dates appear to be offset by one year (Section 2.3). This does not affect ranking, longevity or attribute findings but does affect date labels, and should be confirmed.",
 "One snapshot (1 March 2025) was loaded twice with different content, four days are missing, and 189 popularity values were recorded as zero. All are handled and disclosed, but they add small uncertainty.",
 "Seasonal songs (Christmas, Halloween) re-enter every year and are treated as separate runs within a single song record; a longer window would show their yearly pattern."].forEach((t) => c.push(bullet(t)));
c.push(P([B("Suggested next steps: "), "validate the date offset; add stream and revenue data to connect rank to financial outcomes; extend the window to cover a full second year so seasonality can be separated from release cycles; and track Atlantic-owned artists as a labelled group in the dashboard."], { spacing: { before: 120 } }));

c.push(H1("11. Conclusion"));
c.push(P("US Top 50 playlist success is defined by persistence. Most songs pass through in days, while a small group of long-running songs occupies the majority of the chart. Peak rank is the best early sign of that persistence, the top of the chart is stable, and the churn happens lower down. Artist visibility moves in release-driven waves, and singles convert to Top-10 placement and longevity better than album tracks. Explicit content and song length, by contrast, make no meaningful difference. For Atlantic Recording Corporation this points to a clear strategy: back songs that climb early, lead with singles, time releases around chart turnover, and keep catalog and seasonal songs active."));

// ---- appendix ----
c.push(H1("Appendix: dashboard guide and reproducibility"));
c.push(P([B("Running the dashboard. "), "Install the requirements and run the app from the project folder:"]));
c.push(new Paragraph({ shading: { fill: "F4F6F7", type: ShadingType.CLEAR, color: "auto" }, spacing: { after: 120 }, children: [run("pip install -r requirements.txt", { font: "Consolas", size: 19 })] }));
c.push(new Paragraph({ shading: { fill: "F4F6F7", type: ShadingType.CLEAR, color: "auto" }, spacing: { after: 160 }, children: [run("streamlit run app.py", { font: "Consolas", size: 19 })] }));
c.push(tcap("Table 11. Dashboard modules"));
c.push(table(["Tab", "Contents"], [
  ["Playlist timeline", "Snapshot explorer with album art and daily movement, rank distribution of long-runners, entries and exits, fast risers and slow decliners"],
  ["Song trends", "Rank and popularity-trend charts for chosen songs, song scorecard, peak rank versus longevity"],
  ["Artist dominance", "Leaderboard (primary or full credit), dominance over time, repeat appearances"],
  ["Popularity vs rank", "Scatter with mean line, distribution by rank band, stability versus volatility"],
  ["Explicit vs non-explicit", "Performance panel, explicit share over time and by rank band"],
  ["Content attributes", "Single vs album, duration and album-size comparisons"],
  ["Data & quality", "Validation summary and filtered CSV download"],
], [2300, 6726], { numeric: false, zebra: true }));
c.push(P([B("Filters. "), "Date range, rank-range slider, album-type selection, explicit toggle, artist selection and song-title search apply to every tab."], { spacing: { before: 160 } }));
c.push(P([B("Files. "), "analytics.py (cleaning, features, KPIs), app.py (dashboard), run_analysis.py (figures and statistics for this report), build_report.js (this document)."]));

const doc = new Document({
  creator: "Analytics Team", title: "US Top 50 Playlist Performance and Song Popularity Trend Analysis",
  styles: {
    default: { document: { run: { font: "Calibri", size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Calibri", color: NAVY }, paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0, keepNext: true } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, font: "Calibri", color: ORANGE }, paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1, keepNext: true } },
    ],
  },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] },
    { reference: "num2", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, right: 1440, bottom: 1300, left: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "D5D8DC", space: 4 } },
      children: [run("US Top 50 Playlist Performance and Song Popularity Trend Analysis", { size: 16, color: GREYTXT })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run("Page ", { size: 16, color: GREYTXT }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: GREYTXT })] })] }) },
    children: c,
  }],
});

// ======================================================================
// EXECUTIVE SUMMARY (one page)
// ======================================================================
const e = [];
e.push(new Paragraph({ spacing: { after: 40 }, children: [run("EXECUTIVE SUMMARY", { size: 18, bold: true, color: ORANGE, characterSpacing: 40 })] }));
e.push(new Paragraph({ spacing: { after: 80 }, children: [run("US Top 50 Playlist Performance and Song Popularity Trends", { size: 34, bold: true, color: NAVY })] }));
e.push(new Paragraph({ spacing: { after: 140 }, border: { bottom: { style: BorderStyle.SINGLE, size: 10, color: ORANGE, space: 6 } },
  children: [run(`For Atlantic Recording Corporation  |  ${int(Q.snapshot_days)} daily snapshots, ${dayRange}`, { size: 18, color: GREYTXT })] }));
e.push(new Paragraph({ spacing: { after: 100, line: 260 }, children: [B("Purpose. "), run("To explain how songs rise, persist and fade on the US Top 50 playlist, which artists dominate, and whether song attributes relate to success, so that promotion, release timing and marketing spend can be guided by evidence.")] }));
e.push(new Paragraph({ spacing: { before: 100, after: 60 }, children: [run("What the data shows", { size: 23, bold: true, color: ORANGE })] }));
const small = (parts, ref) => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 70, line: 262 },
  children: parts.map((p) => (typeof p === "string" ? run(p, { size: 21 }) : p)) });
const boldS = (t) => run(t, { bold: true, size: 21 });
const findingsS = [
  [boldS("Short lives, concentrated presence. "), `Median chart life is ${n(S.days_dist["50%"], 0)} days; ${pct(S.share_songs_le7, 0)} of songs last a week or less, but the ${S.n_ge100} songs lasting 100+ days fill ${pct(S.share_slots_from_ge100, 0)} of all slots.`],
  [boldS("Peak rank predicts staying power. "), `Songs that hit #1 lasted a median ${n(S.n1_median_days, 0)} days versus ${n(S.non_n1_median_days, 0)} for the rest.`],
  [boldS("Stable top, churning bottom. "), `Ranks 1-5 move ${n(S.absmove_by_band["1-5"])} place a day versus ${n(S.absmove_by_band["21-35"])} in ranks 21-35; only ${pct(S.pct_exit_from_top10, 0)} of songs exit from the Top 10.`],
  [boldS("Artist concentration. "), `The top 3 artists hold ${pct(S.top3_share, 0)} of slots, the top 10 hold ${pct(S.top10_share, 0)}; ${pct(pctOneSongArtists, 0)} of artists charted a single song. Dominance comes in release-driven waves.`],
  [boldS("Singles beat album tracks. "), `${pct(al.single.top10, 0)} of single slots reach the Top 10 versus ${pct(al.album.top10, 0)} for album tracks, with twice the median chart life (${n(als.single.med_days, 0)} vs ${n(als.album.med_days, 0)} days).`],
  [boldS("Explicit flag and length do not matter. "), `Top-10 share is ${pct(ex["True"].top10)} (explicit) versus ${pct(ex["False"].top10)}; duration shows no meaningful link to rank or popularity.`],
];
findingsS.forEach((f) => e.push(small(f, "bul")));
e.push(new Paragraph({ spacing: { before: 100, after: 60 }, children: [run("Recommendations", { size: 23, bold: true, color: ORANGE })] }));
const fr0 = S.fast_risers.filter((r) => !/Monster|Wonderful|Holly/.test(r.song))[0];
[
  [boldS("Back early climbers. "), `Half of songs disappear within a week, and climbers that reach the Top 10 rarely leave from there. Judge new releases on their first two weeks and concentrate spend on songs that are rising (e.g. "${fr0.song}": #${fr0.entry_rank} to #${n(fr0.rank_day_7, 0)} in seven days).`],
  [boldS("Lead with singles. "), "They convert to Top-10 placement and longevity better; use album tracks to build artist share and catalog."],
  [boldS("Time releases around chart turnover. "), `Entry waves (${S.big_turnover_days[0].entries} new songs on ${S.big_turnover_days[0].date}) mean heavy competition for slots; quieter weeks give new songs a clearer path.`],
  [boldS("Plan seasonal catalog. "), "Holiday and Halloween songs are among the fastest risers each year."],
  [boldS("Focus elsewhere than length or explicit flags. "), "Neither shows an effect on chart performance in this data."],
].forEach((r) => e.push(small(r, "num")));
e.push(new Paragraph({ spacing: { before: 120 }, border: { top: { style: BorderStyle.SINGLE, size: 4, color: "D5D8DC", space: 6 } },
  children: [run("Caveats: the Top 50 hides songs ranked below 50; there are no stream or revenue figures; calendar dates in the source file appear offset by one year and should be confirmed with the data provider (this does not change the findings above). Full evidence is in the research paper; the Streamlit dashboard allows interactive filtering.", { size: 16, italics: true, color: GREYTXT })] }));

// numbering config for exec doc (separate Document instance)
const execDoc = new Document({
  creator: "Analytics Team", title: "Executive Summary - US Top 50 Playlist Analysis",
  styles: { default: { document: { run: { font: "Calibri", size: 20 } } } },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 440, hanging: 260 } } } }] },
    { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 440, hanging: 320 } } } }] },
  ] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 900, right: 1100, bottom: 800, left: 1100 } } }, children: e }],
});

fs.mkdirSync("report", { recursive: true });
Promise.all([
  Packer.toBuffer(doc).then((b) => fs.writeFileSync("report/US_Top50_Playlist_Research_Report.docx", b)),
  Packer.toBuffer(execDoc).then((b) => fs.writeFileSync("report/US_Top50_Executive_Summary.docx", b)),
]).then(() => console.log("written"));
