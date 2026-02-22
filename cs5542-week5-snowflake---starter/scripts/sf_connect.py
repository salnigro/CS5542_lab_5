"""
sf_connect.py — Snowflake connection helper
============================================
Centralises the Snowflake connection so every script/app
reads credentials from a single .env file.

References
----------
- Snowflake Python Connector docs:
  https://docs.snowflake.com/en/developer-guide/python-connector/python-connector
- snowflake-connector-python on PyPI:
  https://pypi.org/project/snowflake-connector-python/
- python-dotenv (for .env loading):
  https://pypi.org/project/python-dotenv/
"""

import os
import snowflake.connector
from dotenv import load_dotenv

# Load environment variables from the .env file in the project root.
# Make sure you have copied .env.example → .env and filled in your credentials.
load_dotenv()

def get_conn():
    """
    Create and return a new Snowflake connection using credentials
    stored in environment variables (loaded from .env).

    Required env vars:
        SNOWFLAKE_ACCOUNT   – e.g. "xy12345.us-east-1"
        SNOWFLAKE_USER      – your Snowflake login username
        SNOWFLAKE_PASSWORD   – password (omit if using SSO/externalbrowser)
        SNOWFLAKE_WAREHOUSE – compute warehouse, e.g. "COMPUTE_WH"
        SNOWFLAKE_DATABASE  – target database, e.g. "CS5542_WEEK5"
        SNOWFLAKE_SCHEMA    – target schema, e.g. "PUBLIC"

    Optional env vars:
        SNOWFLAKE_ROLE          – Snowflake role (default: ACCOUNTADMIN)
        SNOWFLAKE_AUTHENTICATOR – set to "externalbrowser" for SSO

    Returns:
        snowflake.connector.SnowflakeConnection

    Raises:
        RuntimeError: if any required env var is missing.
    """
    # ---- 1. Validate that all required env vars are present ----
    # Password is NOT required when using externalbrowser (SSO) authentication.
    authenticator = os.getenv("SNOWFLAKE_AUTHENTICATOR", "").lower()
    using_sso = authenticator == "externalbrowser"

    required = [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER",
        "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA"
    ]
    if not using_sso:
        required.append("SNOWFLAKE_PASSWORD")

    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing env vars: {missing}. Fill .env from .env.example")

    # ---- 2. Build connection keyword arguments ----
    conn_kwargs = dict(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        role=os.getenv("SNOWFLAKE_ROLE", None),       # optional; defaults to user's default role
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )

    # ---- 3. Handle authenticator (SSO / MFA / default) ----
    # Supported values:
    #   • (empty)                  – plain username + password
    #   • externalbrowser          – opens a browser for SSO (no password needed)
    #   • username_password_mfa    – password + MFA with TOTP passcode
    # See: https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-connect
    authenticator = os.getenv("SNOWFLAKE_AUTHENTICATOR")
    if authenticator:
        conn_kwargs["authenticator"] = authenticator
        # Only remove password for externalbrowser (SSO); MFA still needs it
        if authenticator.lower() == "externalbrowser":
            conn_kwargs.pop("password", None)
        elif authenticator.lower() == "username_password_mfa":
            # Prompt the user for their 6-digit TOTP code from their authenticator app
            passcode = input("Enter your MFA TOTP code (6-digit code from authenticator app): ").strip()
            if passcode:
                conn_kwargs["passcode"] = passcode

    # ---- 4. Open the connection (filter out None/empty values) ----
    return snowflake.connector.connect(**{k: v for k, v in conn_kwargs.items() if v})
