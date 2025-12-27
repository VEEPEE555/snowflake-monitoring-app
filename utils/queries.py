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


# ============================================================================
# COST TRACKING QUERIES
# ============================================================================

def get_cost_by_warehouse(days: int = 30) -> pd.DataFrame:
    """
    Fetch credit and cost breakdown by warehouse.
    Includes compute and cloud services credits.
    """
    query = f"""
    SELECT
        WAREHOUSE_NAME,
        DATE_TRUNC('day', START_TIME) as USAGE_DATE,
        SUM(CREDITS_USED) as TOTAL_CREDITS,
        SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS,
        SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICES_CREDITS
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    GROUP BY WAREHOUSE_NAME, DATE_TRUNC('day', START_TIME)
    ORDER BY USAGE_DATE DESC, WAREHOUSE_NAME
    """
    return execute_query(query)


def get_cost_by_user(days: int = 30) -> pd.DataFrame:
    """
    Fetch credit usage by user based on query execution.
    Aggregates credits from warehouse metering matched to user queries.
    """
    query = f"""
    WITH user_warehouse_usage AS (
        SELECT
            USER_NAME,
            WAREHOUSE_NAME,
            DATE_TRUNC('day', START_TIME) as USAGE_DATE,
            COUNT(*) as QUERY_COUNT,
            SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_HOURS
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND WAREHOUSE_NAME IS NOT NULL
        GROUP BY USER_NAME, WAREHOUSE_NAME, DATE_TRUNC('day', START_TIME)
    ),
    warehouse_credits AS (
        SELECT
            WAREHOUSE_NAME,
            DATE_TRUNC('day', START_TIME) as USAGE_DATE,
            SUM(CREDITS_USED) as CREDITS
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY WAREHOUSE_NAME, DATE_TRUNC('day', START_TIME)
    )
    SELECT
        u.USER_NAME,
        u.USAGE_DATE,
        SUM(u.QUERY_COUNT) as TOTAL_QUERIES,
        SUM(w.CREDITS) as ESTIMATED_CREDITS
    FROM user_warehouse_usage u
    LEFT JOIN warehouse_credits w
        ON u.WAREHOUSE_NAME = w.WAREHOUSE_NAME
        AND u.USAGE_DATE = w.USAGE_DATE
    GROUP BY u.USER_NAME, u.USAGE_DATE
    ORDER BY u.USAGE_DATE DESC, ESTIMATED_CREDITS DESC
    """
    return execute_query(query)


def get_cost_by_database(days: int = 30) -> pd.DataFrame:
    """
    Fetch credit usage and storage costs by database.
    """
    query = f"""
    WITH query_credits AS (
        SELECT
            DATABASE_NAME,
            DATE_TRUNC('day', START_TIME) as USAGE_DATE,
            COUNT(*) as QUERY_COUNT
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND DATABASE_NAME IS NOT NULL
        GROUP BY DATABASE_NAME, DATE_TRUNC('day', START_TIME)
    ),
    database_storage AS (
        SELECT
            DATABASE_NAME,
            USAGE_DATE,
            AVG(AVERAGE_DATABASE_BYTES) / (1024 * 1024 * 1024) as AVG_STORAGE_GB,
            AVG(AVERAGE_FAILSAFE_BYTES) / (1024 * 1024 * 1024) as AVG_FAILSAFE_GB
        FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
        WHERE USAGE_DATE >= DATEADD(day, -{days}, CURRENT_DATE())
        GROUP BY DATABASE_NAME, USAGE_DATE
    )
    SELECT
        COALESCE(q.DATABASE_NAME, s.DATABASE_NAME) as DATABASE_NAME,
        COALESCE(q.USAGE_DATE, s.USAGE_DATE) as USAGE_DATE,
        COALESCE(q.QUERY_COUNT, 0) as QUERY_COUNT,
        COALESCE(s.AVG_STORAGE_GB, 0) as AVG_STORAGE_GB,
        COALESCE(s.AVG_FAILSAFE_GB, 0) as AVG_FAILSAFE_GB
    FROM query_credits q
    FULL OUTER JOIN database_storage s
        ON q.DATABASE_NAME = s.DATABASE_NAME
        AND q.USAGE_DATE = s.USAGE_DATE
    ORDER BY USAGE_DATE DESC, DATABASE_NAME
    """
    return execute_query(query)


def get_storage_costs_detailed(days: int = 30) -> pd.DataFrame:
    """
    Fetch detailed storage costs including data, time-travel, and fail-safe.
    """
    query = f"""
    SELECT
        USAGE_DATE,
        STORAGE_BYTES / (1024 * 1024 * 1024) as STORAGE_GB,
        STAGE_BYTES / (1024 * 1024 * 1024) as STAGE_GB,
        FAILSAFE_BYTES / (1024 * 1024 * 1024) as FAILSAFE_GB,
        (STORAGE_BYTES + STAGE_BYTES + FAILSAFE_BYTES) / (1024 * 1024 * 1024) as TOTAL_STORAGE_GB
    FROM SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE
    WHERE USAGE_DATE >= DATEADD(day, -{days}, CURRENT_DATE())
    ORDER BY USAGE_DATE DESC
    """
    return execute_query(query)


