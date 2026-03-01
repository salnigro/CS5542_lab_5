import os
import sys
import time
from sf_connect import get_conn


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/load_olist.py <path_to_csv>")
        sys.exit(1)

    local_path = sys.argv[1]

    if not os.path.exists(local_path):
        raise FileNotFoundError(local_path)

    stage_name = "CS5542_STAGE"
    file_format = "CS5542_CSV_FMT"
    table_name = "OLIST_CUSTOMERS"

    with get_conn() as conn:
        cur = conn.cursor()

        # Create table structure (adjust based on dataset)
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            customer_id STRING,
            customer_unique_id STRING,
            customer_zip_code_prefix STRING,
            customer_city STRING,
            customer_state STRING
        );
        """)

        # Create file format
        cur.execute(f"""
        CREATE OR REPLACE FILE FORMAT {file_format}
        TYPE=CSV SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='"'
        NULL_IF=('','NULL');
        """)

        # Create stage
        cur.execute(f"CREATE OR REPLACE STAGE {stage_name} FILE_FORMAT={file_format};")

        # Upload file
        cur.execute(f"PUT file://{os.path.abspath(local_path)} @{stage_name} AUTO_COMPRESS=TRUE OVERWRITE=TRUE;")

        filename = os.path.basename(local_path)

        copy_sql = f"""
        COPY INTO {table_name}
        FROM @{stage_name}/{filename}.gz
        ON_ERROR='CONTINUE';
        """

        t0 = time.time()
        cur.execute(copy_sql)
        result = cur.fetchall()
        dt = int((time.time() - t0) * 1000)

        print("COPY RESULT:", result)
        print(f"Load latency: {dt} ms")

        cur.close()


if __name__ == "__main__":
    main()