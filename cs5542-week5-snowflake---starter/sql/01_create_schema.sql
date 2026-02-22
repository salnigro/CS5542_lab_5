-- ============================================================
-- 01_create_schema.sql — Database & table DDL
-- ============================================================
-- Run this script FIRST in a Snowflake Worksheet to create the
-- database, schema, and the two starter tables.
--
-- References:
--   • CREATE DATABASE: https://docs.snowflake.com/en/sql-reference/sql/create-database
--   • CREATE TABLE:    https://docs.snowflake.com/en/sql-reference/sql/create-table
--   • Data types:      https://docs.snowflake.com/en/sql-reference/data-types
-- ============================================================

-- 1. Create (or replace) the project database and schema.
CREATE OR REPLACE DATABASE EAGLE_DB;
CREATE SCHEMA IF NOT EXISTS EAGLE_DB.MY_SCHEMA;

CREATE OR REPLACE TABLE EAGLE_DB.MY_SCHEMA.ONLINE_RETAIL (
  INVOICE STRING,
  STOCKCODE STRING,
  DESCRIPTION STRING,
  QUANTITY INT,
  INVOICEDATE TIMESTAMP_NTZ,
  PRICE FLOAT,
  CUSTOMER_ID STRING,
  COUNTRY STRING
);

-- 2. EVENTS table — holds raw event/activity records.
--    Replace these sample columns with your project dataset columns.
--    • EVENT_ID   – unique identifier for each event
--    • EVENT_TIME – when the event occurred (TIMESTAMP without timezone)
--    • TEAM       – which team generated the event
--    • CATEGORY   – event type (e.g., "search", "upload", "analysis")
--    • VALUE      – a numeric metric associated with the event
CREATE TABLE IF NOT EXISTS EAGLE_DB.MY_SCHEMA.EVENTS (
  EVENT_ID STRING,
  EVENT_TIME TIMESTAMP_NTZ,
  TEAM STRING,
  CATEGORY STRING,
  VALUE FLOAT
);

-- 3. USERS table — team membership information.
--    • USER_ID    – unique user identifier
--    • TEAM       – team name (join key to EVENTS.TEAM)
--    • ROLE       – user's role within the team
--    • CREATED_AT – account creation timestamp
CREATE TABLE IF NOT EXISTS EAGLE_DB.MY_SCHEMA.USERS (
  USER_ID STRING,
  TEAM STRING,
  ROLE STRING,
  CREATED_AT TIMESTAMP_NTZ
);
