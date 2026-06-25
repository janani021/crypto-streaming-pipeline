import os
import html as html_lib
from datetime import timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from google.cloud import bigquery


st.set_page_config(
    page_title="Crypto Risk Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme CSS
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #0b1220 0%, #111827 100%);
            color: #e5e7eb;
        }

        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
        }

        h1, h2, h3, h4, p, label, div, span {
            color: #e5e7eb !important;
        }

        section[data-testid="stSidebar"] {
            background: #0f172a;
        }

        section[data-testid="stSidebar"] * {
            color: #f8fafc !important;
        }

        .stButton button {
            background: #2563eb !important;
            color: white !important;
            border: 1px solid #3b82f6 !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
        }

        .stButton button:hover {
            background: #1d4ed8 !important;
            border-color: #60a5fa !important;
        }

        .metric-card {
            background: rgba(17, 24, 39, 0.92);
            border: 1px solid rgba(75, 85, 99, 0.35);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            min-height: 120px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
        }

        .kpi-label {
            font-size: 0.95rem;
            color: #cbd5e1 !important;
            margin-bottom: 0.45rem;
            font-weight: 600;
        }

        .kpi-value {
            font-size: 2.4rem;
            font-weight: 800;
            color: #f8fafc !important;
            line-height: 1.05;
        }

        .impact-box {
            background: rgba(15, 23, 42, 0.95);
            border-left: 4px solid #38bdf8;
            padding: 1rem 1.2rem;
            border-radius: 14px;
            margin-top: 0.5rem;
            margin-bottom: 1rem;
        }

        .table-wrap {
            background: rgba(17, 24, 39, 0.92);
            border: 1px solid rgba(75, 85, 99, 0.35);
            border-radius: 18px;
            padding: 0.75rem;
            overflow-x: auto;
        }

        .dark-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
            color: #e5e7eb;
        }

        .dark-table th {
            position: sticky;
            top: 0;
            background: #1f2937;
            color: #f8fafc;
            text-align: left;
            padding: 0.75rem;
            border-bottom: 1px solid #334155;
            white-space: nowrap;
        }

        .dark-table td {
            padding: 0.7rem;
            border-bottom: 1px solid #334155;
            white-space: nowrap;
        }

        .dark-table tr:nth-child(even) {
            background: rgba(30, 41, 59, 0.55);
        }

        .dark-table tr:hover {
            background: rgba(59, 130, 246, 0.10);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# Config

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "skilful-card-498314-a2")
DATASET = os.getenv("BQ_DATASET", "crypto_analytics")

RAW_TABLE = f"`{PROJECT_ID}.{DATASET}.trades_raw`"
MART_TABLE = f"`{PROJECT_ID}.{DATASET}.mart_risk_signals`"

ALLOWED_ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD"]
RISK_ORDER = ["LOW", "MEDIUM", "HIGH"]

st.markdown("<br><br>", unsafe_allow_html=True)

st.title("📈 Crypto Risk Intelligence Dashboard")

# BigQuery client
@st.cache_resource
def get_client():
    return bigquery.Client(project=PROJECT_ID)

client = get_client()

# Helpers
@st.cache_data(ttl=60)
def load_date_bounds():
    query = f"""
    SELECT
      MIN(DATE(event_time)) AS min_date,
      MAX(DATE(event_time)) AS max_date
    FROM {RAW_TABLE}
    """
    return client.query(query).to_dataframe()


def build_asset_clause(selected_assets):
    return ", ".join([f"'{a}'" for a in selected_assets])


@st.cache_data(ttl=60)
def load_kpis(start_date, end_date, selected_assets):
    asset_clause = build_asset_clause(selected_assets)

    raw_query = f"""
    SELECT
      COUNT(*) AS total_raw_data,
      MAX(event_time) AS latest_event_time
    FROM {RAW_TABLE}
    WHERE DATE(event_time) BETWEEN '{start_date}' AND '{end_date}'
      AND product_id IN ({asset_clause})
    """

    mart_query = f"""
    SELECT
      COUNT(*) AS total_data_marts,
      SUM(trade_count) AS total_trades,
      AVG(avg_bid_ask_spread) AS avg_spread,
      COUNTIF(risk_level = 'HIGH') AS high_risk_rows
    FROM {MART_TABLE}
    WHERE DATE(minute_bucket) BETWEEN '{start_date}' AND '{end_date}'
      AND product_id IN ({asset_clause})
    """

    raw_df = client.query(raw_query).to_dataframe()
    mart_df = client.query(mart_query).to_dataframe()
    return raw_df.iloc[0], mart_df.iloc[0]


