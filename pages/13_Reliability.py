import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.queries import (
    get_query_failures_categorized,
    get_connection_timeouts,
    get_replication_metrics,
    get_data_transfer_metrics
)

st.set_page_config(
    page_title="Reliability Monitoring",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Reliability & Uptime Monitoring")
st.markdown("Monitor system reliability, query failures, connection issues, and replication health")

# Sidebar controls
st.sidebar.header("Filters")
time_range = st.sidebar.selectbox(
    "Time Range",
    options=[1, 3, 7, 14, 30],
    index=2,
    format_func=lambda x: f"Last {x} days"
)

refresh = st.sidebar.button("🔄 Refresh Data")

# Fetch data
with st.spinner("Loading reliability metrics..."):
    query_failures = get_query_failures_categorized(time_range)
    connection_timeouts = get_connection_timeouts(time_range)
    replication_data = get_replication_metrics()
    data_transfer = get_data_transfer_metrics(time_range)

# =============================================================================
# SECTION 1: QUERY FAILURE CATEGORIZATION
# =============================================================================
st.header("❌ Query Failure Analysis")

if not query_failures.empty:
    query_failures['FIRST_OCCURRENCE'] = pd.to_datetime(query_failures['FIRST_OCCURRENCE'])
    query_failures['LAST_OCCURRENCE'] = pd.to_datetime(query_failures['LAST_OCCURRENCE'])

    # Overall failure metrics
    total_failures = query_failures['FAILURE_COUNT'].sum()
    unique_errors = len(query_failures)
    affected_users = query_failures['AFFECTED_USERS'].sum()
    affected_warehouses = query_failures['AFFECTED_WAREHOUSES'].sum()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Failures", f"{total_failures:,}")

    with col2:
        st.metric("Unique Error Types", f"{unique_errors:,}")

    with col3:
        st.metric("Affected Users", f"{affected_users:,}")

    with col4:
        st.metric("Affected Warehouses", f"{affected_warehouses:,}")

    # Top error codes
    st.subheader("Most Common Error Codes")

    col1, col2 = st.columns(2)

    with col1:
        error_code_dist = query_failures.groupby('ERROR_CODE')['FAILURE_COUNT'].sum().sort_values(ascending=False).head(10)

        fig_codes = px.bar(
            x=error_code_dist.values,
            y=error_code_dist.index.astype(str),
            orientation='h',
            title='Top 10 Error Codes by Failure Count',
            labels={'x': 'Failures', 'y': 'Error Code'},
            color=error_code_dist.values,
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_codes, use_container_width=True)

    with col2:
        fig_codes_pie = px.pie(
            values=error_code_dist.values,
            names=error_code_dist.index.astype(str),
            title='Error Code Distribution'
        )
        st.plotly_chart(fig_codes_pie, use_container_width=True)

    # Most frequent failures
    st.subheader("Most Frequent Failures")

    top_failures = query_failures.nlargest(20, 'FAILURE_COUNT')

    # Truncate error messages for display
    top_failures['ERROR_MESSAGE_SHORT'] = top_failures['ERROR_MESSAGE'].str[:100]

    st.dataframe(
        top_failures[['ERROR_CODE', 'ERROR_MESSAGE_SHORT', 'FAILURE_COUNT', 'AFFECTED_USERS', 'AFFECTED_WAREHOUSES', 'FIRST_OCCURRENCE', 'LAST_OCCURRENCE']],
        use_container_width=True,
        hide_index=True
    )

    # Failure timeline
    st.subheader("Failure Timeline Analysis")

    # Calculate failure duration
    query_failures['DURATION_HOURS'] = (
        (query_failures['LAST_OCCURRENCE'] - query_failures['FIRST_OCCURRENCE']).dt.total_seconds() / 3600
    )

    # Persistent failures (recurring over time)
    persistent_failures = query_failures[query_failures['DURATION_HOURS'] > 24].sort_values('FAILURE_COUNT', ascending=False)

    if not persistent_failures.empty:
        st.warning(f"⚠️ {len(persistent_failures)} error types persisting for 24+ hours")

        fig_persistent = px.scatter(
            persistent_failures.head(20),
            x='DURATION_HOURS',
            y='FAILURE_COUNT',
            size='AFFECTED_USERS',
            hover_data=['ERROR_CODE', 'ERROR_MESSAGE'],
            title='Persistent Failures (24+ hours duration)',
            labels={
                'DURATION_HOURS': 'Error Duration (hours)',
                'FAILURE_COUNT': 'Failure Count',
                'AFFECTED_USERS': 'Affected Users'
            },
            color='FAILURE_COUNT',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_persistent, use_container_width=True)

        with st.expander("📋 View Persistent Failures"):
            persistent_failures['ERROR_MESSAGE_SHORT'] = persistent_failures['ERROR_MESSAGE'].str[:150]
            st.dataframe(
                persistent_failures[['ERROR_CODE', 'ERROR_MESSAGE_SHORT', 'FAILURE_COUNT', 'DURATION_HOURS', 'AFFECTED_USERS']].round(2),
                use_container_width=True,
                hide_index=True
            )

            st.info("**Persistent failures** may indicate systemic issues requiring immediate attention")

    # Error categories
    st.subheader("Error Categorization")

    # Categorize errors based on common patterns
    def categorize_error(error_msg):
        if pd.isna(error_msg):
            return 'Unknown'
        error_msg = str(error_msg).upper()

        if 'TIMEOUT' in error_msg:
            return 'Timeout'
        elif 'PERMISSION' in error_msg or 'ACCESS' in error_msg or 'DENIED' in error_msg:
            return 'Permission'
        elif 'SYNTAX' in error_msg or 'PARSE' in error_msg:
            return 'Syntax'
        elif 'RESOURCE' in error_msg or 'MEMORY' in error_msg:
            return 'Resource'
        elif 'NETWORK' in error_msg or 'CONNECTION' in error_msg:
            return 'Network'
        elif 'NOT FOUND' in error_msg or 'DOES NOT EXIST' in error_msg:
            return 'Object Not Found'
        else:
            return 'Other'

    query_failures['ERROR_CATEGORY'] = query_failures['ERROR_MESSAGE'].apply(categorize_error)

    category_dist = query_failures.groupby('ERROR_CATEGORY')['FAILURE_COUNT'].sum().sort_values(ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_category = px.pie(
            values=category_dist.values,
            names=category_dist.index,
            title='Failures by Error Category'
        )
        st.plotly_chart(fig_category, use_container_width=True)

    with col2:
        fig_category_bar = px.bar(
            x=category_dist.values,
            y=category_dist.index,
            orientation='h',
            title='Failure Count by Category',
            labels={'x': 'Failures', 'y': 'Category'},
            color=category_dist.values,
            color_continuous_scale='Oranges'
        )
        st.plotly_chart(fig_category_bar, use_container_width=True)

else:
    st.success("✅ No query failures detected in the selected time range")

# =============================================================================
# SECTION 2: CONNECTION TIMEOUTS
# =============================================================================
st.header("⏱️ Connection Timeout Analysis")

if not connection_timeouts.empty:
    connection_timeouts['HOUR'] = pd.to_datetime(connection_timeouts['HOUR'])

    total_timeouts = connection_timeouts['TIMEOUT_COUNT'].sum()
    unique_users_affected = connection_timeouts['AFFECTED_USERS'].sum()
    unique_ips = connection_timeouts['AFFECTED_IPS'].sum()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Timeouts", f"{total_timeouts:,}")

    with col2:
        st.metric("Affected Users", f"{unique_users_affected:,}")

    with col3:
        st.metric("Affected IP Addresses", f"{unique_ips:,}")

    # Timeout timeline
    st.subheader("Timeout Timeline")

    fig_timeout = px.area(
        connection_timeouts,
        x='HOUR',
        y='TIMEOUT_COUNT',
        title='Connection Timeouts Over Time',
        labels={'TIMEOUT_COUNT': 'Timeout Count', 'HOUR': 'Time'},
        color_discrete_sequence=['red']
    )
    fig_timeout.update_layout(height=400)
    st.plotly_chart(fig_timeout, use_container_width=True)

    # Peak timeout periods
    st.subheader("Peak Timeout Periods")

    peak_periods = connection_timeouts.nlargest(10, 'TIMEOUT_COUNT')

    st.dataframe(
        peak_periods[['HOUR', 'TIMEOUT_COUNT', 'AFFECTED_USERS', 'AFFECTED_IPS']],
        use_container_width=True,
        hide_index=True
    )

    st.warning("⚠️ **High timeout rates may indicate network issues or service degradation**")

else:
    st.success("✅ No connection timeouts detected")

# =============================================================================
# SECTION 3: REPLICATION MONITORING
# =============================================================================
st.header("🔄 Database Replication Status")

if not replication_data.empty:
    replication_data['LAST_REFRESH_TIME'] = pd.to_datetime(replication_data['LAST_REFRESH_TIME'])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Replication Groups", len(replication_data))

    with col2:
        avg_lag = replication_data['MINUTES_SINCE_REFRESH'].mean()
        st.metric("Avg Replication Lag", f"{avg_lag:.1f} min")

    with col3:
        max_lag = replication_data['MINUTES_SINCE_REFRESH'].max()
        st.metric("Max Replication Lag", f"{max_lag:.1f} min")

    # Replication lag analysis
    st.subheader("Replication Lag by Database")

    fig_lag = px.bar(
        replication_data.sort_values('MINUTES_SINCE_REFRESH', ascending=False),
        x='MINUTES_SINCE_REFRESH',
        y='DATABASE_NAME',
        orientation='h',
        title='Replication Lag by Database',
        labels={'MINUTES_SINCE_REFRESH': 'Lag (minutes)', 'DATABASE_NAME': 'Database'},
        color='MINUTES_SINCE_REFRESH',
        color_continuous_scale='RdYlGn_r'
    )
    st.plotly_chart(fig_lag, use_container_width=True)

    # Replication health alerts
    high_lag = replication_data[replication_data['MINUTES_SINCE_REFRESH'] > 60]

    if not high_lag.empty:
        st.error(f"🚨 {len(high_lag)} databases with replication lag > 60 minutes")

        st.dataframe(
            high_lag[['DATABASE_NAME', 'REPLICATION_GROUP_NAME', 'SOURCE_ACCOUNT_LOCATOR', 'TARGET_ACCOUNT_LOCATOR', 'MINUTES_SINCE_REFRESH', 'LAST_REFRESH_TIME']],
            use_container_width=True,
            hide_index=True
        )

        st.warning("**High replication lag** may impact disaster recovery and data availability")
    else:
        st.success("✅ All replication groups within acceptable lag")

    # Replication schedule details
    with st.expander("📋 Replication Details"):
        st.dataframe(
            replication_data[['DATABASE_NAME', 'REPLICATION_GROUP_NAME', 'REPLICATION_SCHEDULE', 'LAST_REFRESH_TIME', 'MINUTES_SINCE_REFRESH']],
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("ℹ️ No database replication configured or data unavailable")

# =============================================================================
# SECTION 4: DATA TRANSFER & LOAD PATTERNS
# =============================================================================
st.header("📥 Data Loading & Transfer Patterns")

if not data_transfer.empty:
    data_transfer['LOAD_HOUR'] = pd.to_datetime(data_transfer['LOAD_HOUR'])

    # Transfer metrics
    total_files = len(data_transfer)
    successful_loads = len(data_transfer[data_transfer['STATUS'] == 'LOADED'])
    failed_loads = len(data_transfer[data_transfer['STATUS'] != 'LOADED'])
    success_rate = (successful_loads / total_files * 100) if total_files > 0 else 0

    total_rows = data_transfer['ROW_COUNT'].sum()
    total_size = data_transfer['FILE_SIZE_MB'].sum()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Files Loaded", f"{total_files:,}")

    with col2:
        st.metric("Load Success Rate", f"{success_rate:.1f}%")

    with col3:
        st.metric("Total Rows Loaded", f"{total_rows:,}")

    with col4:
        st.metric("Total Data", f"{total_size:,.2f} MB")

    # Load timeline
    st.subheader("Data Loading Timeline")

    timeline = data_transfer.groupby('LOAD_HOUR').agg({
        'ROW_COUNT': 'sum',
        'FILE_SIZE_MB': 'sum'
    }).reset_index()

    fig_load = go.Figure()

    fig_load.add_trace(go.Scatter(
        x=timeline['LOAD_HOUR'],
        y=timeline['ROW_COUNT'],
        name='Rows Loaded',
        mode='lines+markers',
        yaxis='y',
        line=dict(color='blue')
    ))

    fig_load.add_trace(go.Scatter(
        x=timeline['LOAD_HOUR'],
        y=timeline['FILE_SIZE_MB'],
        name='Data Size (MB)',
        mode='lines+markers',
        yaxis='y2',
        line=dict(color='green')
    ))

    fig_load.update_layout(
        title='Data Loading Activity Over Time',
        xaxis_title='Time',
        yaxis=dict(title='Rows Loaded', side='left'),
        yaxis2=dict(title='Data Size (MB)', side='right', overlaying='y'),
        height=400
    )

    st.plotly_chart(fig_load, use_container_width=True)

    # Load by table
    st.subheader("Data Loads by Table")

    table_loads = data_transfer.groupby('TABLE_NAME').agg({
        'FILE_NAME': 'count',
        'ROW_COUNT': 'sum',
        'FILE_SIZE_MB': 'sum'
    }).reset_index()
    table_loads.columns = ['TABLE_NAME', 'FILE_COUNT', 'TOTAL_ROWS', 'TOTAL_SIZE_MB']
    table_loads = table_loads.sort_values('TOTAL_ROWS', ascending=False).head(20)

    col1, col2 = st.columns(2)

    with col1:
        fig_table_rows = px.bar(
            table_loads,
            x='TOTAL_ROWS',
            y='TABLE_NAME',
            orientation='h',
            title='Top 20 Tables by Rows Loaded',
            labels={'TOTAL_ROWS': 'Rows', 'TABLE_NAME': 'Table'},
            color='TOTAL_ROWS',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_table_rows, use_container_width=True)

    with col2:
        fig_table_files = px.bar(
            table_loads,
            x='FILE_COUNT',
            y='TABLE_NAME',
            orientation='h',
            title='Top 20 Tables by File Count',
            labels={'FILE_COUNT': 'Files', 'TABLE_NAME': 'Table'},
            color='FILE_COUNT',
            color_continuous_scale='Greens'
        )
        st.plotly_chart(fig_table_files, use_container_width=True)

    # Failed loads
    if failed_loads > 0:
        st.subheader("⚠️ Failed Data Loads")

        failed_data = data_transfer[data_transfer['STATUS'] != 'LOADED'].sort_values('LOAD_HOUR', ascending=False)

        st.warning(f"Found {failed_loads} failed file loads")

        # Failed loads by table
        failed_by_table = failed_data['TABLE_NAME'].value_counts().head(15)

        fig_failed = px.bar(
            x=failed_by_table.values,
            y=failed_by_table.index,
            orientation='h',
            title='Failed Loads by Table',
            labels={'x': 'Failed Loads', 'y': 'Table'},
            color=failed_by_table.values,
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_failed, use_container_width=True)

        # Recent failures
        with st.expander("📋 View Recent Failed Loads"):
            recent_failures = failed_data.head(50)[[
                'LOAD_HOUR', 'TABLE_NAME', 'FILE_NAME', 'ROW_COUNT', 'STATUS', 'ERROR_MESSAGE'
            ]]
            st.dataframe(recent_failures, use_container_width=True, hide_index=True)

    else:
        st.success("✅ All data loads successful")

    # Bulk vs streaming detection
    st.subheader("Load Pattern Analysis")

    # Categorize as bulk (large files) or streaming (small frequent files)
    data_transfer['LOAD_TYPE'] = data_transfer['FILE_SIZE_MB'].apply(
        lambda x: 'Bulk Load (>100MB)' if x > 100 else 'Streaming (<100MB)'
    )

    pattern_dist = data_transfer.groupby('LOAD_TYPE').agg({
        'FILE_NAME': 'count',
        'ROW_COUNT': 'sum',
        'FILE_SIZE_MB': 'sum'
    }).reset_index()
    pattern_dist.columns = ['LOAD_TYPE', 'FILE_COUNT', 'TOTAL_ROWS', 'TOTAL_SIZE_MB']

    col1, col2 = st.columns(2)

    with col1:
        fig_pattern = px.pie(
            pattern_dist,
            values='FILE_COUNT',
            names='LOAD_TYPE',
            title='Load Pattern Distribution (by file count)'
        )
        st.plotly_chart(fig_pattern, use_container_width=True)

    with col2:
        st.dataframe(
            pattern_dist,
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("No data transfer activity in the selected time range")

# =============================================================================
# SYSTEM HEALTH SUMMARY
# =============================================================================
st.header("📊 System Health Summary")

health_score = 100
alerts = []

# Check query failures
if not query_failures.empty:
    failure_rate = query_failures['FAILURE_COUNT'].sum()
    if failure_rate > 1000:
        health_score -= 20
        alerts.append("High query failure rate")
    elif failure_rate > 100:
        health_score -= 10
        alerts.append("Moderate query failures")

# Check timeouts
if not connection_timeouts.empty:
    timeout_rate = connection_timeouts['TIMEOUT_COUNT'].sum()
    if timeout_rate > 100:
        health_score -= 15
        alerts.append("High connection timeout rate")
    elif timeout_rate > 10:
        health_score -= 5
        alerts.append("Some connection timeouts")

# Check replication lag
if not replication_data.empty:
    max_lag = replication_data['MINUTES_SINCE_REFRESH'].max()
    if max_lag > 120:
        health_score -= 15
        alerts.append("High replication lag")
    elif max_lag > 60:
        health_score -= 5
        alerts.append("Moderate replication lag")

# Check load failures
if not data_transfer.empty:
    failed_loads = len(data_transfer[data_transfer['STATUS'] != 'LOADED'])
    total_loads = len(data_transfer)
    failure_pct = (failed_loads / total_loads * 100) if total_loads > 0 else 0

    if failure_pct > 10:
        health_score -= 20
        alerts.append("High data load failure rate")
    elif failure_pct > 5:
        health_score -= 10
        alerts.append("Some data load failures")

# Display health score
col1, col2 = st.columns([1, 2])

with col1:
    if health_score >= 90:
        st.success(f"## System Health: {health_score}%")
        st.markdown("✅ **Excellent** - System operating normally")
    elif health_score >= 70:
        st.warning(f"## System Health: {health_score}%")
        st.markdown("⚠️ **Good** - Minor issues detected")
    elif health_score >= 50:
        st.warning(f"## System Health: {health_score}%")
        st.markdown("⚠️ **Fair** - Attention needed")
    else:
        st.error(f"## System Health: {health_score}%")
        st.markdown("🚨 **Critical** - Immediate action required")

with col2:
    if alerts:
        st.markdown("**Active Alerts:**")
        for alert in alerts:
            st.markdown(f"- ⚠️ {alert}")
    else:
        st.markdown("**No active alerts**")
        st.markdown("✅ All systems operating normally")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    <small>Data from Snowflake ACCOUNT_USAGE views • Updates may have 45min-3hr latency</small>
    </div>
    """,
    unsafe_allow_html=True
)
