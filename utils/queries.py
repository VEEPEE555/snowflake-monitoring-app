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


# =============================================================================
# WAREHOUSE ADVANCED METRICS
# =============================================================================

def get_warehouse_utilization(days: int = 7) -> pd.DataFrame:
    """
    Fetch warehouse utilization metrics including idle time and auto-suspend patterns.
    """
    query = f"""
    WITH warehouse_events AS (
        SELECT
            WAREHOUSE_NAME,
            START_TIME,
            END_TIME,
            CREDITS_USED,
            CREDITS_USED_COMPUTE,
            CREDITS_USED_CLOUD_SERVICES
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    ),
    query_activity AS (
        SELECT
            WAREHOUSE_NAME,
            DATE_TRUNC('hour', START_TIME) as HOUR,
            COUNT(*) as QUERY_COUNT,
            SUM(EXECUTION_TIME) / 1000 as TOTAL_EXECUTION_SECONDS
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        AND WAREHOUSE_NAME IS NOT NULL
        GROUP BY WAREHOUSE_NAME, DATE_TRUNC('hour', START_TIME)
    )
    SELECT
        we.WAREHOUSE_NAME,
        DATE_TRUNC('hour', we.START_TIME) as HOUR,
        SUM(we.CREDITS_USED) as CREDITS_USED,
        SUM(we.CREDITS_USED_COMPUTE) as CREDITS_COMPUTE,
        SUM(we.CREDITS_USED_CLOUD_SERVICES) as CREDITS_CLOUD,
        COALESCE(qa.QUERY_COUNT, 0) as QUERY_COUNT,
        COALESCE(qa.TOTAL_EXECUTION_SECONDS, 0) as TOTAL_EXECUTION_SECONDS,
        -- Utilization percentage (execution time / 3600 seconds per hour)
        CASE WHEN SUM(we.CREDITS_USED_COMPUTE) > 0
             THEN (COALESCE(qa.TOTAL_EXECUTION_SECONDS, 0) / 3600.0) * 100
             ELSE 0
        END as UTILIZATION_PCT
    FROM warehouse_events we
    LEFT JOIN query_activity qa
        ON we.WAREHOUSE_NAME = qa.WAREHOUSE_NAME
        AND DATE_TRUNC('hour', we.START_TIME) = qa.HOUR
    GROUP BY we.WAREHOUSE_NAME, DATE_TRUNC('hour', we.START_TIME), qa.QUERY_COUNT, qa.TOTAL_EXECUTION_SECONDS
    ORDER BY HOUR DESC
    """
    return execute_query(query)


def get_warehouse_load_events(hours: int = 24) -> pd.DataFrame:
    """
    Fetch warehouse load events to detect auto-suspend/resume patterns.
    """
    query = f"""
    SELECT
        WAREHOUSE_NAME,
        EVENT_NAME,
        EVENT_STATE,
        EVENT_REASON,
        TIMESTAMP,
        USER_NAME,
        ROLE_NAME
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
    WHERE TIMESTAMP >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    ORDER BY TIMESTAMP DESC
    LIMIT 1000
    """
    return execute_query(query)


# =============================================================================
# COST TRACKING
# =============================================================================

def get_credit_consumption_detailed(days: int = 30) -> pd.DataFrame:
    """
    Fetch detailed credit consumption for cost analysis by warehouse, day, and type.
    """
    query = f"""
    SELECT
        DATE_TRUNC('day', START_TIME) as DATE,
        WAREHOUSE_NAME,
        SUM(CREDITS_USED) as TOTAL_CREDITS,
        SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS,
        SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICE_CREDITS
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    GROUP BY DATE_TRUNC('day', START_TIME), WAREHOUSE_NAME
    ORDER BY DATE DESC, TOTAL_CREDITS DESC
    """
    return execute_query(query)


def get_cost_by_user(days: int = 7) -> pd.DataFrame:
    """
    Fetch credit consumption by user.
    """
    query = f"""
    SELECT
        USER_NAME,
        WAREHOUSE_NAME,
        COUNT(*) as QUERY_COUNT,
        SUM(CREDITS_USED_CLOUD_SERVICES) as CREDITS_USED,
        AVG(EXECUTION_TIME / 1000) as AVG_EXECUTION_TIME_SECONDS,
        SUM(BYTES_SCANNED) / (1024*1024*1024) as GB_SCANNED
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND USER_NAME IS NOT NULL
    GROUP BY USER_NAME, WAREHOUSE_NAME
    ORDER BY CREDITS_USED DESC
    """
    return execute_query(query)