@st.cache_data(ttl=60)
def load_risk_table(start_date, end_date, selected_assets):
    asset_clause = build_asset_clause(selected_assets)
    query = f"""
    SELECT
      minute_bucket,
      product_id,
      trade_count,
      avg_price,
      avg_bid_ask_spread,
      avg_price_percent_chg_24_h,
      risk_level
    FROM {MART_TABLE}
    WHERE DATE(minute_bucket) BETWEEN '{start_date}' AND '{end_date}'
      AND product_id IN ({asset_clause})
    ORDER BY minute_bucket ASC
    """
    return client.query(query).to_dataframe()


@st.cache_data(ttl=60)
def load_risk_distribution(start_date, end_date, selected_assets):
    asset_clause = build_asset_clause(selected_assets)
    query = f"""
    SELECT
      risk_level,
      COUNT(*) AS cnt
    FROM {MART_TABLE}
    WHERE DATE(minute_bucket) BETWEEN '{start_date}' AND '{end_date}'
      AND product_id IN ({asset_clause})
    GROUP BY risk_level
    """
    return client.query(query).to_dataframe()


def render_kpi(title, value):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="kpi-label">{title}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def plot_line(df, x_col, y_col, title, color_discrete_sequence=None):
    if df.empty:
        st.info(f"No data for {title}.")
        return

    fig = px.line(
        df,
        x=x_col,
        y=y_col,
        color="product_id" if "product_id" in df.columns and df["product_id"].nunique() > 1 else None,
        template="plotly_dark",
        color_discrete_sequence=color_discrete_sequence,
    )

    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e5e7eb"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
    st.plotly_chart(fig, use_container_width=True)


def render_dark_table(df: pd.DataFrame):
    if df.empty:
        st.info("No rows to display.")
        return

    display_df = df.copy()

    # Format values a bit for readability
    if "minute_bucket" in display_df.columns:
        display_df["minute_bucket"] = pd.to_datetime(display_df["minute_bucket"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    for col in ["avg_price", "avg_bid_ask_spread", "avg_price_percent_chg_24_h"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].map(lambda x: f"{x:.6f}" if pd.notna(x) else "")

    for col in ["trade_count"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].map(lambda x: int(x) if pd.notna(x) else "")

    # Build HTML table
    headers = "".join(f"<th>{html_lib.escape(str(col))}</th>" for col in display_df.columns)
    rows_html = []
    for _, row in display_df.iterrows():
        cells = "".join(f"<td>{html_lib.escape(str(val))}</td>" for val in row.values)
        rows_html.append(f"<tr>{cells}</tr>")

    table_html = f"""
    <div class="table-wrap">
        <table class="dark-table">
            <thead>
                <tr>{headers}</tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Filters")

bounds_df = load_date_bounds()
min_d = bounds_df.iloc[0]["min_date"]
max_d = bounds_df.iloc[0]["max_date"]

if pd.isna(min_d) or pd.isna(max_d):
    st.warning("No data found in BigQuery tables.")
    st.stop()

default_start = max(min_d, max_d - timedelta(days=7))

date_range = st.sidebar.date_input(
    "Date range",
    value=(default_start, max_d),
    min_value=min_d,
    max_value=max_d,
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = default_start, max_d

selected_assets = st.sidebar.multiselect(
    "Assets",
    ALLOWED_ASSETS,
    default=ALLOWED_ASSETS,
)

if not selected_assets:
    st.warning("Select at least one asset.")
    st.stop()

refresh = st.sidebar.button("Refresh data")
if refresh:
    st.cache_data.clear()
    st.rerun()

# -----------------------------
# Business impact box
# -----------------------------
st.markdown(
    """
    <div class="impact-box">
        <h3 style="margin:0;">Business Impact</h3>
        <p style="margin:0.4rem 0 0 0;">
            This dashboard helps monitor live crypto market risk, detect unusual spread changes,
            and track market movement in near real time. It supports faster trading decisions,
            better liquidity monitoring, and early warning of volatile market conditions.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Load data
# -----------------------------
try:
    raw_kpi, mart_kpi = load_kpis(start_date, end_date, selected_assets)
    risk_df = load_risk_table(start_date, end_date, selected_assets)
    risk_dist_df = load_risk_distribution(start_date, end_date, selected_assets)
except Exception as e:
    st.error(f"Failed to load data from BigQuery: {e}")
    st.stop()

if risk_df.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

# -----------------------------
# KPI cards
# -----------------------------
k1, k2, k3, k4 = st.columns(4)

with k1:
    render_kpi("Total Raw Data", f"{int(raw_kpi['total_raw_data'])}")

with k2:
    render_kpi("Total Data Marts", f"{int(mart_kpi['total_data_marts'])}")

with k3:
    avg_spread = mart_kpi["avg_spread"]
    render_kpi("Avg Spread", f"{float(avg_spread):.4f}" if pd.notna(avg_spread) else "N/A")

with k4:
    high_risk = int(mart_kpi["high_risk_rows"]) if pd.notna(mart_kpi["high_risk_rows"]) else 0
    render_kpi("High Risk Rows", f"{high_risk}")

# -----------------------------
# Risk distribution chart
# -----------------------------
st.subheader("Risk Level Distribution")

risk_counts_df = risk_dist_df.set_index("risk_level") if not risk_dist_df.empty else pd.DataFrame()

risk_plot = pd.DataFrame(
    {
        "risk_level": RISK_ORDER,
        "count": [
            int(risk_counts_df.loc["LOW", "cnt"]) if "LOW" in risk_counts_df.index else 0,
            int(risk_counts_df.loc["MEDIUM", "cnt"]) if "MEDIUM" in risk_counts_df.index else 0,
            int(risk_counts_df.loc["HIGH", "cnt"]) if "HIGH" in risk_counts_df.index else 0,
        ],
    }
)

fig = px.bar(
    risk_plot,
    x="risk_level",
    y="count",
    text="count",
    color="risk_level",
    color_discrete_map={
        "LOW": "#22c55e",
        "MEDIUM": "#f59e0b",
        "HIGH": "#ef4444",
    },
    category_orders={"risk_level": RISK_ORDER},
    template="plotly_dark",
)
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    showlegend=False,
    height=420,
    margin=dict(l=20, r=20, t=30, b=20),
    font=dict(color="#e5e7eb"),
)
fig.update_xaxes(showgrid=False)
fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Charts
# -----------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("Trade Count Over Time")
    trade_df = (
        risk_df.groupby(["minute_bucket", "product_id"], as_index=False)["trade_count"]
        .sum()
        .sort_values("minute_bucket")
    )
    trade_pivot = trade_df.pivot(index="minute_bucket", columns="product_id", values="trade_count")
    fig_trade = px.line(
        trade_pivot.reset_index().melt(id_vars="minute_bucket", var_name="product_id", value_name="trade_count"),
        x="minute_bucket",
        y="trade_count",
        color="product_id",
        template="plotly_dark",
    )
    fig_trade.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(color="#e5e7eb"),
    )
    fig_trade.update_xaxes(showgrid=False)
    fig_trade.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
    st.plotly_chart(fig_trade, use_container_width=True)

