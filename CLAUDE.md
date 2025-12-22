# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Streamlit application for monitoring Snowflake account usage, performance, and activity. It provides dashboards for query history, warehouse load, login events, storage usage, task execution, and Snowpipe operations.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run Home.py
```

The app uses Streamlit's multi-page architecture with `Home.py` as the main entry point and additional pages in the `pages/` directory.

## Configuration

### Snowflake Credentials
The app uses Streamlit secrets for Snowflake authentication. Create `.streamlit/secrets.toml`:

```toml
[snowflake]
user = "your_username"
password = "your_password"
account = "your_account"
warehouse = "your_warehouse"
role = "your_role"
```

Required permissions: The Snowflake role must have access to `SNOWFLAKE.ACCOUNT_USAGE` views.

## Architecture

### Application Structure

**Main Page:**
- **Home.py**: Main dashboard with 4 tabs (Overview, Query Performance, Warehouse Usage, Login Activity)
  - Overview tab: Key metrics cards + storage usage trend
  - Query Performance tab: Execution statistics, status distribution, top warehouses, slowest queries
  - Warehouse Usage tab: Credit consumption trends, compute vs cloud services breakdown
  - Login Activity tab: Success/failure rates, active users, recent failed login attempts
  - Sidebar controls for time range selection and manual refresh

**Additional Pages:**
- **pages/1_Warehouse_Load.py**: Detailed warehouse utilization monitoring
  - Query distribution by warehouse, execution time analysis, activity heatmaps

- **pages/2_Access_History.py**: Data governance and access tracking
  - User activity, object access patterns (direct/base/modified), JSON parsing for object arrays

- **pages/3_Task_History.py**: Snowflake task execution monitoring
  - Success/failure rates, task performance metrics, duration analysis, failure tracking

- **pages/4_Snowpipe_Usage.py**: Snowpipe data ingestion monitoring
  - File load status, ingestion trends, parse efficiency, pipe performance metrics

### Connection Management
- **utils/snowflake_connector.py**: Handles Snowflake connections using `@st.cache_resource` for connection pooling
  - `get_snowflake_connection()`: Creates and caches a single Snowflake connection across the app
  - `execute_query(query, params)`: Executes queries and returns pandas DataFrames

### Data Queries
- **utils/queries.py**: Pre-defined query functions for Snowflake ACCOUNT_USAGE views
  - `get_query_history(hours)`: Query execution history and performance metrics
  - `get_warehouse_load(hours)`: Warehouse utilization and query counts per hour
  - `get_login_history(hours)`: Authentication events and login attempts
  - `get_storage_usage()`: Storage consumption over last 30 days (database, stage, failsafe)
  - `get_access_history(hours)`: Object-level access patterns
  - `get_warehouse_metering(days)`: Credit consumption (compute + cloud services)
  - `get_task_history(hours)`: Scheduled task execution status
  - `get_pipe_usage(hours)`: Snowpipe ingestion statistics from COPY_HISTORY

All query functions return pandas DataFrames and handle errors gracefully via the connector's error handling.

### Key Design Patterns

1. **Cached Connection**: Single shared connection via `@st.cache_resource` prevents connection overhead
2. **Account Usage Views**: All queries use `SNOWFLAKE.ACCOUNT_USAGE` schema (note: this data has latency of 45 minutes to 3 hours)
3. **Time-based Filtering**: Most queries accept time ranges (hours/days) and use `DATEADD` for filtering
4. **Result Limits**: Queries limit results (500-1000 rows) to prevent memory issues

## Dependencies

- `streamlit`: Web app framework
- `snowflake-connector-python`: Snowflake database connector
- `pandas`: Data manipulation
- `plotly` + `altair`: Visualization libraries
- `python-dotenv`: Environment variable management

## Important Notes

- ACCOUNT_USAGE views have latency (45 min - 3 hours), not real-time
- Connection is cached at app level; restart app to reset connection
- All queries assume Snowflake Enterprise Edition features (ACCOUNT_USAGE schema)
- Error handling returns empty DataFrames on failure with Streamlit error messages