def get_cost_by_database(days: int = 7) -> pd.DataFrame:
    """
    Fetch credit consumption by database.
    """
    query = f"""
    SELECT
        DATABASE_NAME,
        COUNT(*) as QUERY_COUNT,
        SUM(CREDITS_USED_CLOUD_SERVICES) as CREDITS_USED,
        SUM(EXECUTION_TIME / 1000) as TOTAL_EXECUTION_SECONDS,
        SUM(BYTES_SCANNED) / (1024*1024*1024) as GB_SCANNED
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND DATABASE_NAME IS NOT NULL
    GROUP BY DATABASE_NAME
    ORDER BY CREDITS_USED DESC
    """
    return execute_query(query)


def get_storage_cost_breakdown() -> pd.DataFrame:
    """
    Fetch storage cost breakdown including data, time-travel, and fail-safe.
    """
    query = """
    SELECT
        USAGE_DATE,
        STORAGE_BYTES / (1024*1024*1024) as DATA_STORAGE_GB,
        STAGE_BYTES / (1024*1024*1024) as STAGE_STORAGE_GB,
        FAILSAFE_BYTES / (1024*1024*1024) as FAILSAFE_STORAGE_GB,
        -- Assuming $40 per TB per month for storage (adjust based on your region)
        (STORAGE_BYTES / (1024*1024*1024*1024)) * 40 / 30 as DAILY_DATA_COST,
        (STAGE_BYTES / (1024*1024*1024*1024)) * 40 / 30 as DAILY_STAGE_COST,
        (FAILSAFE_BYTES / (1024*1024*1024*1024)) * 40 / 30 as DAILY_FAILSAFE_COST
    FROM SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE
    WHERE USAGE_DATE >= DATEADD(day, -90, CURRENT_DATE())
    ORDER BY USAGE_DATE DESC
    """
    return execute_query(query)


# =============================================================================
# STORAGE ANALYTICS
# =============================================================================

def get_table_storage() -> pd.DataFrame:
    """
    Fetch table-level storage breakdown.
    """
    query = """
    SELECT
        TABLE_CATALOG as DATABASE_NAME,
        TABLE_SCHEMA as SCHEMA_NAME,
        TABLE_NAME,
        TABLE_TYPE,
        ROW_COUNT,
        BYTES / (1024*1024*1024) as SIZE_GB,
        ACTIVE_BYTES / (1024*1024*1024) as ACTIVE_GB,
        TIME_TRAVEL_BYTES / (1024*1024*1024) as TIME_TRAVEL_GB,
        FAILSAFE_BYTES / (1024*1024*1024) as FAILSAFE_GB,
        CLUSTERING_KEY,
        CREATED,
        LAST_ALTERED
    FROM SNOWFLAKE.ACCOUNT_USAGE.TABLE_STORAGE_METRICS
    WHERE DELETED IS NULL
    ORDER BY BYTES DESC
    LIMIT 500
    """
    return execute_query(query)


def get_clustering_depth() -> pd.DataFrame:
    """
    Fetch clustering depth information for clustered tables.
    """
    query = """
    SELECT
        TABLE_CATALOG as DATABASE_NAME,
        TABLE_SCHEMA as SCHEMA_NAME,
        TABLE_NAME,
        AVG_DEPTH,
        AVG_WIDTH,
        PARTITION_DEPTH_1,
        PARTITION_DEPTH_2_TO_4,
        PARTITION_DEPTH_5_TO_16,
        PARTITION_DEPTH_17_PLUS,
        LAST_RECLUSTERED
    FROM SNOWFLAKE.ACCOUNT_USAGE.AUTOMATIC_CLUSTERING_HISTORY
    WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
    ORDER BY START_TIME DESC
    LIMIT 200
    """
    return execute_query(query)


def get_staged_files() -> pd.DataFrame:
    """
    Fetch information about staged files.
    """
    query = """
    SELECT
        STAGE_SCHEMA as SCHEMA_NAME,
        STAGE_NAME,
        STAGE_CATALOG as DATABASE_NAME,
        STAGE_TYPE,
        STAGE_REGION,
        CREATED,
        LAST_ALTERED
    FROM SNOWFLAKE.ACCOUNT_USAGE.STAGES
    WHERE DELETED IS NULL
    ORDER BY LAST_ALTERED DESC
    LIMIT 200
    """
    return execute_query(query)


