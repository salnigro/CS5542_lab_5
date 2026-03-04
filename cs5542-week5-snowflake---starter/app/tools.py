import os
import sys
import pandas as pd
from typing import Dict, Any, List

# Add parent directory for module resolution if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.sf_connect import get_conn
from scripts.retrieve import Retriever
from langchain.tools import tool

@tool
def search_financial_news(query: str) -> str:
    """
    Search the local FAISS index for unstructured knowledge regarding financial news, retail products, or order statuses.
    Use this tool when the user asks qualitative questions, asks for sentiment analysis, or seeks context about an event or product.

    Args:
        query (str): The specific topic, product name, or company to search for.

    Returns:
        str: A concatenated string of the top semantically retrieved text chunks containing the context.
    """
    try:
        retriever = Retriever()
        results = retriever.search(query, k=3)
        if not results:
            return f"No relevant information found for: {query}"
        
        context = "\n---\n".join([f"Source: {r['source']}\nContent: {r['text']}" for r in results])
        return f"Semantic Search Results:\n{context}"
    except Exception as e:
        return f"Error executing FAISS search: {str(e)}"

@tool
def query_snowflake(sql_query: str) -> str:
    """
    Execute a read-only SELECT query against the Snowflake database.
    Use this tool when the user asks for quantitative analytics, statistics, counting rows, summing revenue, finding specific records, or generating tabular data.
    
    The database contains the following tables:
    - USERS (USER_ID, TEAM, ROLE, CREATED_AT)
    - EVENTS (EVENT_ID, EVENT_TIME, TEAM, CATEGORY, VALUE)
    - ONLINE_RETAIL (Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country)
    - OLIST_ORDERS (order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date)
    
    Args:
        sql_query (str): The fully formed, valid Snowflake SQL SELECT query.

    Returns:
        str: Markdown formatted table of the query results, or an error message if the query fails.
    """
    try:
        if not sql_query.strip().upper().startswith("SELECT"):
            return "Error: Only SELECT queries are permitted for safety."

        from app.streamlit_app import get_cached_conn
        conn = get_cached_conn()
        df = pd.read_sql(sql_query, conn)
        
        if df.empty:
            return "Query executed successfully, but returned 0 rows."
        
        # Format dataframe as markdown table string to return to LLM
        return df.to_markdown(index=False)
            
    except Exception as e:
        return f"Database Error executing query '{sql_query}': {str(e)}"

@tool
def calculate_metrics(values: List[float], operation: str) -> str:
    """
    Perform a statistical calculation (sum, average, min, max) on a list of numeric values. 
    Use this if the database query returns raw values and the user requires a mathematical aggregate that wasn't already computed in SQL.

    Args:
        values (List[float]): A list of numerical values.
        operation (str): The operation to perform ('sum', 'avg', 'average', 'min', 'max').

    Returns:
        str: The calculated result.
    """
    try:
        if not values:
            return "Error: List of values is empty."
        
        op = operation.lower()
        if op == "sum":
            res = sum(values)
        elif op in ["avg", "average"]:
            res = sum(values) / len(values)
        elif op == "min":
            res = min(values)
        elif op == "max":
            res = max(values)
        else:
            return f"Error: Unsupported operation '{operation}'"
        
        return f"The {operation} of the provided values is {res:.2f}"
    except Exception as e:
        return f"Error calculating metrics: {str(e)}"
