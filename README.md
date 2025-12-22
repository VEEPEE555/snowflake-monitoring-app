# Snowflake Monitoring Dashboard

A comprehensive Streamlit application for monitoring Snowflake account usage, performance, and activity.

## Features

### 🏠 Home Dashboard
- **Overview**: Key metrics including total queries, success rate, credit usage, and failed logins
- **Query Performance**: Execution statistics, status distribution, and slowest queries
- **Warehouse Usage**: Credit consumption trends and compute vs cloud services breakdown
- **Login Activity**: Success/failure rates, active users, and failed login tracking

### 📊 Additional Monitoring Pages

#### 🏭 Warehouse Load
- Query distribution and count over time
- Execution time analysis by warehouse
- Activity heatmaps showing hourly patterns
- Warehouse performance comparisons

#### 🔐 Access History
- User activity tracking
- Object access patterns (direct, base, and modified objects)
- Data governance insights
- Recent modifications log

#### ⚙️ Task History
- Task execution success/failure rates
- Performance metrics and duration analysis
- Failed task analysis with error messages
- Task distribution by database/schema

#### 📊 Snowpipe Usage
- File load status tracking
- Data ingestion trends over time
- Parse efficiency metrics
- Pipe performance comparisons

## Prerequisites

- Python 3.8+
- Snowflake account with access to `SNOWFLAKE.ACCOUNT_USAGE` views
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/snowflake-monitoring-app.git
cd snowflake-monitoring-app
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure Snowflake credentials:
```bash
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
```

4. Edit `.streamlit/secrets.toml` with your Snowflake credentials:
```toml
[snowflake]
user = "your_username"
password = "your_password"
account = "your_account"  # e.g., "abc12345.us-east-1"
warehouse = "your_warehouse"  # e.g., "COMPUTE_WH"
role = "your_role"  # Must have access to SNOWFLAKE.ACCOUNT_USAGE
```

## Usage

Run the Streamlit application:
```bash
streamlit run Home.py
```

The app will be available at `http://localhost:8501`

## Snowflake Permissions

The Snowflake role must have `SELECT` privileges on the following views in the `SNOWFLAKE.ACCOUNT_USAGE` schema:

- `QUERY_HISTORY`
- `WAREHOUSE_METERING_HISTORY`
- `LOGIN_HISTORY`
- `STORAGE_USAGE`
- `ACCESS_HISTORY`
- `TASK_HISTORY`
- `COPY_HISTORY`

## Architecture

- **Home.py**: Main dashboard entry point
- **pages/**: Additional monitoring pages (auto-discovered by Streamlit)
- **utils/snowflake_connector.py**: Connection management with caching
- **utils/queries.py**: Pre-defined queries for ACCOUNT_USAGE views

## Important Notes

- **Data Latency**: `ACCOUNT_USAGE` views have a latency of 45 minutes to 3 hours
- **Not Real-Time**: This is historical monitoring, not real-time
- **Enterprise Edition**: Requires Snowflake Enterprise Edition or higher

## Security

- Never commit `.streamlit/secrets.toml` to version control
- The `.gitignore` file is configured to exclude sensitive files
- Use environment-specific credentials

## Dependencies

- `streamlit==1.40.1`
- `snowflake-connector-python==3.12.3`
- `pandas==2.2.3`
- `plotly==5.24.1`
- `altair==5.4.1`
- `python-dotenv==1.0.1`

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