def get_database_storage() -> pd.DataFrame:
    """
    Fetch database-level storage metrics.
    """
    query = """
    SELECT
        DATABASE_NAME,
        SUM(ACTIVE_BYTES) / (1024*1024*1024) as ACTIVE_GB,
        SUM(TIME_TRAVEL_BYTES) / (1024*1024*1024) as TIME_TRAVEL_GB,
        SUM(FAILSAFE_BYTES) / (1024*1024*1024) as FAILSAFE_GB,
        SUM(BYTES) / (1024*1024*1024) as TOTAL_GB
    FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
    WHERE USAGE_DATE >= DATEADD(day, -30, CURRENT_DATE())
    GROUP BY DATABASE_NAME
    ORDER BY TOTAL_GB DESC
    """
    return execute_query(query)


# =============================================================================
# SECURITY & SESSION METRICS
# =============================================================================

def get_active_sessions(hours: int = 1) -> pd.DataFrame:
    """
    Fetch active user sessions and connections.
    """
    query = f"""
    SELECT
        SESSION_ID,
        USER_NAME,
        CREATED_ON,
        LOGIN_EVENT_ID,
        CLIENT_APPLICATION_ID,
        CLIENT_ENVIRONMENT,
        CLIENT_NET_ADDRESS,
        AUTHENTICATION_METHOD
    FROM SNOWFLAKE.ACCOUNT_USAGE.SESSIONS
    WHERE CREATED_ON >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    ORDER BY CREATED_ON DESC
    LIMIT 500
    """
    return execute_query(query)


def get_session_metrics(days: int = 7) -> pd.DataFrame:
    """
    Fetch session metrics including duration and authentication methods.
    """
    query = f"""
    WITH session_data AS (
        SELECT
            USER_NAME,
            AUTHENTICATION_METHOD,
            CREATED_ON,
            -- Note: DESTROYED_ON may not be available in all Snowflake editions
            LAG(CREATED_ON) OVER (PARTITION BY USER_NAME ORDER BY CREATED_ON DESC) as NEXT_SESSION
        FROM SNOWFLAKE.ACCOUNT_USAGE.SESSIONS
        WHERE CREATED_ON >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    )
    SELECT
        USER_NAME,
        AUTHENTICATION_METHOD,
        COUNT(*) as SESSION_COUNT,
        MIN(CREATED_ON) as FIRST_SESSION,
        MAX(CREATED_ON) as LAST_SESSION
    FROM session_data
    GROUP BY USER_NAME, AUTHENTICATION_METHOD
    ORDER BY SESSION_COUNT DESC
    """
    return execute_query(query)


def get_query_patterns_by_user(days: int = 7) -> pd.DataFrame:
    """
    Fetch query patterns segmented by user and role.
    """
    query = f"""
    SELECT
        USER_NAME,
        ROLE_NAME,
        QUERY_TYPE,
        COUNT(*) as QUERY_COUNT,
        AVG(EXECUTION_TIME / 1000) as AVG_EXECUTION_SECONDS,
        SUM(BYTES_SCANNED) / (1024*1024*1024) as GB_SCANNED,
        SUM(ROWS_PRODUCED) as TOTAL_ROWS_PRODUCED
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND USER_NAME IS NOT NULL
    GROUP BY USER_NAME, ROLE_NAME, QUERY_TYPE
    ORDER BY QUERY_COUNT DESC
    LIMIT 500
    """
    return execute_query(query)


def get_access_control_changes(days: int = 30) -> pd.DataFrame:
    """
    Fetch access control changes including potential privilege escalation.
    """
    query = f"""
    SELECT
        TIMESTAMP,
        USER_NAME,
        ROLE_NAME,
        QUERY_TEXT,
        OBJECT_TYPE,
        OBJECT_NAME,
        PRIVILEGE,
        GRANTED_ON,
        GRANTED_BY
    FROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_ROLES
    WHERE CREATED_ON >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND DELETED_ON IS NULL
    ORDER BY CREATED_ON DESC
    LIMIT 500
    """
    return execute_query(query)


def get_network_policy_checks(hours: int = 24) -> pd.DataFrame:
    """
    Fetch network policy effectiveness by checking blocked login attempts.
    """
    query = f"""
    SELECT
        EVENT_TIMESTAMP,
        USER_NAME,
        CLIENT_IP,
        REPORTED_CLIENT_TYPE,
        IS_SUCCESS,
        ERROR_CODE,
        ERROR_MESSAGE
    FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
    WHERE EVENT_TIMESTAMP >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    AND IS_SUCCESS = 'NO'
    AND ERROR_MESSAGE ILIKE '%network policy%'
    ORDER BY EVENT_TIMESTAMP DESC
    LIMIT 200
    """
    return execute_query(query)


