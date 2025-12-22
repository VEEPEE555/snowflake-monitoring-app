import streamlit as st
import snowflake.connector
from typing import Optional
import pandas as pd


@st.cache_resource
def get_snowflake_connection():
    """
    Create and cache Snowflake connection using Streamlit secrets.
    """
    try:
        conn = snowflake.connector.connect(
            user=st.secrets["snowflake"]["user"],
            password=st.secrets["snowflake"]["password"],
            account=st.secrets["snowflake"]["account"],
            warehouse=st.secrets["snowflake"]["warehouse"],
            role=st.secrets["snowflake"]["role"]
        )
        return conn
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {str(e)}")
        return None


def execute_query(query: str, params: Optional[dict] = None) -> pd.DataFrame:
    """
    Execute a query and return results as a DataFrame.
    """
    conn = get_snowflake_connection()
    if conn is None:
        return pd.DataFrame()

    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # Fetch results and column names
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        cursor.close()

        return pd.DataFrame(results, columns=columns)
    except Exception as e:
        st.error(f"Query execution failed: {str(e)}")
        return pd.DataFrame()
