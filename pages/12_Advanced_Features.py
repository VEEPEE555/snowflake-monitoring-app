import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.queries import (
    get_stored_procedure_metrics,
    get_udf_performance,
    get_materialized_view_refresh,
    get_stream_lag
)

st.set_page_config(
    page_title="Advanced Features",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 Advanced Features Monitoring")
st.markdown("Monitor stored procedures, UDFs, materialized views, and streams performance")

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
with st.spinner("Loading advanced features data..."):
    proc_metrics = get_stored_procedure_metrics(time_range)
    udf_data = get_udf_performance(time_range)
    mv_data = get_materialized_view_refresh(time_range)
    stream_data = get_stream_lag()

# =============================================================================
# SECTION 1: STORED PROCEDURES
# =============================================================================
st.header("⚙️ Stored Procedure Execution Metrics")

if not proc_metrics.empty:
    # Overall metrics
    total_executions = proc_metrics['EXECUTION_COUNT'].sum()
    total_success = proc_metrics['SUCCESS_COUNT'].sum()
    total_failures = proc_metrics['FAILURE_COUNT'].sum()
    success_rate = (total_success / total_executions * 100) if total_executions > 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Executions", f"{total_executions:,}")

    with col2:
        st.metric("Success Rate", f"{success_rate:.1f}%")

    with col3:
        st.metric("Total Procedures", len(proc_metrics))

    with col4:
        avg_exec_time = proc_metrics['AVG_EXECUTION_SECONDS'].mean()
        st.metric("Avg Execution Time", f"{avg_exec_time:.2f}s")

    # Most executed procedures
    st.subheader("Most Executed Stored Procedures")

    col1, col2 = st.columns(2)

    with col1:
        top_procs = proc_metrics.nlargest(15, 'EXECUTION_COUNT')
        top_procs['FULL_NAME'] = (
            top_procs['PROCEDURE_CATALOG'] + '.' +
            top_procs['PROCEDURE_SCHEMA'] + '.' +
            top_procs['PROCEDURE_NAME']
        )

        fig_exec = px.bar(
            top_procs,
            x='EXECUTION_COUNT',
            y='FULL_NAME',
            orientation='h',
            title='Top 15 by Execution Count',
            labels={'EXECUTION_COUNT': 'Executions', 'FULL_NAME': 'Procedure'},
            color='EXECUTION_COUNT',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_exec, use_container_width=True)

    with col2:
        slowest_procs = proc_metrics.nlargest(15, 'AVG_EXECUTION_SECONDS')
        slowest_procs['FULL_NAME'] = (
            slowest_procs['PROCEDURE_CATALOG'] + '.' +
            slowest_procs['PROCEDURE_SCHEMA'] + '.' +
            slowest_procs['PROCEDURE_NAME']
        )

        fig_slow = px.bar(
            slowest_procs,
            x='AVG_EXECUTION_SECONDS',
            y='FULL_NAME',
            orientation='h',
            title='Top 15 by Avg Execution Time',
            labels={'AVG_EXECUTION_SECONDS': 'Avg Time (s)', 'FULL_NAME': 'Procedure'},
            color='AVG_EXECUTION_SECONDS',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_slow, use_container_width=True)

    # Success vs failure analysis
    st.subheader("Procedure Success vs Failure")

    proc_metrics['FULL_NAME'] = (
        proc_metrics['PROCEDURE_CATALOG'] + '.' +
        proc_metrics['PROCEDURE_SCHEMA'] + '.' +
        proc_metrics['PROCEDURE_NAME']
    )

    # Procedures with failures
    procs_with_failures = proc_metrics[proc_metrics['FAILURE_COUNT'] > 0].sort_values('FAILURE_COUNT', ascending=False)

    if not procs_with_failures.empty:
        st.warning(f"⚠️ {len(procs_with_failures)} procedures have execution failures")

        col1, col2 = st.columns(2)

        with col1:
            fig_failures = px.bar(
                procs_with_failures.head(15),
                x='FAILURE_COUNT',
                y='FULL_NAME',
                orientation='h',
                title='Procedures with Most Failures',
                labels={'FAILURE_COUNT': 'Failures', 'FULL_NAME': 'Procedure'},
                color='FAILURE_COUNT',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_failures, use_container_width=True)

        with col2:
            procs_with_failures['FAILURE_RATE'] = (
                procs_with_failures['FAILURE_COUNT'] / procs_with_failures['EXECUTION_COUNT'] * 100
            )

            fig_failure_rate = px.bar(
                procs_with_failures.head(15),
                x='FAILURE_RATE',
                y='FULL_NAME',
                orientation='h',
                title='Highest Failure Rates',
                labels={'FAILURE_RATE': 'Failure Rate (%)', 'FULL_NAME': 'Procedure'},
                color='FAILURE_RATE',
                color_continuous_scale='Oranges'
            )
            st.plotly_chart(fig_failure_rate, use_container_width=True)

        with st.expander("📋 View Procedures with Failures"):
            st.dataframe(
                procs_with_failures[['FULL_NAME', 'EXECUTION_COUNT', 'SUCCESS_COUNT', 'FAILURE_COUNT', 'FAILURE_RATE', 'AVG_EXECUTION_SECONDS']].round(2),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.success("✅ All stored procedures executing successfully")

    # Performance distribution
    st.subheader("Execution Time Distribution")

    fig_perf = px.box(
        proc_metrics,
        y='AVG_EXECUTION_SECONDS',
        title='Stored Procedure Execution Time Distribution',
        labels={'AVG_EXECUTION_SECONDS': 'Avg Execution Time (s)'}
    )
    st.plotly_chart(fig_perf, use_container_width=True)

    # Detailed procedure list
    with st.expander("📋 All Stored Procedures"):
        st.dataframe(
            proc_metrics[['FULL_NAME', 'EXECUTION_COUNT', 'SUCCESS_COUNT', 'FAILURE_COUNT', 'AVG_EXECUTION_SECONDS', 'MAX_EXECUTION_SECONDS']].round(2),
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("No stored procedure execution data available")

# =============================================================================
# SECTION 2: USER-DEFINED FUNCTIONS (UDFs)
# =============================================================================
st.header("📐 User-Defined Functions (UDFs)")

if not udf_data.empty:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total UDFs", len(udf_data))

    with col2:
        total_calls = udf_data['CALL_COUNT'].sum()
        st.metric("Total Calls", f"{total_calls:,}")

    with col3:
        avg_time = udf_data['AVG_EXECUTION_SECONDS'].mean()
        st.metric("Avg Execution Time", f"{avg_time:.3f}s")

    # UDF language distribution
    st.subheader("UDF Language Distribution")

    col1, col2 = st.columns(2)

    with col1:
        lang_dist = udf_data['LANGUAGE'].value_counts()

        fig_lang = px.pie(
            values=lang_dist.values,
            names=lang_dist.index,
            title='UDFs by Language'
        )
        st.plotly_chart(fig_lang, use_container_width=True)

    with col2:
        lang_calls = udf_data.groupby('LANGUAGE')['CALL_COUNT'].sum()

        fig_lang_calls = px.bar(
            x=lang_calls.index,
            y=lang_calls.values,
            title='Total Calls by Language',
            labels={'x': 'Language', 'y': 'Total Calls'}
        )
        st.plotly_chart(fig_lang_calls, use_container_width=True)

    # Most called UDFs
    st.subheader("Most Called UDFs")

    top_udfs = udf_data.nlargest(20, 'CALL_COUNT')
    top_udfs['FULL_NAME'] = (
        top_udfs['FUNCTION_CATALOG'] + '.' +
        top_udfs['FUNCTION_SCHEMA'] + '.' +
        top_udfs['FUNCTION_NAME']
    )

    col1, col2 = st.columns(2)

    with col1:
        fig_udf_calls = px.bar(
            top_udfs.head(15),
            x='CALL_COUNT',
            y='FULL_NAME',
            orientation='h',
            title='Top 15 UDFs by Call Count',
            labels={'CALL_COUNT': 'Calls', 'FULL_NAME': 'Function'},
            color='LANGUAGE',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig_udf_calls, use_container_width=True)

    with col2:
        slowest_udfs = udf_data.nlargest(15, 'AVG_EXECUTION_SECONDS')
        slowest_udfs['FULL_NAME'] = (
            slowest_udfs['FUNCTION_CATALOG'] + '.' +
            slowest_udfs['FUNCTION_SCHEMA'] + '.' +
            slowest_udfs['FUNCTION_NAME']
        )

        fig_udf_slow = px.bar(
            slowest_udfs,
            x='AVG_EXECUTION_SECONDS',
            y='FULL_NAME',
            orientation='h',
            title='Slowest UDFs',
            labels={'AVG_EXECUTION_SECONDS': 'Avg Time (s)', 'FULL_NAME': 'Function'},
            color='LANGUAGE'
        )
        st.plotly_chart(fig_udf_slow, use_container_width=True)

    # Performance by language
    st.subheader("UDF Performance by Language")

    lang_perf = udf_data.groupby('LANGUAGE').agg({
        'CALL_COUNT': 'sum',
        'AVG_EXECUTION_SECONDS': 'mean'
    }).reset_index()

    fig_lang_perf = px.scatter(
        lang_perf,
        x='CALL_COUNT',
        y='AVG_EXECUTION_SECONDS',
        size='CALL_COUNT',
        color='LANGUAGE',
        title='UDF Performance by Language',
        labels={
            'CALL_COUNT': 'Total Calls',
            'AVG_EXECUTION_SECONDS': 'Avg Execution Time (s)'
        },
        hover_data=['LANGUAGE']
    )
    st.plotly_chart(fig_lang_perf, use_container_width=True)

    with st.expander("📋 All UDFs"):
        udf_data['FULL_NAME'] = (
            udf_data['FUNCTION_CATALOG'] + '.' +
            udf_data['FUNCTION_SCHEMA'] + '.' +
            udf_data['FUNCTION_NAME']
        )
        st.dataframe(
            udf_data[['FULL_NAME', 'LANGUAGE', 'CALL_COUNT', 'AVG_EXECUTION_SECONDS']].round(3),
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("No UDF execution data available")

# =============================================================================
# SECTION 3: MATERIALIZED VIEWS
# =============================================================================
st.header("🔄 Materialized View Refresh Patterns")

if not mv_data.empty:
    mv_data['LAST_ALTERED'] = pd.to_datetime(mv_data['LAST_ALTERED'])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Materialized Views", len(mv_data))

    with col2:
        total_size = mv_data['SIZE_GB'].sum()
        st.metric("Total Size", f"{total_size:.2f} GB")

    with col3:
        total_rows = mv_data['ROW_COUNT'].sum()
        st.metric("Total Rows", f"{total_rows:,}")

    # Recent refreshes
    st.subheader("Recently Refreshed Materialized Views")

    recent_mv = mv_data.sort_values('LAST_ALTERED', ascending=False).head(20)
    recent_mv['FULL_NAME'] = (
        recent_mv['TABLE_CATALOG'] + '.' +
        recent_mv['TABLE_SCHEMA'] + '.' +
        recent_mv['TABLE_NAME']
    )

    col1, col2 = st.columns(2)

    with col1:
        fig_mv = px.bar(
            recent_mv,
            x='SIZE_GB',
            y='FULL_NAME',
            orientation='h',
            title='Top 20 Materialized Views by Size',
            labels={'SIZE_GB': 'Size (GB)', 'FULL_NAME': 'View'},
            color='SIZE_GB',
            color_continuous_scale='Purples'
        )
        st.plotly_chart(fig_mv, use_container_width=True)

    with col2:
        fig_mv_rows = px.bar(
            recent_mv,
            x='ROW_COUNT',
            y='FULL_NAME',
            orientation='h',
            title='Top 20 Materialized Views by Row Count',
            labels={'ROW_COUNT': 'Rows', 'FULL_NAME': 'View'},
            color='ROW_COUNT',
            color_continuous_scale='Greens'
        )
        st.plotly_chart(fig_mv_rows, use_container_width=True)

    # Refresh timeline
    st.subheader("Refresh Activity Timeline")

    mv_data['HOURS_SINCE_REFRESH'] = (pd.Timestamp.now() - mv_data['LAST_ALTERED']).dt.total_seconds() / 3600

    fig_timeline = px.scatter(
        mv_data.sort_values('HOURS_SINCE_REFRESH'),
        x='HOURS_SINCE_REFRESH',
        y='SIZE_GB',
        size='ROW_COUNT',
        hover_data=['TABLE_NAME'],
        title='Materialized View Refresh Age vs Size',
        labels={
            'HOURS_SINCE_REFRESH': 'Hours Since Last Refresh',
            'SIZE_GB': 'Size (GB)',
            'ROW_COUNT': 'Row Count'
        }
    )
    st.plotly_chart(fig_timeline, use_container_width=True)

    # Stale materialized views
    stale_mvs = mv_data[mv_data['HOURS_SINCE_REFRESH'] > 24]

    if not stale_mvs.empty:
        st.warning(f"⚠️ {len(stale_mvs)} materialized views not refreshed in 24+ hours")

        with st.expander("View Stale Materialized Views"):
            stale_mvs['FULL_NAME'] = (
                stale_mvs['TABLE_CATALOG'] + '.' +
                stale_mvs['TABLE_SCHEMA'] + '.' +
                stale_mvs['TABLE_NAME']
            )
            st.dataframe(
                stale_mvs[['FULL_NAME', 'HOURS_SINCE_REFRESH', 'SIZE_GB', 'ROW_COUNT', 'LAST_ALTERED']].round(2),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.success("✅ All materialized views refreshed within 24 hours")

    # Full list
    with st.expander("📋 All Materialized Views"):
        mv_data['FULL_NAME'] = (
            mv_data['TABLE_CATALOG'] + '.' +
            mv_data['TABLE_SCHEMA'] + '.' +
            mv_data['TABLE_NAME']
        )
        st.dataframe(
            mv_data[['FULL_NAME', 'SIZE_GB', 'ROW_COUNT', 'LAST_ALTERED']].round(2),
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("No materialized views found")

# =============================================================================
# SECTION 4: STREAMS
# =============================================================================
st.header("🌊 Stream Processing Lag Monitoring")

if not stream_data.empty:
    stream_data['LAST_ALTERED'] = pd.to_datetime(stream_data['LAST_ALTERED'])
    stream_data['CREATED'] = pd.to_datetime(stream_data['CREATED'])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Streams", len(stream_data))

    with col2:
        stale_streams = len(stream_data[stream_data['STALE'] == 'YES'])
        st.metric("Stale Streams", stale_streams)

    with col3:
        stream_modes = stream_data['MODE'].nunique()
        st.metric("Stream Types", stream_modes)

    # Stream overview
    st.subheader("Stream Overview")

    stream_data['FULL_NAME'] = (
        stream_data['DATABASE_NAME'] + '.' +
        stream_data['SCHEMA_NAME'] + '.' +
        stream_data['TABLE_NAME']
    )

    col1, col2 = st.columns(2)

    with col1:
        # Stream mode distribution
        mode_dist = stream_data['MODE'].value_counts()

        fig_mode = px.pie(
            values=mode_dist.values,
            names=mode_dist.index,
            title='Stream Mode Distribution'
        )
        st.plotly_chart(fig_mode, use_container_width=True)

    with col2:
        # Stale vs active
        stale_dist = stream_data['STALE'].value_counts()

        fig_stale = px.pie(
            values=stale_dist.values,
            names=stale_dist.index,
            title='Stream Status (Stale vs Active)',
            color_discrete_map={'YES': 'red', 'NO': 'green'}
        )
        st.plotly_chart(fig_stale, use_container_width=True)

    # Recent stream activity
    st.subheader("Recent Stream Activity")

    recent_streams = stream_data.sort_values('LAST_ALTERED', ascending=False).head(20)

    st.dataframe(
        recent_streams[['FULL_NAME', 'SOURCE_TABLE_NAME', 'MODE', 'STALE', 'LAST_ALTERED', 'CREATED']],
        use_container_width=True,
        hide_index=True
    )

    # Stale streams alert
    if stale_streams > 0:
        st.warning(f"⚠️ {stale_streams} streams are marked as stale")

        stale_stream_data = stream_data[stream_data['STALE'] == 'YES']

        with st.expander("View Stale Streams"):
            st.dataframe(
                stale_stream_data[['FULL_NAME', 'SOURCE_TABLE_NAME', 'MODE', 'STALE_AFTER', 'LAST_ALTERED']],
                use_container_width=True,
                hide_index=True
            )

        st.info("**Stale streams** have exceeded their STALE_AFTER time and may need to be refreshed or recreated")
    else:
        st.success("✅ All streams are active")

    # Stream age analysis
    st.subheader("Stream Age Analysis")

    stream_data['DAYS_SINCE_CREATION'] = (pd.Timestamp.now() - stream_data['CREATED']).dt.days
    stream_data['DAYS_SINCE_MODIFIED'] = (pd.Timestamp.now() - stream_data['LAST_ALTERED']).dt.days

    fig_age = px.scatter(
        stream_data,
        x='DAYS_SINCE_CREATION',
        y='DAYS_SINCE_MODIFIED',
        hover_data=['TABLE_NAME', 'MODE'],
        title='Stream Age: Creation vs Last Modification',
        labels={
            'DAYS_SINCE_CREATION': 'Days Since Creation',
            'DAYS_SINCE_MODIFIED': 'Days Since Last Modified'
        },
        color='STALE'
    )
    st.plotly_chart(fig_age, use_container_width=True)

else:
    st.info("No streams found in the account")

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