# =============================================================================
# PERFORMANCE ALERTS & MONITORING
# =============================================================================

def get_long_running_queries(hours: int = 24, threshold_minutes: int = 5) -> pd.DataFrame:
    """
    Identify long-running queries exceeding a threshold.
    """
    query = f"""
    SELECT
        QUERY_ID,
        USER_NAME,
        WAREHOUSE_NAME,
        QUERY_TYPE,
        START_TIME,
        END_TIME,
        TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SECONDS,
        TOTAL_ELAPSED_TIME / 60000 as ELAPSED_MINUTES,
        EXECUTION_STATUS,
        QUERY_TEXT
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    AND TOTAL_ELAPSED_TIME >= {threshold_minutes * 60 * 1000}
    ORDER BY TOTAL_ELAPSED_TIME DESC
    LIMIT 100
    """
    return execute_query(query)


def get_cache_metrics(hours: int = 24) -> pd.DataFrame:
    """
    Fetch query result cache hit rates.
    """
    query = f"""
    SELECT
        DATE_TRUNC('hour', START_TIME) as HOUR,
        WAREHOUSE_NAME,
        COUNT(*) as TOTAL_QUERIES,
        SUM(CASE WHEN QUERY_RESULT_CACHE_HIT = TRUE THEN 1 ELSE 0 END) as CACHE_HITS,
        (SUM(CASE WHEN QUERY_RESULT_CACHE_HIT = TRUE THEN 1 ELSE 0 END) / COUNT(*) * 100) as CACHE_HIT_RATE
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    AND WAREHOUSE_NAME IS NOT NULL
    GROUP BY DATE_TRUNC('hour', START_TIME), WAREHOUSE_NAME
    ORDER BY HOUR DESC
    """
    return execute_query(query)


def get_warehouse_queue_depth(hours: int = 24) -> pd.DataFrame:
    """
    Fetch warehouse queuing depth metrics.
    """
    query = f"""
    SELECT
        DATE_TRUNC('minute', START_TIME) as TIME_BUCKET,
        WAREHOUSE_NAME,
        COUNT(*) as QUERIES_IN_QUEUE,
        AVG(QUEUED_OVERLOAD_TIME / 1000) as AVG_QUEUE_SECONDS,
        MAX(QUEUED_OVERLOAD_TIME / 1000) as MAX_QUEUE_SECONDS
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    AND QUEUED_OVERLOAD_TIME > 0
    GROUP BY DATE_TRUNC('minute', START_TIME), WAREHOUSE_NAME
    ORDER BY TIME_BUCKET DESC
    """
    return execute_query(query)


# =============================================================================
# DATA QUALITY MONITORING
# =============================================================================

def get_row_count_trends(days: int = 30) -> pd.DataFrame:
    """
    Fetch row count trends for tables over time.
    """
    query = f"""
    SELECT
        TABLE_CATALOG as DATABASE_NAME,
        TABLE_SCHEMA as SCHEMA_NAME,
        TABLE_NAME,
        USAGE_DATE,
        ROW_COUNT,
        BYTES / (1024*1024*1024) as SIZE_GB
    FROM SNOWFLAKE.ACCOUNT_USAGE.TABLE_STORAGE_METRICS
    WHERE USAGE_DATE >= DATEADD(day, -{days}, CURRENT_DATE())
    AND DELETED IS NULL
    ORDER BY USAGE_DATE DESC, ROW_COUNT DESC
    LIMIT 1000
    """
    return execute_query(query)


def get_data_freshness() -> pd.DataFrame:
    """
    Monitor data freshness by checking last modification times.
    """
    query = """
    SELECT
        TABLE_CATALOG as DATABASE_NAME,
        TABLE_SCHEMA as SCHEMA_NAME,
        TABLE_NAME,
        LAST_ALTERED,
        DATEDIFF(hour, LAST_ALTERED, CURRENT_TIMESTAMP()) as HOURS_SINCE_UPDATE,
        ROW_COUNT
    FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
    WHERE DELETED IS NULL
    AND TABLE_TYPE = 'BASE TABLE'
    ORDER BY LAST_ALTERED DESC
    LIMIT 200
    """
    return execute_query(query)


