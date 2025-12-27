import pandas as pd
from datetime import datetime, timedelta
from .snowflake_connector import execute_query


def get_query_history(hours: int = 24) -> pd.DataFrame:
    """
    Fetch query history from Snowflake QUERY_HISTORY view.
    """
    query = f"""
    SELECT
        QUERY_ID,
        QUERY_TEXT,
        USER_NAME,
        ROLE_NAME,
        WAREHOUSE_NAME,
        WAREHOUSE_SIZE,
        EXECUTION_STATUS,
        TOTAL_ELAPSED_TIME / 1000 as EXECUTION_TIME_SECONDS,
        BYTES_SCANNED,
        ROWS_PRODUCED,
        START_TIME,
        END_TIME,
        ERROR_CODE,
        ERROR_MESSAGE
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    ORDER BY START_TIME DESC
    LIMIT 1000
    """
    return execute_query(query)


def get_warehouse_load(hours: int = 24) -> pd.DataFrame:
    """
    Fetch warehouse load and credit usage.
    """
    query = f"""
    SELECT
        WAREHOUSE_NAME,
        DATE_TRUNC('hour', START_TIME) as HOUR,
        COUNT(*) as QUERY_COUNT,
        AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_EXECUTION_TIME_SECONDS,
        SUM(TOTAL_ELAPSED_TIME) / 1000 as TOTAL_EXECUTION_TIME_SECONDS
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    AND WAREHOUSE_NAME IS NOT NULL
    GROUP BY WAREHOUSE_NAME, DATE_TRUNC('hour', START_TIME)
    ORDER BY HOUR DESC
    """
    return execute_query(query)


def get_login_history(hours: int = 24) -> pd.DataFrame:
    """
    Fetch login history and authentication events.
    """
    query = f"""
    SELECT
        EVENT_TIMESTAMP,
        USER_NAME,
        CLIENT_IP,
        REPORTED_CLIENT_TYPE,
        FIRST_AUTHENTICATION_FACTOR,
        IS_SUCCESS,
        ERROR_CODE,
        ERROR_MESSAGE
    FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
    WHERE EVENT_TIMESTAMP >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    ORDER BY EVENT_TIMESTAMP DESC
    LIMIT 1000
    """
    return execute_query(query)


def get_storage_usage() -> pd.DataFrame:
    """
    Fetch storage usage over time.
    """
    query = """
    SELECT
        USAGE_DATE,
        STORAGE_BYTES / (1024 * 1024 * 1024) as STORAGE_GB,
        STAGE_BYTES / (1024 * 1024 * 1024) as STAGE_GB,
        FAILSAFE_BYTES / (1024 * 1024 * 1024) as FAILSAFE_GB
    FROM SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE
    WHERE USAGE_DATE >= DATEADD(day, -30, CURRENT_DATE())
    ORDER BY USAGE_DATE DESC
    """
    return execute_query(query)


def get_access_history(hours: int = 24) -> pd.DataFrame:
    """
    Fetch data access history and object usage.
    """
    query = f"""
    SELECT
        QUERY_ID,
        QUERY_START_TIME,
        USER_NAME,
        DIRECT_OBJECTS_ACCESSED,
        BASE_OBJECTS_ACCESSED,
        OBJECTS_MODIFIED
    FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY
    WHERE QUERY_START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    ORDER BY QUERY_START_TIME DESC
    LIMIT 500
    """
    return execute_query(query)


def get_warehouse_metering(days: int = 7) -> pd.DataFrame:
    """
    Fetch warehouse credit usage and metering.
    """
    query = f"""
    SELECT
        START_TIME,
        END_TIME,
        WAREHOUSE_NAME,
        CREDITS_USED,
        CREDITS_USED_COMPUTE,
        CREDITS_USED_CLOUD_SERVICES
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    ORDER BY START_TIME DESC
    """
    return execute_query(query)


