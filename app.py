import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------
# PAGE CONFIG + STYLE
# ---------------------------------------------------------
st.set_page_config(
    page_title="Approval Patterns Dashboard",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

TECH_COLORS = {
    "Gary Arnold": "#E45756",
    "Juan Mendez": "#4C78A8",
    "Matt Shawn": "#54A24B",
}

st.markdown("""
<style>
    .block-container {padding-top: 1.5rem;}
    div[data-testid="stMetric"] {
        background-color: #f8f9fb;
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 12px 16px;
    }
    div[data-testid="stMetricLabel"] {font-size: 0.85rem; color: #555;}
    h1 {color: #1f2937;}
    h2, h3 {color: #2d3748;}
    .narrative-box {
        background-color: #f0f4f8;
        border-left: 4px solid #4C78A8;
        padding: 14px 18px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .flag-box {
        background-color: #fff4f4;
        border-left: 4px solid #E45756;
        padding: 14px 18px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("approval_data_clean.csv", parse_dates=["approval_date"])
    df["payout_period"] = np.where(
        df["approval_date"] < pd.Timestamp("2020-06-01"),
        "Pre-June 2020 ($50)", "Post-June 2020 ($17)"
    )
    return df

df = load_data()
technicians_all = sorted(df["technician"].unique())

# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
st.title("📋 Technician Approval Patterns Dashboard")
st.caption("ClearCheck Technologies — Remote Device Authorization Case Study | 15-month review period")

# ---------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------
st.sidebar.header("🔍 Filters")
selected_techs = st.sidebar.multiselect("Technician(s)", technicians_all, default=technicians_all)

min_date = df["approval_date"].min().date()
max_date = df["approval_date"].max().date()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

fast_threshold = st.sidebar.select_slider(
    "Highlight approvals faster than (sec)", options=[2, 5, 10, 30, 60], value=10
)

st.sidebar.divider()
compare_mode = st.sidebar.checkbox("Enable technician comparison mode", value=False)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

mask = (
    df["technician"].isin(selected_techs)
    & (df["approval_date"].dt.date >= start_date)
    & (df["approval_date"].dt.date <= end_date)
)
fdf = df[mask].copy()

if fdf.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

color_map = {t: TECH_COLORS.get(t, "#888") for t in technicians_all}

# ---------------------------------------------------------
# TABS
# ---------------------------------------------------------
tab_summary, tab_speed, tab_batch, tab_payout, tab_stats, tab_data = st.tabs(
    ["📌 Executive Summary", "⚡ Speed Analysis", "📦 Batch Claim", "💰 Payout Policy", "🧮 Statistical Tests", "📄 Raw Data"]
)

# ===========================================================
# TAB 1: EXECUTIVE SUMMARY
# ===========================================================
with tab_summary:
    st.markdown("""
    <div class="narrative-box">
    <b>In plain terms:</b> This dashboard examines whether three technicians reviewed device approval
    cases carefully, or rushed through them. Across 15 months and over 64,000 approvals, the typical
    review took only a few seconds — far below any reasonable industry standard — and the technicians'
    own "we batch-review, then approve" explanation does not hold up when tested against the data.
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Approvals", f"{len(fdf):,}")
    c2.metric("Median Review Time", f"{fdf['duration_sec'].median():.0f} sec")
    c3.metric(f"% Under {fast_threshold}s", f"{(fdf['duration_sec'] < fast_threshold).mean()*100:.1f}%")
    c4.metric("Technicians in View", fdf["technician"].nunique())

    st.markdown("### Key Findings")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="flag-box">
        <b>🚩 Speed:</b> All three technicians' average review times are statistically significantly
        below every benchmark tested (10, 5, 2, and 1 minute). Gary Arnold's median review time is
        just 4 seconds.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="flag-box">
        <b>🚩 Batch defense doesn't hold:</b> If technicians pre-reviewed cases then rapidly
        approved them, review speed should improve inside large blocks. It doesn't — Gary Arnold
        and Matt Shawn approve at essentially the same pace whether in a 5-case or 100-case block.
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="narrative-box">
        <b>✔️ Nuance:</b> Juan Mendez is a clear exception — his review pace (median 28 sec) and
        in-block behavior are much more consistent with genuine case-by-case review.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="narrative-box">
        <b>⚠️ Data limitation:</b> Only Gary Arnold's records span the June 2020 payout cut
        ($50→$17/case). For him, review time dropped significantly after the cut — but this can't
        be generalized to the other two technicians, who left before the change.
        </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Share of Total Approvals")
        vol = fdf["technician"].value_counts().reset_index()
        vol.columns = ["technician", "count"]
        fig_donut = px.pie(
            vol, names="technician", values="count", hole=0.55,
            color="technician", color_discrete_map=color_map
        )
        fig_donut.update_traces(textinfo="label+percent", textposition="outside")
        fig_donut.update_layout(showlegend=False, annotations=[dict(
            text=f"{len(fdf):,}<br>approvals", x=0.5, y=0.5, font_size=16, showarrow=False
        )])
        st.plotly_chart(fig_donut, use_container_width=True)
    with col2:
        st.markdown(f"### Fast (&lt;{fast_threshold}s) vs. Normal Approvals")
        fast_split = fdf["duration_sec"].apply(lambda x: f"Under {fast_threshold}s" if x < fast_threshold else f"{fast_threshold}s or more")
        split_counts = fast_split.value_counts().reset_index()
        split_counts.columns = ["category", "count"]
        fig_donut2 = px.pie(
            split_counts, names="category", values="count", hole=0.55,
            color="category", color_discrete_map={f"Under {fast_threshold}s": "#E45756", f"{fast_threshold}s or more": "#c9c9c9"}
        )
        fig_donut2.update_traces(textinfo="label+percent", textposition="outside")
        pct = (fdf["duration_sec"] < fast_threshold).mean() * 100
        fig_donut2.update_layout(showlegend=False, annotations=[dict(
            text=f"{pct:.0f}%<br>fast", x=0.5, y=0.5, font_size=16, showarrow=False
        )])
        st.plotly_chart(fig_donut2, use_container_width=True)

    st.markdown("### Duration Overview")
    fig_overview = px.box(
        fdf, x="technician", y="duration_sec", color="technician",
        color_discrete_map=color_map, points=False, log_y=True,
        labels={"duration_sec": "Duration (sec, log scale)"}
    )
    fig_overview.update_layout(showlegend=False)
    st.plotly_chart(fig_overview, use_container_width=True)

    st.markdown("### Technician Comparison Radar")
    st.caption("Each metric is normalized 0-100 (higher = more of that behavior) so technicians with very different scales can be compared on one chart.")
    radar_rows = []
    for tech in selected_techs:
        tdata = fdf[fdf["technician"] == tech]
        radar_rows.append({
            "technician": tech,
            "Fast-approval %": (tdata["duration_sec"] < fast_threshold).mean() * 100,
            "Same-second %": (tdata["duration_sec"] == 0).mean() * 100,
            "Median speed (inv)": 100 - min(tdata["duration_sec"].median(), 100),
            "Volume (rel.)": len(tdata) / fdf.groupby("technician").size().max() * 100,
        })
    radar_df = pd.DataFrame(radar_rows)
    categories = ["Fast-approval %", "Same-second %", "Median speed (inv)", "Volume (rel.)"]
    fig_radar = go.Figure()
    for _, row in radar_df.iterrows():
        fig_radar.add_trace(go.Scatterpolar(
            r=[row[c] for c in categories] + [row[categories[0]]],
            theta=categories + [categories[0]],
            fill="toself", name=row["technician"],
            line_color=color_map.get(row["technician"], "#888")
        ))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True)
    st.plotly_chart(fig_radar, use_container_width=True)

# ===========================================================
# TAB 2: SPEED ANALYSIS
# ===========================================================
with tab_speed:
    st.subheader("Distribution of Approval Durations")
    cap = st.slider("Cap x-axis at (seconds)", 30, 600, 300, step=30, key="cap1")
    plot_df = fdf[fdf["duration_sec"] <= cap]

    fig_hist = px.histogram(
        plot_df, x="duration_sec", color="technician", color_discrete_map=color_map,
        nbins=60, barmode="overlay", opacity=0.65,
        labels={"duration_sec": "Duration (seconds)"}
    )
    fig_hist.add_vline(x=fast_threshold, line_dash="dash", line_color="black",
                        annotation_text=f"{fast_threshold}s threshold")
    st.plotly_chart(fig_hist, use_container_width=True)

    st.subheader("Fast-Approval Rates by Threshold")
    thresholds = [2, 5, 10, 30, 60]
    fast_table = pd.DataFrame({
        f"< {t}s": fdf.groupby("technician")["duration_sec"].apply(lambda x: (x < t).mean()*100)
        for t in thresholds
    }).round(1)
    st.dataframe(fast_table.style.background_gradient(cmap="Reds", axis=1), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Approval Days")
        daily = fdf.assign(day=fdf["approval_date"].dt.date).groupby("day").size().reset_index(name="approvals")
        top_days = daily.sort_values("approvals", ascending=False).head(10)
        fig_days = px.bar(top_days.sort_values("approvals"), x="approvals", y="day", orientation="h")
        st.plotly_chart(fig_days, use_container_width=True)
    with col2:
        st.subheader("Approvals by Hour of Day")
        hourly = fdf.groupby(["hour", "technician"]).size().reset_index(name="count")
        fig_hourly = px.line(hourly, x="hour", y="count", color="technician",
                              color_discrete_map=color_map, markers=True)
        st.plotly_chart(fig_hourly, use_container_width=True)

    st.subheader("Activity Heatmap: Hour × Weekday")
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    heat_data = fdf.groupby(["weekday", "hour"]).size().reset_index(name="count")
    heat_pivot = heat_data.pivot(index="weekday", columns="hour", values="count").reindex(weekday_order).fillna(0)
    fig_heat = px.imshow(
        heat_pivot, aspect="auto", color_continuous_scale="YlOrRd",
        labels=dict(x="Hour of Day", y="Weekday", color="Approvals")
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    if compare_mode and len(selected_techs) >= 2:
        st.subheader("Side-by-Side Technician Comparison")
        cols = st.columns(len(selected_techs))
        for i, tech in enumerate(selected_techs):
            tdata = fdf[fdf["technician"] == tech]["duration_sec"]
            with cols[i]:
                st.markdown(f"**{tech}**")
                st.metric("Median (sec)", f"{tdata.median():.1f}")
                st.metric("Mean (sec)", f"{tdata.mean():.1f}")
                st.metric(f"% < {fast_threshold}s", f"{(tdata < fast_threshold).mean()*100:.1f}%")

# ===========================================================
# TAB 3: BATCH CLAIM
# ===========================================================
with tab_batch:
    st.markdown("""
    <div class="narrative-box">
    A <b>block</b> is a review session — a run of approvals where the gap between consecutive cases
    is under 10 minutes. A new block starts after any 10+ minute gap. If technicians genuinely
    pre-reviewed cases and batch-approved them, review speed <i>within</i> a block should be much
    faster than their overall pace, and should get faster as blocks get bigger. The data below tests that.
    </div>
    """, unsafe_allow_html=True)

    block_view = (
        fdf.dropna(subset=["block_id"])
        .groupby(["technician", "block_id"])
        .agg(cases_in_block=("case_number", "count"),
             block_start=("approval_date", "min"),
             block_end=("approval_date", "max"),
             avg_review_time=("duration_sec", lambda x: x[x < 600].mean()))
        .reset_index()
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Block Size Distribution")
        fig_bh = px.histogram(
            block_view[block_view["cases_in_block"] <= 100],
            x="cases_in_block", color="technician", color_discrete_map=color_map,
            nbins=30, barmode="overlay", opacity=0.65
        )
        st.plotly_chart(fig_bh, use_container_width=True)
    with col2:
        st.subheader("Block Size vs. Review Speed")
        fig_bs = px.scatter(
            block_view[block_view["cases_in_block"] <= 150],
            x="cases_in_block", y="avg_review_time", color="technician",
            color_discrete_map=color_map, opacity=0.5,
            labels={"avg_review_time": "Avg review time in block (sec)"}
        )
        st.plotly_chart(fig_bs, use_container_width=True)

    st.subheader("Block Composition Treemap")
    st.caption("Each rectangle is one review block, sized by number of cases. Bigger blocks = larger rectangles. Grouped by technician.")
    treemap_df = block_view.copy()
    treemap_df["block_label"] = "Block " + treemap_df["block_id"].astype(str)
    fig_tree = px.treemap(
        treemap_df, path=["technician", "block_label"], values="cases_in_block",
        color="avg_review_time", color_continuous_scale="RdYlGn_r",
        labels={"avg_review_time": "Avg review time (sec)"}
    )
    st.plotly_chart(fig_tree, use_container_width=True)

    st.subheader("Block-Level KPI Summary")
    kpis = block_view.groupby("technician").agg(
        total_blocks=("block_id", "count"),
        avg_cases_per_block=("cases_in_block", "mean"),
        median_cases_per_block=("cases_in_block", "median"),
        max_cases_per_block=("cases_in_block", "max"),
        avg_review_time_in_block=("avg_review_time", "mean"),
    ).round(2)
    st.dataframe(kpis, use_container_width=True)
    st.caption("Verdict: review speed stays flat as block size grows for Gary Arnold and Matt Shawn — "
               "inconsistent with genuine upfront batch review. Juan Mendez's slower, steadier pace is the exception.")

# ===========================================================
# TAB 4: PAYOUT POLICY
# ===========================================================
with tab_payout:
    st.markdown("""
    <div class="flag-box">
    <b>Data limitation:</b> Only Gary Arnold's approvals span the June 2020 payout change
    ($50 → $17 per case). Juan Mendez and Matt Shawn's records end before that date, so a
    company-wide before/after comparison would be misleading — it would mix a real behavior
    change with an unrelated shift in who was active. The chart below isolates Gary Arnold.
    </div>
    """, unsafe_allow_html=True)

    review_df = fdf[~fdf["is_session_gap"]] if "is_session_gap" in fdf.columns else fdf
    ga = review_df[review_df["technician"] == "Gary Arnold"]

    if not ga.empty and ga["payout_period"].nunique() == 2:
        summary = ga.groupby("payout_period")["duration_sec"].agg(["count", "mean", "median"]).round(2)
        st.dataframe(summary, use_container_width=True)

        fig_pay = px.box(ga, x="payout_period", y="duration_sec", color="payout_period",
                          log_y=True, labels={"duration_sec": "Duration (sec, log scale)"})
        st.plotly_chart(fig_pay, use_container_width=True)

        pre = ga[ga["payout_period"] == "Pre-June 2020 ($50)"]["duration_sec"].dropna()
        post = ga[ga["payout_period"] == "Post-June 2020 ($17)"]["duration_sec"].dropna()
        if len(pre) > 1 and len(post) > 1:
            t_stat, p_val = stats.ttest_ind(pre, post, equal_var=False)
            st.metric("Welch's t-test p-value (Gary Arnold, pre vs. post)", f"{p_val:.2e}")
            st.caption(f"Mean dropped from {pre.mean():.1f}s to {post.mean():.1f}s after the payout cut "
                       f"({'statistically significant' if p_val < 0.05 else 'not significant'}, p < 0.05 threshold).")
    else:
        st.info("Select Gary Arnold and a date range spanning June 2020 to see this comparison.")

# ===========================================================
# TAB 5: STATISTICAL TESTS
# ===========================================================
with tab_stats:
    st.subheader("One-Sample T-Tests vs. Industry Benchmarks")
    st.caption("Tests whether each technician's average IN-BLOCK review time is significantly below "
               "the stated benchmark (session-start gaps excluded).")

    review_df = fdf[~fdf["is_session_gap"]] if "is_session_gap" in fdf.columns else fdf
    benchmarks = [10, 5, 2, 1]
    rows = []
    for tech in selected_techs:
        durations = review_df[review_df["technician"] == tech]["duration_sec"].dropna()
        if len(durations) < 2:
            continue
        for b in benchmarks:
            t_stat, p_two = stats.ttest_1samp(durations, b*60)
            p_one = p_two/2 if t_stat < 0 else 1 - p_two/2
            rows.append({
                "Technician": tech, "Benchmark (min)": b,
                "Mean (sec)": round(durations.mean(), 1),
                "t-stat": round(t_stat, 2), "p-value (one-tailed)": f"{p_one:.2e}",
                "Significantly below benchmark?": "Yes" if (t_stat < 0 and p_one < 0.05) else "No"
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.subheader("Duplicate Case Numbers (Data Quality Flag)")
    dupe_count = fdf["case_number"].duplicated(keep=False).sum()
    st.metric("Rows with a repeated case number (in current filter)", f"{dupe_count:,}")
    st.caption("Mostly the same technician re-approving the same case at a different time; "
               "a small number were approved by more than one technician. Doesn't affect duration "
               "calculations, but worth flagging as a process/logging issue.")

# ===========================================================
# TAB 6: RAW DATA
# ===========================================================
with tab_data:
    st.subheader("Filtered Raw Data")
    show_cols = [c for c in ["case_number", "technician", "approval_date", "duration_sec",
                              "block_id", "payout_period"] if c in fdf.columns]
    st.dataframe(fdf[show_cols], use_container_width=True)
    st.download_button(
        "Download filtered data as CSV",
        fdf[show_cols].to_csv(index=False).encode("utf-8"),
        "filtered_approval_data.csv", "text/csv"
    )

st.divider()
st.caption("Data: 15 months of approval records, ClearCheck Technologies case study.")