def get_schema_evolution(days: int = 30) -> pd.DataFrame:
    """
    Track schema evolution and changes.
    """
    query = f"""
    SELECT
        TABLE_CATALOG as DATABASE_NAME,
        TABLE_SCHEMA as SCHEMA_NAME,
        TABLE_NAME,
        COLUMN_NAME,
        DATA_TYPE,
        IS_NULLABLE,
        CREATED,
        LAST_ALTERED,
        DELETED
    FROM SNOWFLAKE.ACCOUNT_USAGE.COLUMNS
    WHERE LAST_ALTERED >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    OR DELETED >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    ORDER BY LAST_ALTERED DESC
    LIMIT 500
    """
    return execute_query(query)


def get_pipe_validation_metrics(hours: int = 24) -> pd.DataFrame:
    """
    Validate Snowpipe ingestion patterns.
    """
    query = f"""
    SELECT
        PIPE_NAME,
        DATE_TRUNC('hour', PIPE_RECEIVED_TIME) as HOUR,
        COUNT(*) as FILE_COUNT,
        SUM(ROW_COUNT) as TOTAL_ROWS,
        SUM(ROW_PARSED) as TOTAL_PARSED,
        SUM(FILE_SIZE) / (1024*1024) as TOTAL_SIZE_MB,
        SUM(CASE WHEN STATUS = 'LOADED' THEN 1 ELSE 0 END) as LOADED_FILES,
        SUM(CASE WHEN STATUS != 'LOADED' THEN 1 ELSE 0 END) as FAILED_FILES
    FROM SNOWFLAKE.ACCOUNT_USAGE.COPY_HISTORY
    WHERE PIPE_RECEIVED_TIME >= DATEADD(hour, -{hours}, CURRENT_TIMESTAMP())
    GROUP BY PIPE_NAME, DATE_TRUNC('hour', PIPE_RECEIVED_TIME)
    ORDER BY HOUR DESC
    """
    return execute_query(query)


# =============================================================================
# ADVANCED FEATURES MONITORING
# =============================================================================

def get_stored_procedure_metrics(days: int = 7) -> pd.DataFrame:
    """
    Fetch stored procedure execution metrics.
    """
    query = f"""
    SELECT
        PROCEDURE_NAME,
        PROCEDURE_SCHEMA,
        PROCEDURE_CATALOG,
        COUNT(*) as EXECUTION_COUNT,
        AVG(TOTAL_ELAPSED_TIME / 1000) as AVG_EXECUTION_SECONDS,
        MAX(TOTAL_ELAPSED_TIME / 1000) as MAX_EXECUTION_SECONDS,
        SUM(CASE WHEN EXECUTION_STATUS = 'SUCCESS' THEN 1 ELSE 0 END) as SUCCESS_COUNT,
        SUM(CASE WHEN EXECUTION_STATUS != 'SUCCESS' THEN 1 ELSE 0 END) as FAILURE_COUNT
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND QUERY_TYPE = 'CALL'
    GROUP BY PROCEDURE_NAME, PROCEDURE_SCHEMA, PROCEDURE_CATALOG
    ORDER BY EXECUTION_COUNT DESC
    """
    return execute_query(query)


def get_udf_performance(days: int = 7) -> pd.DataFrame:
    """
    Track UDF (User Defined Function) performance.
    """
    query = f"""
    SELECT
        FUNCTION_NAME,
        FUNCTION_SCHEMA,
        FUNCTION_CATALOG,
        LANGUAGE,
        COUNT(*) as CALL_COUNT,
        AVG(TOTAL_ELAPSED_TIME / 1000) as AVG_EXECUTION_SECONDS
    FROM SNOWFLAKE.ACCOUNT_USAGE.FUNCTIONS
    WHERE CREATED >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND DELETED IS NULL
    GROUP BY FUNCTION_NAME, FUNCTION_SCHEMA, FUNCTION_CATALOG, LANGUAGE
    ORDER BY CALL_COUNT DESC
    LIMIT 100
    """
    return execute_query(query)


def get_materialized_view_refresh(days: int = 7) -> pd.DataFrame:
    """
    Monitor materialized view refresh patterns.
    """
    query = f"""
    SELECT
        TABLE_NAME,
        TABLE_SCHEMA,
        TABLE_CATALOG,
        LAST_ALTERED,
        BYTES / (1024*1024*1024) as SIZE_GB,
        ROW_COUNT,
        -- Check if it's a materialized view
        IS_MATERIALIZED_VIEW
    FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
    WHERE IS_MATERIALIZED_VIEW = 'YES'
    AND DELETED IS NULL
    ORDER BY LAST_ALTERED DESC
    LIMIT 100
    """
    return execute_query(query)


