from retrieve import Retriever
from sf_connect import get_conn
import pandas as pd

def run_sql(sql):
    with get_conn() as conn:
        return pd.read_sql(sql, conn)

def hybrid_query(user_query):
    retriever = Retriever()
    retrieved_docs = retriever.search(user_query, k=5)

    sql = """
    SELECT DESCRIPTION,
           SUM(QUANTITY) AS TOTAL_SOLD
    FROM ONLINE_RETAIL
    GROUP BY DESCRIPTION
    ORDER BY TOTAL_SOLD DESC
    LIMIT 10;
    """

    sql_results = run_sql(sql)

    return {
        "retrieved_text": retrieved_docs,
        "sql_results": sql_results.to_dict("records")
    }

if __name__ == "__main__":
    result = hybrid_query("What products are trending?")
    print(result)