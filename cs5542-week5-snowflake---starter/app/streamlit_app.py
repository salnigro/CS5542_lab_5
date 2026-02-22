"""
streamlit_app.py — CS 5542 Week 5 Snowflake Dashboard
=====================================================
A Streamlit dashboard that connects to Snowflake, runs
parameterised queries, displays results with Altair charts,
and logs every query execution for monitoring.

Run with:
    streamlit run app/streamlit_app.py

References
----------
- Streamlit docs:       https://docs.streamlit.io/
- Streamlit cheat-sheet: https://docs.streamlit.io/develop/quick-reference/cheat-sheet
- Altair docs:           https://altair-viz.github.io/
- Snowflake SQL ref:     https://docs.snowflake.com/en/sql-reference
- Snowflake + Streamlit:  https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit
"""

import os
import sys
import time
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime

# Ensure the project root is on the path so `scripts.sf_connect` can be imported
# regardless of where Streamlit is launched from.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.sf_connect import get_conn

# ──────────────────── Config ────────────────────
DB = os.getenv("SNOWFLAKE_DATABASE", "INSTRUCTOR2_DB")
SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "MY_SCHEMA")
LOG_PATH = "logs/pipeline_logs.csv"
TABLES = ["EVENTS", "USERS", "ONLINE_RETAIL"]

# ──────────────────── Helpers ────────────────────

def log_event(team: str, user: str, query_name: str, latency_ms: int, rows: int, error: str = ""):
    """Append one row to the pipeline log CSV file."""
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "team": team, "user": user, "query_name": query_name,
        "latency_ms": latency_ms, "rows_returned": rows, "error": error,
    }
    df = pd.DataFrame([row])
    header = not os.path.exists(LOG_PATH) or os.path.getsize(LOG_PATH) == 0
    df.to_csv(LOG_PATH, mode="a", header=header, index=False)

@st.cache_resource
def get_cached_conn():
    """Return a Snowflake connection cached across Streamlit reruns."""
    return get_conn()

def run_query(sql: str):
    """Run SQL and return (DataFrame, latency_ms). Auto-reconnects on stale connections."""
    t0 = time.time()
    conn = get_cached_conn()
    try:
        df = pd.read_sql(sql, conn)
    except Exception:
        st.cache_resource.clear()
        conn = get_cached_conn()
        df = pd.read_sql(sql, conn)
    return df, int((time.time() - t0) * 1000)

def run_write(sql: str):
    """Execute a write SQL statement (UPDATE/INSERT/DELETE). Returns rows affected."""
    conn = get_cached_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        affected = cur.rowcount
        cur.close()
        return affected
    except Exception:
        st.cache_resource.clear()
        conn = get_cached_conn()
        cur = conn.cursor()
        cur.execute(sql)
        affected = cur.rowcount
        cur.close()
        return affected

def fqn(table: str) -> str:
    """Return fully qualified table name: DB.SCHEMA.TABLE"""
    return f"{DB}.{SCHEMA}.{table}"

# ══════════════════════════════════════════════════════════════
# UI LAYOUT
# ══════════════════════════════════════════════════════════════

st.set_page_config(page_title="CS 5542 Snowflake Dashboard", layout="wide")
st.title("❄️ CS 5542 — Week 5 Snowflake Dashboard")

# ── Sidebar: identification & settings ──
with st.sidebar:
    st.header("⚙️ Settings")
    team = st.text_input("Team name", value="TeamX")
    user = st.text_input("Your name", value="StudentName")
    st.divider()
    st.caption(f"Database: `{DB}`")
    st.caption(f"Schema: `{SCHEMA}`")

# ══════════════════════════════════════════════════════════════
# TAB 1: DATA EXPLORER  |  TAB 2: ANALYTICS  |  TAB 3: UPDATE RECORDS  |  TAB 4: LOGS
# ══════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4 = st.tabs(["📋 Data Explorer", "📊 Analytics", "✏️ Update Records", "📝 Logs"])

# ────────────────── TAB 1: DATA EXPLORER ──────────────────
with tab1:
    st.subheader("Browse Table Data")
    selected_table = st.selectbox("Select table", TABLES, key="explorer_table")

    if st.button("🔍 Load Data", key="load_data"):
        sql = f"SELECT * FROM {fqn(selected_table)} LIMIT 500;"
        try:
            df, latency_ms = run_query(sql)
            st.caption(f"✅ {len(df)} rows loaded in {latency_ms} ms")

            # Scrollable dataframe with height control
            st.dataframe(df, use_container_width=True, height=400)

            # Show schema information
            with st.expander("📐 Table Schema"):
                schema_sql = f"DESCRIBE TABLE {fqn(selected_table)};"
                schema_df, _ = run_query(schema_sql)
                st.dataframe(schema_df, use_container_width=True)

            log_event(team, user, f"SELECT * FROM {selected_table}", latency_ms, len(df))
        except Exception as e:
            st.error(f"Error: {e}")
            log_event(team, user, f"SELECT * FROM {selected_table}", 0, 0, str(e))