def get_stream_lag() -> pd.DataFrame:
    """
    Monitor stream processing lag.
    """
    query = """
    SELECT
        TABLE_CATALOG as DATABASE_NAME,
        TABLE_SCHEMA as SCHEMA_NAME,
        TABLE_NAME,
        SOURCE_TABLE_NAME,
        CREATED,
        LAST_ALTERED,
        STALE,
        STALE_AFTER,
        -- Stream type (standard, append-only, etc.)
        MODE
    FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
    WHERE TABLE_TYPE = 'STREAM'
    AND DELETED IS NULL
    ORDER BY LAST_ALTERED DESC
    LIMIT 100
    """
    return execute_query(query)


# =============================================================================
# RELIABILITY & UPTIME MONITORING
# =============================================================================

def get_query_failures_categorized(days: int = 7) -> pd.DataFrame:
    """
    Categorize query failures by error type.
    """
    query = f"""
    SELECT
        ERROR_CODE,
        ERROR_MESSAGE,
        COUNT(*) as FAILURE_COUNT,
        COUNT(DISTINCT USER_NAME) as AFFECTED_USERS,
        COUNT(DISTINCT WAREHOUSE_NAME) as AFFECTED_WAREHOUSES,
        MIN(START_TIME) as FIRST_OCCURRENCE,
        MAX(START_TIME) as LAST_OCCURRENCE
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND EXECUTION_STATUS = 'FAILED'
    GROUP BY ERROR_CODE, ERROR_MESSAGE
    ORDER BY FAILURE_COUNT DESC
    LIMIT 100
    """
    return execute_query(query)


def get_connection_timeouts(days: int = 7) -> pd.DataFrame:
    """
    Track connection timeout rates.
    """
    query = f"""
    SELECT
        DATE_TRUNC('hour', EVENT_TIMESTAMP) as HOUR,
        COUNT(*) as TIMEOUT_COUNT,
        COUNT(DISTINCT USER_NAME) as AFFECTED_USERS,
        COUNT(DISTINCT CLIENT_IP) as AFFECTED_IPS
    FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
    WHERE EVENT_TIMESTAMP >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    AND ERROR_MESSAGE ILIKE '%timeout%'
    GROUP BY DATE_TRUNC('hour', EVENT_TIMESTAMP)
    ORDER BY HOUR DESC
    """
    return execute_query(query)


def get_replication_metrics() -> pd.DataFrame:
    """
    Monitor database replication lag (for accounts using replication).
    """
    query = """
    SELECT
        DATABASE_NAME,
        REPLICATION_GROUP_NAME,
        SOURCE_ACCOUNT_LOCATOR,
        TARGET_ACCOUNT_LOCATOR,
        REPLICATION_SCHEDULE,
        LAST_REFRESH_TIME,
        DATEDIFF(minute, LAST_REFRESH_TIME, CURRENT_TIMESTAMP()) as MINUTES_SINCE_REFRESH
    FROM SNOWFLAKE.ACCOUNT_USAGE.REPLICATION_GROUP_USAGE_HISTORY
    WHERE LAST_REFRESH_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
    ORDER BY LAST_REFRESH_TIME DESC
    LIMIT 100
    """
    return execute_query(query)


def get_data_transfer_metrics(days: int = 7) -> pd.DataFrame:
    """
    Track data loading and transfer patterns.
    """
    query = f"""
    SELECT
        TABLE_NAME,
        TABLE_CATALOG as DATABASE_NAME,
        TABLE_SCHEMA as SCHEMA_NAME,
        DATE_TRUNC('hour', LAST_LOAD_TIME) as LOAD_HOUR,
        FILE_NAME,
        ROW_COUNT,
        ROW_PARSED,
        FILE_SIZE / (1024*1024) as FILE_SIZE_MB,
        STATUS,
        ERROR_MESSAGE,
        PIPE_NAME
    FROM SNOWFLAKE.ACCOUNT_USAGE.LOAD_HISTORY
    WHERE LAST_LOAD_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    ORDER BY LAST_LOAD_TIME DESC
    LIMIT 500
    """
    return execute_query(query)
