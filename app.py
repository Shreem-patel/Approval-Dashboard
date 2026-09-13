import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(page_title="Approval Patterns Dashboard", layout="wide")

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("approval_data_clean.csv", parse_dates=["approval_date"])
    return df

df = load_data()

st.title("Technician Approval Patterns Dashboard")
st.caption("ClearCheck Technologies — Remote Device Authorization Case Study")

# ---------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------
st.sidebar.header("Filters")

technicians = sorted(df["technician"].unique())
selected_techs = st.sidebar.multiselect(
    "Technician(s)", technicians, default=technicians
)

min_date = df["approval_date"].min().date()
max_date = df["approval_date"].max().date()
date_range = st.sidebar.date_input(
    "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)

fast_threshold = st.sidebar.select_slider(
    "Highlight approvals faster than (seconds)",
    options=[2, 5, 10, 30, 60],
    value=10
)

# Apply filters
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
    st.warning("No data matches the selected filters. Adjust the technician or date range.")
    st.stop()

# ---------------------------------------------------------
# TOP-LEVEL KPIs
# ---------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Approvals", f"{len(fdf):,}")
col2.metric("Median Duration (sec)", f"{fdf['duration_sec'].median():.1f}")
col3.metric(
    f"% Under {fast_threshold} sec",
    f"{(fdf['duration_sec'] < fast_threshold).mean() * 100:.1f}%"
)
col4.metric("Technicians Shown", f"{fdf['technician'].nunique()}")

st.divider()

# ---------------------------------------------------------
# ROW 1: HISTOGRAM OF DURATIONS + FAST APPROVAL HIGHLIGHT
# ---------------------------------------------------------
r1c1, r1c2 = st.columns(2)

with r1c1:
    st.subheader("Distribution of Approval Durations")
    cap = st.slider("Cap x-axis at (seconds)", 30, 600, 300, step=30)
    plot_df = fdf[fdf["duration_sec"] <= cap].copy()
    plot_df["is_fast"] = plot_df["duration_sec"] < fast_threshold

    fig_hist = px.histogram(
        plot_df, x="duration_sec", color="technician",
        nbins=60, barmode="overlay", opacity=0.6,
        labels={"duration_sec": "Duration (seconds)"},
    )
    fig_hist.add_vline(
        x=fast_threshold, line_dash="dash", line_color="red",
        annotation_text=f"{fast_threshold}s threshold"
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with r1c2:
    st.subheader(f"Fast-Approval Rate (< {fast_threshold} sec)")
    fast_pct = (
        fdf.groupby("technician")["duration_sec"]
        .apply(lambda x: (x < fast_threshold).mean() * 100)
        .reset_index(name="pct_fast")
    )
    fig_fast = px.bar(
        fast_pct, x="technician", y="pct_fast", color="technician",
        text=fast_pct["pct_fast"].round(1).astype(str) + "%",
        labels={"pct_fast": "% of approvals"}
    )
    fig_fast.update_traces(textposition="outside")
    st.plotly_chart(fig_fast, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# ROW 2: TOP APPROVAL DAYS + HOUR/WEEKDAY PATTERNS
# ---------------------------------------------------------
r2c1, r2c2 = st.columns(2)

with r2c1:
    st.subheader("Top Approval Days")
    daily_counts = (
        fdf.assign(day=fdf["approval_date"].dt.date)
        .groupby(["day", "technician"]).size()
        .reset_index(name="approvals")
    )
    top_days = (
        daily_counts.groupby("day")["approvals"].sum()
        .sort_values(ascending=False).head(10).reset_index()
    )
    fig_top_days = px.bar(
        top_days.sort_values("approvals"), x="approvals", y="day",
        orientation="h", labels={"approvals": "Total Approvals", "day": "Date"}
    )
    st.plotly_chart(fig_top_days, use_container_width=True)

with r2c2:
    st.subheader("Approvals by Hour of Day")
    hourly = fdf.groupby(["hour", "technician"]).size().reset_index(name="count")
    fig_hourly = px.line(
        hourly, x="hour", y="count", color="technician", markers=True,
        labels={"hour": "Hour of Day", "count": "Approvals"}
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# ROW 3: BLOCK VISUALIZATION AND SUMMARY
# ---------------------------------------------------------
st.subheader("Approval Block Analysis")
st.caption(
    "A block is a review session: a run of approvals where the gap between "
    "consecutive cases is under 10 minutes. A new block starts after a 10+ minute gap."
)

block_view = (
    fdf.dropna(subset=["block_id"])
    .groupby(["technician", "block_id"])
    .agg(
        cases_in_block=("case_number", "count"),
        block_start=("approval_date", "min"),
        block_end=("approval_date", "max"),
        avg_review_time=("duration_sec", lambda x: x[x < 600].mean())
    ).reset_index()
)

r3c1, r3c2 = st.columns(2)

with r3c1:
    st.markdown("**Block Size Distribution**")
    fig_block_hist = px.histogram(
        block_view[block_view["cases_in_block"] <= 100],
        x="cases_in_block", color="technician", nbins=30, barmode="overlay", opacity=0.6,
        labels={"cases_in_block": "Cases per Block"}
    )
    st.plotly_chart(fig_block_hist, use_container_width=True)

with r3c2:
    st.markdown("**Block Size vs. Avg Review Time (tests the 'batch approval' claim)**")
    fig_block_scatter = px.scatter(
        block_view[block_view["cases_in_block"] <= 150],
        x="cases_in_block", y="avg_review_time", color="technician",
        labels={"cases_in_block": "Cases in Block", "avg_review_time": "Avg Review Time (sec)"},
        opacity=0.5
    )
    st.plotly_chart(fig_block_scatter, use_container_width=True)

st.markdown("**Block-Level KPI Summary**")
block_kpis = block_view.groupby("technician").agg(
    total_blocks=("block_id", "count"),
    avg_cases_per_block=("cases_in_block", "mean"),
    median_cases_per_block=("cases_in_block", "median"),
    max_cases_per_block=("cases_in_block", "max"),
    avg_review_time_in_block=("avg_review_time", "mean"),
).round(2).reset_index()
st.dataframe(block_kpis, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# ROW 4: RAW DATA (FILTERED)
# ---------------------------------------------------------
with st.expander("View filtered raw data"):
    st.dataframe(
        fdf[["case_number", "technician", "approval_date", "duration_sec", "block_id"]],
        use_container_width=True
    )

st.caption("Data: 15 months of approval records, ClearCheck Technologies case study.")
