-- ============================================================
-- 03_queries.sql — Example analytical queries
-- ============================================================
-- These are the same queries surfaced in the Streamlit dashboard
-- (app/streamlit_app.py).  Run them here in a worksheet if you
-- want to explore results before building UI.
--
-- References:
--   • Aggregate functions: https://docs.snowflake.com/en/sql-reference/functions-aggregation
--   • DATEADD:             https://docs.snowflake.com/en/sql-reference/functions/dateadd
--   • JOIN:                https://docs.snowflake.com/en/sql-reference/constructs/join
-- ============================================================

USE DATABASE EAGLE_DB;
USE SCHEMA MY_SCHEMA;

-- Q1: Basic aggregation — count events and average value per team × category.
--     Useful for spotting which teams are most active in each category.
SELECT 
  COUNTRY,
  SUM(QUANTITY * PRICE) AS TOTAL_REVENUE
FROM ONLINE_RETAIL
GROUP BY COUNTRY
ORDER BY TOTAL_REVENUE DESC;

-- Q2: Rolling 24-hour window — which categories have the most recent activity?
--     DATEADD('hour', -24, CURRENT_TIMESTAMP()) computes "24 hours ago".
SELECT 
  DESCRIPTION,
  SUM(QUANTITY) AS TOTAL_SOLD
FROM ONLINE_RETAIL
GROUP BY DESCRIPTION
ORDER BY TOTAL_SOLD DESC
LIMIT 10;

-- Q3: JOIN users ↔ events — attribute event categories to user roles.
--     The join key is TEAM (both tables share this column).
SELECT 
  DATE_TRUNC('month', INVOICEDATE) AS MONTH,
  SUM(QUANTITY * PRICE) AS REVENUE
FROM ONLINE_RETAIL
GROUP BY MONTH
ORDER BY MONTH;