def get_daily_credit_consumption(days: int = 30) -> pd.DataFrame:
    """
    Fetch daily credit consumption across all services.
    """
    query = f"""
    SELECT
        DATE_TRUNC('day', START_TIME) as USAGE_DATE,
        SUM(CREDITS_USED) as TOTAL_CREDITS,
        SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS,
        SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICES_CREDITS,
        COUNT(DISTINCT WAREHOUSE_NAME) as ACTIVE_WAREHOUSES
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    GROUP BY DATE_TRUNC('day', START_TIME)
    ORDER BY USAGE_DATE DESC
    """
    return execute_query(query)


def get_weekly_credit_consumption(weeks: int = 12) -> pd.DataFrame:
    """
    Fetch weekly credit consumption for trend analysis.
    """
    query = f"""
    SELECT
        DATE_TRUNC('week', START_TIME) as WEEK_START,
        SUM(CREDITS_USED) as TOTAL_CREDITS,
        SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS,
        SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICES_CREDITS,
        COUNT(DISTINCT WAREHOUSE_NAME) as ACTIVE_WAREHOUSES
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE START_TIME >= DATEADD(week, -{weeks}, CURRENT_TIMESTAMP())
    GROUP BY DATE_TRUNC('week', START_TIME)
    ORDER BY WEEK_START DESC
    """
    return execute_query(query)


def get_monthly_credit_consumption(months: int = 12) -> pd.DataFrame:
    """
    Fetch monthly credit consumption for long-term trend analysis.
    """
    query = f"""
    SELECT
        DATE_TRUNC('month', START_TIME) as MONTH_START,
        SUM(CREDITS_USED) as TOTAL_CREDITS,
        SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS,
        SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICES_CREDITS,
        COUNT(DISTINCT WAREHOUSE_NAME) as ACTIVE_WAREHOUSES,
        AVG(CREDITS_USED) as AVG_CREDITS_PER_HOUR
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE START_TIME >= DATEADD(month, -{months}, CURRENT_TIMESTAMP())
    GROUP BY DATE_TRUNC('month', START_TIME)
    ORDER BY MONTH_START DESC
    """
    return execute_query(query)


def get_cost_anomalies(days: int = 30, std_dev_threshold: float = 2.0) -> pd.DataFrame:
    """
    Detect cost anomalies based on statistical analysis.
    Returns days where credit usage exceeds threshold standard deviations from mean.
    """
    query = f"""
    WITH daily_credits AS (
        SELECT
            DATE_TRUNC('day', START_TIME) as USAGE_DATE,
            SUM(CREDITS_USED) as TOTAL_CREDITS
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY DATE_TRUNC('day', START_TIME)
    ),
    stats AS (
        SELECT
            AVG(TOTAL_CREDITS) as MEAN_CREDITS,
            STDDEV(TOTAL_CREDITS) as STDDEV_CREDITS
        FROM daily_credits
    )
    SELECT
        d.USAGE_DATE,
        d.TOTAL_CREDITS,
        s.MEAN_CREDITS,
        s.STDDEV_CREDITS,
        (d.TOTAL_CREDITS - s.MEAN_CREDITS) / NULLIF(s.STDDEV_CREDITS, 0) as Z_SCORE,
        CASE
            WHEN d.TOTAL_CREDITS > s.MEAN_CREDITS + ({std_dev_threshold} * s.STDDEV_CREDITS) THEN 'HIGH'
            WHEN d.TOTAL_CREDITS < s.MEAN_CREDITS - ({std_dev_threshold} * s.STDDEV_CREDITS) THEN 'LOW'
            ELSE 'NORMAL'
        END as ANOMALY_TYPE
    FROM daily_credits d
    CROSS JOIN stats s
    WHERE ABS((d.TOTAL_CREDITS - s.MEAN_CREDITS) / NULLIF(s.STDDEV_CREDITS, 0)) > {std_dev_threshold}
    ORDER BY d.USAGE_DATE DESC
    """
    return execute_query(query)


def get_warehouse_cost_trends(days: int = 30) -> pd.DataFrame:
    """
    Fetch warehouse-level cost trends for forecasting.
    """
    query = f"""
    SELECT
        WAREHOUSE_NAME,
        DATE_TRUNC('day', START_TIME) as USAGE_DATE,
        SUM(CREDITS_USED) as DAILY_CREDITS,
        AVG(SUM(CREDITS_USED)) OVER (
            PARTITION BY WAREHOUSE_NAME
            ORDER BY DATE_TRUNC('day', START_TIME)
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) as SEVEN_DAY_AVG,
        SUM(SUM(CREDITS_USED)) OVER (
            PARTITION BY WAREHOUSE_NAME
            ORDER BY DATE_TRUNC('day', START_TIME)
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) as CUMULATIVE_CREDITS
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    GROUP BY WAREHOUSE_NAME, DATE_TRUNC('day', START_TIME)
    ORDER BY WAREHOUSE_NAME, USAGE_DATE DESC
    """
    return execute_query(query)
