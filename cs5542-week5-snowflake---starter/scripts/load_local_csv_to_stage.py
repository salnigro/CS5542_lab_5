"""
load_local_csv_to_stage.py — Upload a local CSV to a Snowflake internal stage and COPY into a table
====================================================================================================
Usage:
    python scripts/load_local_csv_to_stage.py <local_csv_path> <target_table>

Example:
    python scripts/load_local_csv_to_stage.py data/events.csv EVENTS

Workflow:
    1. Creates (or replaces) a CSV file format and an internal stage.
    2. Uses PUT to upload the local CSV file to the stage.
    3. Uses COPY INTO to load the staged file into the target table.

References
----------
- PUT command:       https://docs.snowflake.com/en/sql-reference/sql/put
- COPY INTO <table>: https://docs.snowflake.com/en/sql-reference/sql/copy-into-table
- Internal stages:   https://docs.snowflake.com/en/user-guide/data-load-local-file-system-create-stage
"""

import os
import sys
import time
from sf_connect import get_conn

def run(sql: str):
    """Execute a single SQL statement and return results (if any)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            try:
                return cur.fetchall()
            except Exception:
                return None

def main():
    """CLI entry-point: validate args → create stage → PUT file → COPY INTO table."""
    if len(sys.argv) < 3:
        print("Usage: python scripts/load_local_csv_to_stage.py <local_csv_path> <target_table>")
        print("Example: python scripts/load_local_csv_to_stage.py data/events.csv EVENTS")
        sys.exit(1)

    local_path = sys.argv[1]
    target_table = sys.argv[2].upper()

    if not os.path.exists(local_path):
        raise FileNotFoundError(local_path)

    stage_name = "CS5542_STAGE"
    file_format = "CS5542_CSV_FMT"

    # Use a SINGLE connection for all operations.
    # This is important for externalbrowser auth — otherwise each get_conn()
    # call opens a new browser popup asking you to log in.
    with get_conn() as conn:
        cur = conn.cursor()

        # Step 0: Set up database context — create objects if they don't exist
        wh = os.getenv("SNOWFLAKE_WAREHOUSE", "INSTRUCTOR_WH")
        db = os.getenv("SNOWFLAKE_DATABASE", "INSTRUCTOR2_DB")
        schema = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")

        print("Setting up database context...")
        cur.execute(f"CREATE WAREHOUSE IF NOT EXISTS {wh} WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE;")
        cur.execute(f"USE WAREHOUSE {wh};")
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {db};")
        cur.execute(f"USE DATABASE {db};")
        cur.execute(f"USE SCHEMA {schema};")

        # Create tables if they don't exist
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {db}.{schema}.EVENTS (
          EVENT_ID STRING, EVENT_TIME TIMESTAMP_NTZ,
          TEAM STRING, CATEGORY STRING, VALUE FLOAT
        );""")
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {db}.{schema}.USERS (
          USER_ID STRING, TEAM STRING, ROLE STRING, CREATED_AT TIMESTAMP_NTZ
        );""")

        # Step 1: Create file format + internal stage (idempotent — safe to re-run)
        # Docs: https://docs.snowflake.com/en/sql-reference/sql/create-file-format
        print("Creating file format and stage...")
        cur.execute(f"""
        CREATE OR REPLACE FILE FORMAT {file_format}
          TYPE = CSV
          SKIP_HEADER = 1
          FIELD_OPTIONALLY_ENCLOSED_BY = '"'
          NULL_IF = ('', 'NULL', 'null');
        """)

        cur.execute(f"CREATE OR REPLACE STAGE {stage_name} FILE_FORMAT = {file_format};")

        # Step 2: PUT the local CSV onto the Snowflake internal stage
        # The file is automatically gzip-compressed during upload (AUTO_COMPRESS=TRUE).
        put_sql = f"PUT file://{os.path.abspath(local_path)} @{stage_name} AUTO_COMPRESS=TRUE OVERWRITE=TRUE;"
        print(put_sql)
        cur.execute(put_sql)
        print(cur.fetchall())

        # Step 3: COPY the staged (compressed) file into the target table.
        # ON_ERROR='CONTINUE' skips bad rows instead of aborting the whole load.
        filename = os.path.basename(local_path)
        copy_sql = f"""
        COPY INTO {target_table}
        FROM @{stage_name}/{filename}.gz
        ON_ERROR='CONTINUE';
        """
        t0 = time.time()
        cur.execute(copy_sql)
        res = cur.fetchall()
        dt_ms = int((time.time() - t0) * 1000)

        print("COPY result:", res)
        print(f"Load latency: {dt_ms} ms")

        cur.close()

if __name__ == "__main__":
    main()