def get_task_history(hours: int = 24) -> pd.DataFrame:
    """
    Fetch Snowflake task execution history.
    """
    query = f"""
    SELECT
        NAME as TASK_NAME,
        DATABASE_NAME,
        SCHEMA_NAME,
        STATE,
        SCHEDULED_TIME,
        COMPLETED_TIME,
        ERROR_CODE,
        ERROR_MESSAGE,
        QUERY_ID
    FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY
    WHERE SCHEDULED_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    ORDER BY SCHEDULED_TIME DESC
    LIMIT 500
    """
    return execute_query(query)


def get_pipe_usage(hours: int = 24) -> pd.DataFrame:
    """
    Fetch Snowpipe usage and statistics.
    """
    query = f"""
    SELECT
        PIPE_NAME,
        PIPE_RECEIVED_TIME,
        FILE_NAME,
        ROW_COUNT,
        ROW_PARSED,
        STATUS,
        ERROR_MESSAGE
    FROM SNOWFLAKE.ACCOUNT_USAGE.COPY_HISTORY
    WHERE PIPE_RECEIVED_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    ORDER BY PIPE_RECEIVED_TIME DESC
    LIMIT 500
    """
    return execute_query(query)


def get_detailed_query_performance(hours: int = 24) -> pd.DataFrame:
    """
    Fetch detailed query performance metrics including:
    - Execution time breakdowns (compilation, execution, queue wait times)
    - Percentile calculations for performance analysis
    - Concurrency tracking
    """
    query = f"""
    SELECT
        QUERY_ID,
        QUERY_TEXT,
        USER_NAME,
        ROLE_NAME,
        WAREHOUSE_NAME,
        WAREHOUSE_SIZE,
        EXECUTION_STATUS,
        START_TIME,
        END_TIME,
        -- Time metrics in seconds
        TOTAL_ELAPSED_TIME / 1000 as TOTAL_ELAPSED_TIME_SECONDS,
        COMPILATION_TIME / 1000 as COMPILATION_TIME_SECONDS,
        EXECUTION_TIME / 1000 as EXECUTION_TIME_SECONDS,
        QUEUED_PROVISIONING_TIME / 1000 as QUEUED_PROVISIONING_TIME_SECONDS,
        QUEUED_REPAIR_TIME / 1000 as QUEUED_REPAIR_TIME_SECONDS,
        QUEUED_OVERLOAD_TIME / 1000 as QUEUED_OVERLOAD_TIME_SECONDS,
        -- Additional performance metrics
        BYTES_SCANNED,
        BYTES_WRITTEN,
        BYTES_SPILLED_TO_LOCAL_STORAGE,
        BYTES_SPILLED_TO_REMOTE_STORAGE,
        ROWS_PRODUCED,
        ROWS_INSERTED,
        ROWS_UPDATED,
        ROWS_DELETED,
        PARTITIONS_SCANNED,
        PARTITIONS_TOTAL,
        -- Query characteristics
        QUERY_TYPE,
        QUERY_TAG,
        -- Resource usage
        CREDITS_USED_CLOUD_SERVICES,
        -- Error tracking
        ERROR_CODE,
        ERROR_MESSAGE
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    AND EXECUTION_STATUS IN ('SUCCESS', 'FAILED', 'INCIDENT')
    ORDER BY START_TIME DESC
    LIMIT 5000
    """
    return execute_query(query)


def get_query_concurrency(hours: int = 24) -> pd.DataFrame:
    """
    Fetch query concurrency data by analyzing overlapping query execution times.
    """
    query = f"""
    SELECT
        DATE_TRUNC('minute', START_TIME) as TIME_BUCKET,
        WAREHOUSE_NAME,
        COUNT(DISTINCT QUERY_ID) as CONCURRENT_QUERIES,
        AVG(EXECUTION_TIME / 1000) as AVG_EXECUTION_TIME_SECONDS
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    AND WAREHOUSE_NAME IS NOT NULL
    AND EXECUTION_STATUS = 'SUCCESS'
    GROUP BY DATE_TRUNC('minute', START_TIME), WAREHOUSE_NAME
    ORDER BY TIME_BUCKET DESC
    """
    return execute_query(query)
