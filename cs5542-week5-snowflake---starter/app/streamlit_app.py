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
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

# Ensure the project root is on the path so `scripts.sf_connect` can be imported
# regardless of where Streamlit is launched from.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.sf_connect import get_conn
from scripts.retrieve import Retriever
from app.chat_agent import get_agent

# ──────────────────── Config ────────────────────
DB = os.getenv("SNOWFLAKE_DATABASE", "INSTRUCTOR2_DB")
SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "MY_SCHEMA")
LOG_PATH = "logs/pipeline_logs.csv"
TABLES = ["EVENTS", "USERS", "ONLINE_RETAIL", "OLIST_ORDERS"]

# ──────────────────── Logging Setup ────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ──────────────────── Helpers ────────────────────

def log_event(team: str, user: str, query_name: str, latency_ms: int, rows: int, error: str = ""):
    """Log to both local CSV and Snowflake QUERY_LOGS table."""
    
    # ── Local CSV Logging ──
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "team": team,
        "user": user,
        "query_name": query_name,
        "latency_ms": latency_ms,
        "rows_returned": rows,
        "error": error,
    }
    df = pd.DataFrame([row])
    header = not os.path.exists(LOG_PATH) or os.path.getsize(LOG_PATH) == 0
    df.to_csv(LOG_PATH, mode="a", header=header, index=False)

    # ── Snowflake Logging ──
    try:
        conn = get_cached_conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS QUERY_LOGS (
                TIMESTAMP TIMESTAMP_NTZ,
                TEAM STRING,
                USER_NAME STRING,
                QUERY_NAME STRING,
                LATENCY_MS NUMBER,
                ROWS_RETURNED NUMBER,
                ERROR STRING
            );
        """)

        cur.execute("""
            INSERT INTO QUERY_LOGS
            (TIMESTAMP, TEAM, USER_NAME, QUERY_NAME, LATENCY_MS, ROWS_RETURNED, ERROR)
            VALUES (CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s)
        """, (team, user, query_name, latency_ms, rows, error))

        cur.close()
    except Exception:
        pass

@st.cache_resource
def get_cached_conn():
    """Return a Snowflake connection cached across Streamlit reruns."""
    return get_conn()

def run_query(sql: str):
    """Run SQL and return (DataFrame, latency_ms). Auto-reconnects on stale connections."""
    t0 = time.time()
    conn = get_cached_conn()
    try:
        logger.info(f"Executing query: {sql[:100]}...")
        df = pd.read_sql(sql, conn)
    except Exception as e:
        logger.warning(f"Query failed, reconnecting. Error: {e}")
        st.cache_resource.clear()
        conn = get_cached_conn()
        try:
            df = pd.read_sql(sql, conn)
        except Exception as retry_e:
            logger.error(f"Retry query failed: {retry_e}", exc_info=True)
            raise retry_e
    
    latency = int((time.time() - t0) * 1000)
    logger.info(f"Query completed in {latency} ms with {len(df)} rows.")
    return df, latency

@st.cache_data(ttl=600, show_spinner=False)
def run_query_cached(sql: str):
    """Cached version of run_query for read-only analytics."""
    logger.info(f"Cache miss for query, querying DB...")
    # st.cache_data requires return values to be serializable, so we only cache the dataframe
    # Latency will be recorded as 0 when hitting cache
    t0 = time.time()
    conn = get_conn() # Do not use the cached connection resource inside a cache_data, instead get a new or separate connection or rely on sf_connect
    try:
         df = pd.read_sql(sql, conn)
    except Exception as e:
         logger.error(f"Cached query failed: {e}", exc_info=True)
         raise e
    latency = int((time.time() - t0) * 1000)
    return df, latency

def run_write(sql: str):
    """Execute a write SQL statement (UPDATE/INSERT/DELETE). Returns rows affected."""
    conn = get_cached_conn()
    try:
        logger.info(f"Executing write: {sql[:100]}...")
        cur = conn.cursor()
        cur.execute(sql)
        affected = cur.rowcount
        cur.close()
        logger.info(f"Write successful. {affected} rows affected.")
        return affected
    except Exception as e:
        logger.warning(f"Write failed, reconnecting. Error: {e}")
        st.cache_resource.clear()
        conn = get_cached_conn()
        cur = conn.cursor()
        try:
            cur.execute(sql)
            affected = cur.rowcount
            cur.close()
            logger.info(f"Retry write successful. {affected} rows affected.")
            return affected
        except Exception as retry_e:
            logger.error(f"Retry write failed: {retry_e}", exc_info=True)
            raise retry_e

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

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "📋 Data Explorer",
    "📊 Analytics",
    "✏️ Update Records",
    "📝 Logs (Local)",
    "🏗 Warehouse Status",
    "🧠 Financial RAG",
    "🤖 Agent Chat",
    "⚖️ Domain Eval",
    "📈 App Metrics"
])

# ────────────────── TAB 1: DATA EXPLORER ──────────────────
with tab1:
    st.subheader("Browse Table Data")
    selected_table = st.selectbox("Select table", TABLES, key="explorer_table")

    if st.button("🔍 Load Data", key="load_data"):
        sql = f"SELECT * FROM {fqn(selected_table)} LIMIT 500;"
        try:
            # Use cached queries for explorer to avoid repeated loads
            df, latency_ms = run_query_cached(sql)
            st.caption(f"✅ {len(df)} rows loaded in ~{latency_ms} ms (cacheable)")

            # Scrollable dataframe with height control
            st.dataframe(df, use_container_width=True, height=400)

            # Show schema information
            with st.expander("📐 Table Schema"):
                schema_sql = f"DESCRIBE TABLE {fqn(selected_table)};"
                schema_df, _ = run_query_cached(schema_sql)
                st.dataframe(schema_df, use_container_width=True)

            log_event(team, user, f"SELECT * FROM {selected_table}", latency_ms, len(df))
        except Exception as e:
            logger.error(f"Error loading data for {selected_table}: {e}", exc_info=True)
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
    q4 = f"""
    SELECT 
    ORDER_STATUS,
    COUNT(*) AS TOTAL_ORDERS
    FROM OLIST_ORDERS
    GROUP BY ORDER_STATUS
    ORDER BY TOTAL_ORDERS DESC;
    """
    q5 = f"""
    SELECT 
    DATE_TRUNC('month', ORDER_PURCHASE_TIMESTAMP) AS MONTH,
    COUNT(*) AS TOTAL_ORDERS
    FROM OLIST_ORDERS
    GROUP BY MONTH
    ORDER BY MONTH;
    """
    q6 = f"""
    SELECT 
    COUNT(*) AS TOTAL_ORDERS,
    COUNT_IF(ORDER_DELIVERED_CUSTOMER_DATE > ORDER_ESTIMATED_DELIVERY_DATE) 
        AS LATE_DELIVERIES
    FROM OLIST_ORDERS
    WHERE ORDER_STATUS = 'delivered';
    """

    queries = {
        "Q1: Country × Total Revenue": q1,
        "Q2: Description x Total Sold": q2,
        "Q3: Revenue over Time": q3,
        "Q4: Orders by Status": q4,
        "Q5: Orders Over Time": q5,
        "Q6: Delivery Performance": q6,
    }

    choice = st.selectbox("Choose query", list(queries.keys()))
    sql = queries[choice]

    with st.expander("View SQL"):
        st.code(sql, language="sql")

    if st.button("▶️ Run Query", key="run_analytics"):
        try:
            df, latency_ms = run_query_cached(sql)
            st.caption(f"✅ Executed (cached) | Rows: {len(df)}")
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
            logger.error(f"Analytics query error: {e}", exc_info=True)
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
        "ONLINE_RETAIL":["Invoice","StockCode","Description","Quantity","InvoiceDate","Price","Customer ID","Country"],
        "OLIST_ORDERS": ["order_id","customer_id","order_status","order_purchase_timestamp","order_approved_at","order_delivered_carrier_date","order_delivered_customer_date","order_estimated_delivery_date"]
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
    st.markdown("---")
    st.subheader("Snowflake QUERY_LOGS Table")

    if st.button("Load Snowflake Logs"):
        try:
            df, _ = run_query("SELECT * FROM QUERY_LOGS ORDER BY TIMESTAMP DESC LIMIT 50;")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading Snowflake logs: {e}")

with tab5:
    st.subheader("Snowflake Warehouse Status")

    if st.button("Check Warehouse"):
        try:
            sql = "SELECT CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA();"
            df, latency = run_query(sql)
            st.dataframe(df)
            st.success(f"Connected successfully in {latency} ms")
        except Exception as e:
            st.error(f"Connection error: {e}")


# ────────────────── TAB 6: FINANCIAL RAG ──────────────────
with tab6:
    st.subheader("Financial News Retrieval (Twitter Sentiment Dataset)")

    query = st.text_input("Ask a financial question")

    if st.button("Retrieve Evidence"):
        try:
            logger.info(f"Running RAG retrieval for query: {query}")
            retriever = Retriever()
            results = retriever.search(query, k=5)

            st.markdown("### Retrieved Chunks")

            for i, r in enumerate(results):
                with st.expander(f"Result {i+1} | Source: {r['source']} | Score: {r['score']:.2f}"):
                    st.write(r["text"])

            combined_text = "\n\n".join([r["text"] for r in results])

            st.markdown("### Synthesized Answer")
            with st.spinner("Synthesizing answer with Gemini..."):
                llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.2)
                sys_msg = SystemMessage(content="You are a helpful financial assistant. Synthesize an answer to the user's query using ONLY the provided retrieved context. If the context does not contain the answer, say so.")
                user_msg = HumanMessage(content=f"Query: {query}\n\nContext:\n{combined_text}")
                response = llm.invoke([sys_msg, user_msg])
                st.write(response.content)
                logger.info("RAG Synthesis complete.")

        except Exception as e:
            logger.error(f"Retrieval error: {e}", exc_info=True)
            st.error(f"Retrieval error: {e}")

# ────────────────── TAB 7: AGENT CHAT ──────────────────
with tab7:
    st.subheader("Interactive AI Agent Interface")
    st.write("Ask complex queries. The agent will decide whether to write SQL or query the FAISS document retrieve.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User input
    if prompt := st.chat_input("E.g., What was the total revenue in France, and were there any news about tech stocks?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Agent response with spinner
        with st.chat_message("assistant"), st.spinner("Agent is reasoning and fetching data..."):
            try:
                logger.info(f"Agent invoked with prompt: {prompt}")
                agent = get_agent()
                inputs = {"messages": st.session_state.messages}
                start_time = time.time()

                result = agent.invoke(inputs)

                # ⏱️ End time
                end_time = time.time()
                latency = int((end_time - start_time) * 1000)
                logger.info(f"Agent response time: {latency} ms")

                # Extract response text
                response = result["messages"][-1].content
                if isinstance(response, list):
                    response = "".join(
                        part.get("text", "") for part in response if isinstance(part, dict) and "text" in part
                    )

                st.markdown(response)

                # Optional strong logging
                log_event(team, user, "Agent Query", latency, 1)
                st.session_state.messages.append({"role": "assistant", "content": response})
                logger.info("Agent execution successful.")

            except Exception as e:
                logger.error(f"Agent Execution Error: {e}", exc_info=True)
                st.error(f"Agent Execution Error: {str(e)}")
# ────────────────── TAB 8: DOMAIN EVALUATION ──────────────────
with tab8:
    st.subheader("Domain Adaptation Evaluation")
    st.write("Compare the generic baseline agent with the specialized domain-adapted agent.")
    
    eval_query = st.text_area(
        "Enter evaluation query", 
        value="Assess the sentiment and business outlook based on recent order fulfillment metrics."
    )
    
    if st.button("⚖️ Run Comparison", type="primary"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🤖 Baseline (Generic)")
            with st.spinner("Running Baseline Agent..."):
                try:
                    logger.info("Running Baseline Eval Agent")
                    baseline_agent = get_agent(adapted=False)
                    base_res = baseline_agent.invoke({"messages": [("user", eval_query)]})
                    
                    base_out = base_res["messages"][-1].content
                    if isinstance(base_out, list):
                        base_out = "".join(p.get("text", "") for p in base_out if isinstance(p, dict))
                        
                    st.info(base_out)
                except Exception as e:
                    logger.error(f"Baseline Eval Error: {e}", exc_info=True)
                    st.error(f"Error: {e}")
                    
        with col2:
            st.markdown("### 🎓 Adapted (Domain Expert)")
            with st.spinner("Running Adapted Agent..."):
                try:
                    logger.info("Running Adapted Eval Agent")
                    adapted_agent = get_agent(adapted=True)
                    adapt_res = adapted_agent.invoke({"messages": [("user", eval_query)]})
                    
                    adapt_out = adapt_res["messages"][-1].content
                    if isinstance(adapt_out, list):
                        adapt_out = "".join(p.get("text", "") for p in adapt_out if isinstance(p, dict))
                        
                    st.success(adapt_out)
                except Exception as e:
                    logger.error(f"Adapted Eval Error: {e}", exc_info=True)
                    st.error(f"Error: {e}")

# ────────────────── TAB 9: APP METRICS ──────────────────
with tab9:
    st.subheader("System Evaluation & Monitoring")
    st.write("Monitor system stability, query volumes, and latencies across users and teams.")
    
    if st.button("Load Metrics Dashboard"):
        if os.path.exists(LOG_PATH):
            try:
                metrics_df = pd.read_csv(LOG_PATH)
                metrics_df['timestamp'] = pd.to_datetime(metrics_df['timestamp'])
                
                st.metric(label="Total Queries Executed", value=len(metrics_df))
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Average Latency by Query Name**")
                    avg_latency = metrics_df.groupby('query_name')['latency_ms'].mean().reset_index()
                    chart = alt.Chart(avg_latency).mark_bar().encode(
                        x=alt.X('query_name:N', sort='-y', title="Query Type"),
                        y=alt.Y('latency_ms:Q', title="Avg Latency (ms)"),
                        color=alt.Color('query_name:N', legend=None),
                        tooltip=['query_name', 'latency_ms']
                    ).properties(height=300)
                    st.altair_chart(chart, use_container_width=True)
                
                with col_b:
                    st.markdown("**Query Execution Volume by Team**")
                    vol_team = metrics_df.groupby('team').size().reset_index(name='count')
                    chart2 = alt.Chart(vol_team).mark_arc().encode(
                        theta=alt.Theta(field="count", type="quantitative"),
                        color=alt.Color(field="team", type="nominal"),
                        tooltip=['team', 'count']
                    ).properties(height=300)
                    st.altair_chart(chart2, use_container_width=True)
                    
                st.markdown("**Error Logs Summary**")
                errors_df = metrics_df[metrics_df['error'].notna() & (metrics_df['error'] != "")]
                if not errors_df.empty:
                    st.warning(f"Found {len(errors_df)} errors in the logs.")
                    st.dataframe(errors_df[['timestamp', 'team', 'user', 'query_name', 'error']].tail(20), use_container_width=True)
                else:
                    st.success("No errors found in the logs!")
                    
            except Exception as e:
                logger.error(f"Error loading metrics: {e}", exc_info=True)
                st.error(f"Failed to generate custom metrics dashboard: {e}")
        else:
            st.info("No logs generated yet. Use the other tabs to generate logs.")