with c2:
    st.subheader("Average Spread Over Time")
    spread_df = (
        risk_df.groupby(["minute_bucket", "product_id"], as_index=False)["avg_bid_ask_spread"]
        .mean()
        .sort_values("minute_bucket")
    )
    spread_pivot = spread_df.pivot(index="minute_bucket", columns="product_id", values="avg_bid_ask_spread")
    fig_spread = px.line(
        spread_pivot.reset_index().melt(id_vars="minute_bucket", var_name="product_id", value_name="avg_bid_ask_spread"),
        x="minute_bucket",
        y="avg_bid_ask_spread",
        color="product_id",
        template="plotly_dark",
    )
    fig_spread.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(color="#e5e7eb"),
    )
    fig_spread.update_xaxes(showgrid=False)
    fig_spread.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
    st.plotly_chart(fig_spread, use_container_width=True)

st.write("")

c3, c4 = st.columns(2)

with c3:
    st.subheader("Average Price Over Time")
    price_df = (
        risk_df.groupby(["minute_bucket", "product_id"], as_index=False)["avg_price"]
        .mean()
        .sort_values("minute_bucket")
    )
    price_pivot = price_df.pivot(index="minute_bucket", columns="product_id", values="avg_price")
    fig_price = px.line(
        price_pivot.reset_index().melt(id_vars="minute_bucket", var_name="product_id", value_name="avg_price"),
        x="minute_bucket",
        y="avg_price",
        color="product_id",
        template="plotly_dark",
    )
    fig_price.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(color="#e5e7eb"),
    )
    fig_price.update_xaxes(showgrid=False)
    fig_price.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
    st.plotly_chart(fig_price, use_container_width=True)

with c4:
    st.subheader("Latest Risk Signals")
    render_dark_table(
        risk_df.sort_values("minute_bucket", ascending=False).head(7)[
            [
                "minute_bucket",
                "product_id",
                "trade_count",
                "avg_price",
                "avg_bid_ask_spread",
                "avg_price_percent_chg_24_h",
                "risk_level",
            ]
        ]
    )

st.caption(f"Filtered from {start_date} to {end_date} | Assets: {', '.join(selected_assets)}")