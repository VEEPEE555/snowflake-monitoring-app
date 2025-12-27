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


def get_warehouse_utilization(hours: int = 24) -> pd.DataFrame:
    """
    Calculate warehouse utilization percentage based on query execution times
    and warehouse uptime.
    """
    query = f"""
    WITH warehouse_stats AS (
        SELECT
            WAREHOUSE_NAME,
            DATE_TRUNC('hour', START_TIME) as HOUR,
            SUM(EXECUTION_TIME) / 1000 as TOTAL_EXECUTION_SECONDS,
            COUNT(DISTINCT QUERY_ID) as QUERY_COUNT,
            -- Approximate warehouse running time (3600 seconds per hour)
            3600 as AVAILABLE_SECONDS
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
        AND WAREHOUSE_NAME IS NOT NULL
        GROUP BY WAREHOUSE_NAME, DATE_TRUNC('hour', START_TIME)
    )
    SELECT
        WAREHOUSE_NAME,
        HOUR,
        TOTAL_EXECUTION_SECONDS,
        QUERY_COUNT,
        AVAILABLE_SECONDS,
        ROUND((TOTAL_EXECUTION_SECONDS / AVAILABLE_SECONDS) * 100, 2) as UTILIZATION_PERCENTAGE
    FROM warehouse_stats
    ORDER BY HOUR DESC, WAREHOUSE_NAME
    """
    return execute_query(query)


def get_warehouse_state_changes(hours: int = 24) -> pd.DataFrame:
    """
    Fetch warehouse state changes (auto-suspend/resume patterns).
    """
    query = f"""
    SELECT
        WAREHOUSE_NAME,
        START_TIME,
        END_TIME,
        WAREHOUSE_ID,
        CLUSTER_NUMBER,
        CREDITS_USED,
        CREDITS_USED_COMPUTE,
        CREDITS_USED_CLOUD_SERVICES
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    ORDER BY START_TIME DESC
    """
    return execute_query(query)


def get_warehouse_events(hours: int = 168) -> pd.DataFrame:
    """
    Fetch warehouse load history events including suspend/resume events.
    """
    query = f"""
    SELECT
        WAREHOUSE_NAME,
        START_TIME,
        END_TIME,
        WAREHOUSE_ID,
        CLUSTER_NUMBER,
        AVG_RUNNING,
        AVG_QUEUED_LOAD,
        AVG_QUEUED_PROVISIONING,
        AVG_BLOCKED
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
    WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    ORDER BY START_TIME DESC
    LIMIT 5000
    """
    return execute_query(query)


def get_warehouse_queue_depth(hours: int = 24) -> pd.DataFrame:
    """
    Analyze warehouse queuing patterns and depth.
    """
    query = f"""
    SELECT
        WAREHOUSE_NAME,
        DATE_TRUNC('minute', START_TIME) as TIME_BUCKET,
        COUNT(*) as TOTAL_QUERIES,
        SUM(CASE WHEN QUEUED_OVERLOAD_TIME > 0 THEN 1 ELSE 0 END) as QUEUED_OVERLOAD_COUNT,
        SUM(CASE WHEN QUEUED_PROVISIONING_TIME > 0 THEN 1 ELSE 0 END) as QUEUED_PROVISIONING_COUNT,
        SUM(CASE WHEN QUEUED_REPAIR_TIME > 0 THEN 1 ELSE 0 END) as QUEUED_REPAIR_COUNT,
        AVG(QUEUED_OVERLOAD_TIME) / 1000 as AVG_QUEUE_OVERLOAD_SECONDS,
        AVG(QUEUED_PROVISIONING_TIME) / 1000 as AVG_QUEUE_PROVISIONING_SECONDS,
        AVG(QUEUED_REPAIR_TIME) / 1000 as AVG_QUEUE_REPAIR_SECONDS,
        MAX(QUEUED_OVERLOAD_TIME) / 1000 as MAX_QUEUE_OVERLOAD_SECONDS,
        MAX(QUEUED_PROVISIONING_TIME) / 1000 as MAX_QUEUE_PROVISIONING_SECONDS
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    AND WAREHOUSE_NAME IS NOT NULL
    GROUP BY WAREHOUSE_NAME, DATE_TRUNC('minute', START_TIME)
    ORDER BY TIME_BUCKET DESC
    """
    return execute_query(query)


def get_multi_warehouse_load_distribution(hours: int = 24) -> pd.DataFrame:
    """
    Analyze load distribution across multiple warehouses.
    """
    query = f"""
    WITH warehouse_metrics AS (
        SELECT
            WAREHOUSE_NAME,
            WAREHOUSE_SIZE,
            DATE_TRUNC('hour', START_TIME) as HOUR,
            COUNT(*) as QUERY_COUNT,
            AVG(EXECUTION_TIME / 1000) as AVG_EXECUTION_TIME_SECONDS,
            SUM(EXECUTION_TIME / 1000) as TOTAL_EXECUTION_TIME_SECONDS,
            AVG(BYTES_SCANNED) as AVG_BYTES_SCANNED,
            SUM(BYTES_SCANNED) as TOTAL_BYTES_SCANNED,
            COUNT(DISTINCT USER_NAME) as UNIQUE_USERS
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
        AND WAREHOUSE_NAME IS NOT NULL
        AND EXECUTION_STATUS = 'SUCCESS'
        GROUP BY WAREHOUSE_NAME, WAREHOUSE_SIZE, DATE_TRUNC('hour', START_TIME)
    )
    SELECT
        WAREHOUSE_NAME,
        WAREHOUSE_SIZE,
        HOUR,
        QUERY_COUNT,
        AVG_EXECUTION_TIME_SECONDS,
        TOTAL_EXECUTION_TIME_SECONDS,
        AVG_BYTES_SCANNED,
        TOTAL_BYTES_SCANNED,
        UNIQUE_USERS,
        -- Calculate percentage of total queries
        ROUND(QUERY_COUNT * 100.0 / SUM(QUERY_COUNT) OVER (PARTITION BY HOUR), 2) as QUERY_PERCENTAGE
    FROM warehouse_metrics
    ORDER BY HOUR DESC, QUERY_COUNT DESC
    """
    return execute_query(query)


def get_warehouse_credit_breakdown(days: int = 7) -> pd.DataFrame:
    """
    Detailed breakdown of warehouse credit consumption with hourly granularity.
    """
    query = f"""
    SELECT
        WAREHOUSE_NAME,
        DATE_TRUNC('hour', START_TIME) as HOUR,
        SUM(CREDITS_USED) as TOTAL_CREDITS,
        SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS,
        SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICES_CREDITS,
        COUNT(DISTINCT WAREHOUSE_ID) as WAREHOUSE_COUNT,
        AVG(CREDITS_USED) as AVG_CREDITS_PER_INTERVAL
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    GROUP BY WAREHOUSE_NAME, DATE_TRUNC('hour', START_TIME)
    ORDER BY HOUR DESC
    """
    return execute_query(query)