# ────────────────── TAB 2: ANALYTICS ──────────────────
with tab2:
    st.subheader("Analytical Queries")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        category = st.text_input("Category filter (optional)", value="", key="cat_filter")
    with col2:
        limit = st.slider("Limit rows", 10, 200, 50)

    base_where = ""
    if category.strip():
        safe = category.strip().replace("'", "''")
        base_where = f"WHERE CATEGORY ILIKE '%{safe}%'"

    # Pre-built queries
    q1 = f"""
    SELECT COUNTRY,
    SUM(QUANTITY * PRICE) AS TOTAL_REVENUE
    FROM ONLINE_RETAIL
    GROUP BY COUNTRY
    ORDER BY TOTAL_REVENUE DESC
    LIMIT {limit};
    """

    q2 = f"""
    SELECT 
    DESCRIPTION,
    SUM(QUANTITY) AS TOTAL_SOLD
    FROM ONLINE_RETAIL
    GROUP BY DESCRIPTION
    ORDER BY TOTAL_SOLD DESC
    LIMIT {limit};
    """

    q3 = f"""
    SELECT 
    DATE_TRUNC('month', INVOICEDATE) AS MONTH,
    SUM(QUANTITY * PRICE) AS REVENUE
    FROM ONLINE_RETAIL
    GROUP BY MONTH
    ORDER BY MONTH
    LIMIT {limit};
    """

    queries = {
        "Q1: Country × Total Revenue": q1,
        "Q2: Description x Total Sold": q2,
        "Q3: Revenue over Time": q3,
    }

    choice = st.selectbox("Choose query", list(queries.keys()))
    sql = queries[choice]

    with st.expander("View SQL"):
        st.code(sql, language="sql")

    if st.button("▶️ Run Query", key="run_analytics"):
        try:
            df, latency_ms = run_query(sql)
            st.caption(f"✅ Latency: {latency_ms} ms | Rows: {len(df)}")
            st.dataframe(df, use_container_width=True, height=350)

            # Auto-chart
            if "N" in df.columns and "CATEGORY" in df.columns:
                chart = alt.Chart(df).mark_bar().encode(
                    x=alt.X("CATEGORY:N", sort="-y"),
                    y="N:Q",
                    color=alt.Color("CATEGORY:N", legend=None),
                    tooltip=["CATEGORY", "N"]
                ).properties(height=300)
                st.altair_chart(chart, use_container_width=True)

            if "N_24H" in df.columns and "CATEGORY" in df.columns:
                chart = alt.Chart(df).mark_bar().encode(
                    x=alt.X("CATEGORY:N", sort="-y"),
                    y="N_24H:Q",
                    color=alt.Color("CATEGORY:N", legend=None),
                    tooltip=["CATEGORY", "N_24H"]
                ).properties(height=300)
                st.altair_chart(chart, use_container_width=True)

            log_event(team, user, choice, latency_ms, len(df))
        except Exception as e:
            st.error(f"Error: {e}")
            log_event(team, user, choice, 0, 0, str(e))

# ────────────────── TAB 3: UPDATE RECORDS ──────────────────
with tab3:
    st.subheader("Update / Modify Records")
    st.info("Select a table, identify the record to update using a WHERE condition, then set the new value.")

    update_table = st.selectbox("Table to update", TABLES, key="update_table")

    # Column definitions per table
    table_columns = {
        "EVENTS": ["EVENT_ID", "EVENT_TIME", "TEAM", "CATEGORY", "VALUE"],
        "USERS":  ["USER_ID", "TEAM", "ROLE", "CREATED_AT"],
        "ONLINE_RETAIL":["Invoice","StockCode","Description","Quantity","InvoiceDate","Price","Customer ID","Country"]
    }

    cols = table_columns.get(update_table, [])

    st.markdown("---")
    st.markdown("**Step 1: Preview current data**")
    if st.button("📋 Preview Table", key="preview_update"):
        preview_sql = f"SELECT * FROM {fqn(update_table)} LIMIT 100;"
        try:
            df, _ = run_query(preview_sql)
            st.dataframe(df, use_container_width=True, height=250)
        except Exception as e:
            st.error(f"Error loading preview: {e}")

    st.markdown("---")
    st.markdown("**Step 2: Configure the UPDATE**")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("*SET (what to change):*")
        set_column = st.selectbox("Column to update", cols, key="set_col")
        new_value = st.text_input("New value", key="new_val")

    with col_b:
        st.markdown("*WHERE (which rows):*")
        where_column = st.selectbox("WHERE column", cols, key="where_col")
        where_value = st.text_input("WHERE value (exact match)", key="where_val")

    # Build UPDATE statement
    if new_value and where_value:
        safe_new = new_value.replace("'", "''")
        safe_where = where_value.replace("'", "''")
        update_sql = f"UPDATE {fqn(update_table)} SET {set_column} = '{safe_new}' WHERE {where_column} = '{safe_where}';"

        with st.expander("Preview SQL"):
            st.code(update_sql, language="sql")

        if st.button("⚡ Execute UPDATE", key="exec_update", type="primary"):
            try:
                affected = run_write(update_sql)
                st.success(f"✅ UPDATE complete — {affected} row(s) affected.")
                log_event(team, user, f"UPDATE {update_table}", 0, affected)

                # Show updated data
                st.markdown("**Updated data:**")
                post_sql = f"SELECT * FROM {fqn(update_table)} WHERE {where_column} = '{safe_new}' LIMIT 50;"
                try:
                    df, _ = run_query(post_sql)
                    st.dataframe(df, use_container_width=True)
                except Exception:
                    # Fallback: show all data
                    df, _ = run_query(f"SELECT * FROM {fqn(update_table)} LIMIT 50;")
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"UPDATE failed: {e}")
                log_event(team, user, f"UPDATE {update_table}", 0, 0, str(e))
    else:
        st.caption("Fill in both the new value and WHERE condition to generate the UPDATE statement.")

# ────────────────── TAB 4: LOGS ──────────────────
with tab4:
    st.subheader("Pipeline Execution Logs")
    if os.path.exists(LOG_PATH):
        log_df = pd.read_csv(LOG_PATH)
        st.caption(f"Total log entries: {len(log_df)}")
        st.dataframe(log_df.tail(50), use_container_width=True, height=400)
    else:
        st.info("No logs yet. Run a query to generate logs.")
