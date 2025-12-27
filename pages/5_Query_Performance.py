import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.queries import get_detailed_query_performance, get_query_concurrency
import numpy as np

st.set_page_config(
    page_title="Advanced Query Performance",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Advanced Query Performance Analysis")
st.markdown("Deep dive into query execution metrics, percentiles, and concurrency patterns")

# Sidebar controls
st.sidebar.header("Filters")
time_range = st.sidebar.selectbox(
    "Time Range",
    options=[1, 6, 12, 24, 48, 72, 168],
    index=3,
    format_func=lambda x: f"Last {x} hours" if x < 168 else "Last 7 days"
)

refresh = st.sidebar.button("🔄 Refresh Data")

# Fetch data
with st.spinner("Loading detailed query performance data..."):
    query_data = get_detailed_query_performance(time_range)
    concurrency_data = get_query_concurrency(time_range)

if query_data.empty:
    st.warning("No query performance data available for the selected time range")
    st.stop()

# Filter for successful queries for most analysis
successful_queries = query_data[query_data['EXECUTION_STATUS'] == 'SUCCESS'].copy()

# =============================================================================
# SECTION 1: EXECUTION TIME PERCENTILES (p50, p95, p99)
# =============================================================================
st.header("📊 Execution Time Percentiles")
st.markdown("Statistical distribution of query execution times")

if not successful_queries.empty:
    col1, col2, col3, col4 = st.columns(4)

    # Calculate percentiles
    p50 = successful_queries['EXECUTION_TIME_SECONDS'].quantile(0.50)
    p95 = successful_queries['EXECUTION_TIME_SECONDS'].quantile(0.95)
    p99 = successful_queries['EXECUTION_TIME_SECONDS'].quantile(0.99)
    avg_time = successful_queries['EXECUTION_TIME_SECONDS'].mean()

    with col1:
        st.metric("Average", f"{avg_time:.2f}s")

    with col2:
        st.metric("p50 (Median)", f"{p50:.2f}s")

    with col3:
        st.metric("p95", f"{p95:.2f}s")

    with col4:
        st.metric("p99", f"{p99:.2f}s")

    # Percentiles by warehouse
    st.subheader("Execution Time Percentiles by Warehouse")

    warehouse_percentiles = successful_queries.groupby('WAREHOUSE_NAME')['EXECUTION_TIME_SECONDS'].agg([
        ('p50', lambda x: x.quantile(0.50)),
        ('p95', lambda x: x.quantile(0.95)),
        ('p99', lambda x: x.quantile(0.99)),
        ('avg', 'mean'),
        ('count', 'count')
    ]).reset_index()

    warehouse_percentiles = warehouse_percentiles.sort_values('p95', ascending=False).head(10)

    fig_percentiles = go.Figure()

    fig_percentiles.add_trace(go.Bar(
        name='p50 (Median)',
        x=warehouse_percentiles['WAREHOUSE_NAME'],
        y=warehouse_percentiles['p50'],
        marker_color='lightblue'
    ))

    fig_percentiles.add_trace(go.Bar(
        name='p95',
        x=warehouse_percentiles['WAREHOUSE_NAME'],
        y=warehouse_percentiles['p95'],
        marker_color='orange'
    ))

    fig_percentiles.add_trace(go.Bar(
        name='p99',
        x=warehouse_percentiles['WAREHOUSE_NAME'],
        y=warehouse_percentiles['p99'],
        marker_color='red'
    ))

    fig_percentiles.update_layout(
        title='Query Execution Time Percentiles by Warehouse',
        xaxis_title='Warehouse',
        yaxis_title='Time (seconds)',
        barmode='group',
        height=500
    )

    st.plotly_chart(fig_percentiles, use_container_width=True)

    # Show percentiles table
    with st.expander("📋 View Detailed Percentiles Table"):
        st.dataframe(
            warehouse_percentiles.round(2),
            use_container_width=True,
            hide_index=True
        )

# =============================================================================
# SECTION 2: COMPILATION VS EXECUTION TIME
# =============================================================================
st.header("⚙️ Compilation vs Execution Time Analysis")
st.markdown("Compare time spent on query compilation versus actual execution")

col1, col2 = st.columns(2)

with col1:
    # Calculate totals
    total_compilation = successful_queries['COMPILATION_TIME_SECONDS'].sum()
    total_execution = successful_queries['EXECUTION_TIME_SECONDS'].sum()

    fig_comp_exec = px.pie(
        values=[total_compilation, total_execution],
        names=['Compilation Time', 'Execution Time'],
        title='Total Time: Compilation vs Execution',
        color_discrete_sequence=['#FF6B6B', '#4ECDC4']
    )
    st.plotly_chart(fig_comp_exec, use_container_width=True)

with col2:
    # Average times
    avg_compilation = successful_queries['COMPILATION_TIME_SECONDS'].mean()
    avg_execution = successful_queries['EXECUTION_TIME_SECONDS'].mean()
    compilation_ratio = (avg_compilation / (avg_compilation + avg_execution) * 100) if (avg_compilation + avg_execution) > 0 else 0

    st.metric("Avg Compilation Time", f"{avg_compilation:.3f}s")
    st.metric("Avg Execution Time", f"{avg_execution:.3f}s")
    st.metric("Compilation Ratio", f"{compilation_ratio:.1f}%")

# Compilation time over time
st.subheader("Compilation vs Execution Time Trends")
successful_queries['START_TIME'] = pd.to_datetime(successful_queries['START_TIME'])
time_series = successful_queries.set_index('START_TIME').resample('1H').agg({
    'COMPILATION_TIME_SECONDS': 'mean',
    'EXECUTION_TIME_SECONDS': 'mean'
}).reset_index()

fig_time_trend = go.Figure()

fig_time_trend.add_trace(go.Scatter(
    x=time_series['START_TIME'],
    y=time_series['COMPILATION_TIME_SECONDS'],
    name='Compilation Time',
    mode='lines+markers',
    line=dict(color='#FF6B6B')
))

fig_time_trend.add_trace(go.Scatter(
    x=time_series['START_TIME'],
    y=time_series['EXECUTION_TIME_SECONDS'],
    name='Execution Time',
    mode='lines+markers',
    line=dict(color='#4ECDC4')
))

fig_time_trend.update_layout(
    title='Average Compilation and Execution Time Over Time',
    xaxis_title='Time',
    yaxis_title='Time (seconds)',
    height=400
)

st.plotly_chart(fig_time_trend, use_container_width=True)

# Queries with high compilation time
st.subheader("Queries with Highest Compilation Time")
high_compilation = successful_queries.nlargest(10, 'COMPILATION_TIME_SECONDS')[
    ['QUERY_ID', 'USER_NAME', 'WAREHOUSE_NAME', 'COMPILATION_TIME_SECONDS', 'EXECUTION_TIME_SECONDS', 'START_TIME']
]
st.dataframe(high_compilation, use_container_width=True, hide_index=True)

# =============================================================================
# SECTION 3: QUEUE WAIT TIME ANALYSIS
# =============================================================================
st.header("⏳ Queue Wait Time Analysis")
st.markdown("Analyze query queue wait times across different queue types")

# Calculate total queue time
successful_queries['TOTAL_QUEUE_TIME_SECONDS'] = (
    successful_queries['QUEUED_PROVISIONING_TIME_SECONDS'].fillna(0) +
    successful_queries['QUEUED_REPAIR_TIME_SECONDS'].fillna(0) +
    successful_queries['QUEUED_OVERLOAD_TIME_SECONDS'].fillna(0)
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    avg_queue_time = successful_queries['TOTAL_QUEUE_TIME_SECONDS'].mean()
    st.metric("Avg Total Queue Time", f"{avg_queue_time:.2f}s")

with col2:
    avg_provisioning = successful_queries['QUEUED_PROVISIONING_TIME_SECONDS'].mean()
    st.metric("Avg Provisioning Queue", f"{avg_provisioning:.2f}s")

with col3:
    avg_repair = successful_queries['QUEUED_REPAIR_TIME_SECONDS'].mean()
    st.metric("Avg Repair Queue", f"{avg_repair:.2f}s")

with col4:
    avg_overload = successful_queries['QUEUED_OVERLOAD_TIME_SECONDS'].mean()
    st.metric("Avg Overload Queue", f"{avg_overload:.2f}s")

# Queue time breakdown
queue_breakdown = pd.DataFrame({
    'Queue Type': ['Provisioning', 'Repair', 'Overload'],
    'Total Time (s)': [
        successful_queries['QUEUED_PROVISIONING_TIME_SECONDS'].sum(),
        successful_queries['QUEUED_REPAIR_TIME_SECONDS'].sum(),
        successful_queries['QUEUED_OVERLOAD_TIME_SECONDS'].sum()
    ]
})

fig_queue = px.bar(
    queue_breakdown,
    x='Queue Type',
    y='Total Time (s)',
    title='Total Queue Wait Time by Type',
    color='Queue Type',
    color_discrete_sequence=['#FFB6C1', '#FFA07A', '#FF6347']
)

st.plotly_chart(fig_queue, use_container_width=True)

# Queue time by warehouse
st.subheader("Queue Wait Times by Warehouse")
warehouse_queue = successful_queries.groupby('WAREHOUSE_NAME').agg({
    'TOTAL_QUEUE_TIME_SECONDS': 'mean',
    'QUEUED_PROVISIONING_TIME_SECONDS': 'mean',
    'QUEUED_REPAIR_TIME_SECONDS': 'mean',
    'QUEUED_OVERLOAD_TIME_SECONDS': 'mean'
}).sort_values('TOTAL_QUEUE_TIME_SECONDS', ascending=False).head(10)

fig_warehouse_queue = go.Figure()

fig_warehouse_queue.add_trace(go.Bar(
    name='Provisioning',
    x=warehouse_queue.index,
    y=warehouse_queue['QUEUED_PROVISIONING_TIME_SECONDS'],
    marker_color='#FFB6C1'
))

fig_warehouse_queue.add_trace(go.Bar(
    name='Repair',
    x=warehouse_queue.index,
    y=warehouse_queue['QUEUED_REPAIR_TIME_SECONDS'],
    marker_color='#FFA07A'
))

fig_warehouse_queue.add_trace(go.Bar(
    name='Overload',
    x=warehouse_queue.index,
    y=warehouse_queue['QUEUED_OVERLOAD_TIME_SECONDS'],
    marker_color='#FF6347'
))

fig_warehouse_queue.update_layout(
    title='Average Queue Wait Times by Warehouse',
    xaxis_title='Warehouse',
    yaxis_title='Time (seconds)',
    barmode='stack',
    height=400
)

st.plotly_chart(fig_warehouse_queue, use_container_width=True)

# Queries with longest queue times
st.subheader("Queries with Longest Queue Wait Times")
queries_with_queue = successful_queries[successful_queries['TOTAL_QUEUE_TIME_SECONDS'] > 0].nlargest(
    10, 'TOTAL_QUEUE_TIME_SECONDS'
)[['QUERY_ID', 'USER_NAME', 'WAREHOUSE_NAME', 'TOTAL_QUEUE_TIME_SECONDS', 'EXECUTION_TIME_SECONDS', 'START_TIME']]

if not queries_with_queue.empty:
    st.dataframe(queries_with_queue, use_container_width=True, hide_index=True)
else:
    st.info("No queries experienced queue wait time in this period")

# =============================================================================
# SECTION 4: SLOWEST QUERIES IDENTIFICATION
# =============================================================================
st.header("🐌 Slowest Queries Identification")
st.markdown("Identify and analyze the slowest performing queries")

# Get slowest queries
slowest_queries = successful_queries.nlargest(20, 'TOTAL_ELAPSED_TIME_SECONDS')

# Create breakdown of time components
fig_slowest = go.Figure()

fig_slowest.add_trace(go.Bar(
    name='Queue Time',
    x=slowest_queries['QUERY_ID'][:10],
    y=slowest_queries['TOTAL_QUEUE_TIME_SECONDS'][:10],
    marker_color='#FF6B6B'
))

fig_slowest.add_trace(go.Bar(
    name='Compilation Time',
    x=slowest_queries['QUERY_ID'][:10],
    y=slowest_queries['COMPILATION_TIME_SECONDS'][:10],
    marker_color='#FFA500'
))

fig_slowest.add_trace(go.Bar(
    name='Execution Time',
    x=slowest_queries['QUERY_ID'][:10],
    y=slowest_queries['EXECUTION_TIME_SECONDS'][:10],
    marker_color='#4ECDC4'
))

fig_slowest.update_layout(
    title='Time Breakdown for Top 10 Slowest Queries',
    xaxis_title='Query ID',
    yaxis_title='Time (seconds)',
    barmode='stack',
    height=500,
    xaxis={'tickangle': -45}
)

st.plotly_chart(fig_slowest, use_container_width=True)

# Detailed slowest queries table
st.subheader("Detailed Slowest Queries")
slowest_details = slowest_queries[[
    'QUERY_ID', 'USER_NAME', 'WAREHOUSE_NAME', 'QUERY_TYPE',
    'TOTAL_ELAPSED_TIME_SECONDS', 'COMPILATION_TIME_SECONDS',
    'EXECUTION_TIME_SECONDS', 'TOTAL_QUEUE_TIME_SECONDS',
    'BYTES_SCANNED', 'ROWS_PRODUCED', 'START_TIME'
]]

st.dataframe(slowest_details, use_container_width=True, hide_index=True)

# Query text for slowest queries
with st.expander("📝 View Query Text for Slowest Queries"):
    for idx, row in slowest_queries.head(5).iterrows():
        st.markdown(f"**Query ID:** `{row['QUERY_ID']}`")
        st.markdown(f"**Execution Time:** {row['TOTAL_ELAPSED_TIME_SECONDS']:.2f}s")
        st.code(row['QUERY_TEXT'][:500] if len(str(row['QUERY_TEXT'])) > 500 else row['QUERY_TEXT'], language='sql')
        st.markdown("---")

# =============================================================================
# SECTION 5: QUERY CONCURRENCY PATTERNS
# =============================================================================
st.header("🔄 Query Concurrency Patterns")
st.markdown("Analyze concurrent query execution patterns and warehouse utilization")

if not concurrency_data.empty:
    concurrency_data['TIME_BUCKET'] = pd.to_datetime(concurrency_data['TIME_BUCKET'])

    # Overall concurrency metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        max_concurrent = concurrency_data['CONCURRENT_QUERIES'].max()
        st.metric("Peak Concurrent Queries", f"{max_concurrent:,}")

    with col2:
        avg_concurrent = concurrency_data['CONCURRENT_QUERIES'].mean()
        st.metric("Avg Concurrent Queries", f"{avg_concurrent:.1f}")

    with col3:
        total_warehouses = concurrency_data['WAREHOUSE_NAME'].nunique()
        st.metric("Active Warehouses", total_warehouses)

    # Concurrency over time by warehouse
    st.subheader("Concurrent Queries Over Time")

    fig_concurrency = px.line(
        concurrency_data,
        x='TIME_BUCKET',
        y='CONCURRENT_QUERIES',
        color='WAREHOUSE_NAME',
        title='Query Concurrency by Warehouse',
        labels={'CONCURRENT_QUERIES': 'Concurrent Queries', 'TIME_BUCKET': 'Time'}
    )

    fig_concurrency.update_layout(height=500)
    st.plotly_chart(fig_concurrency, use_container_width=True)

    # Concurrency heatmap
    st.subheader("Concurrency Heatmap")

    pivot_concurrency = concurrency_data.pivot_table(
        values='CONCURRENT_QUERIES',
        index='WAREHOUSE_NAME',
        columns='TIME_BUCKET',
        aggfunc='sum',
        fill_value=0
    )

    fig_heatmap = go.Figure(data=go.Heatmap(
        z=pivot_concurrency.values,
        x=pivot_concurrency.columns,
        y=pivot_concurrency.index,
        colorscale='YlOrRd',
        hoverongaps=False
    ))

    fig_heatmap.update_layout(
        title='Query Concurrency Heatmap',
        xaxis_title='Time',
        yaxis_title='Warehouse',
        height=400
    )

    st.plotly_chart(fig_heatmap, use_container_width=True)

    # Peak concurrency periods
    st.subheader("Peak Concurrency Periods")

    peak_periods = concurrency_data.nlargest(10, 'CONCURRENT_QUERIES')[
        ['TIME_BUCKET', 'WAREHOUSE_NAME', 'CONCURRENT_QUERIES', 'AVG_EXECUTION_TIME_SECONDS']
    ]

    st.dataframe(peak_periods, use_container_width=True, hide_index=True)
else:
    st.info("No concurrency data available for the selected time range")

# =============================================================================
# SECTION 6: ADDITIONAL PERFORMANCE INSIGHTS
# =============================================================================
st.header("💡 Additional Performance Insights")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Query Type Distribution")
    query_type_dist = successful_queries['QUERY_TYPE'].value_counts().head(10)

    fig_query_type = px.pie(
        values=query_type_dist.values,
        names=query_type_dist.index,
        title='Query Type Distribution'
    )
    st.plotly_chart(fig_query_type, use_container_width=True)

with col2:
    st.subheader("Data Spill Analysis")
    spill_to_disk = successful_queries['BYTES_SPILLED_TO_LOCAL_STORAGE'].sum() / (1024**3)  # GB
    spill_to_remote = successful_queries['BYTES_SPILLED_TO_REMOTE_STORAGE'].sum() / (1024**3)  # GB

    st.metric("Total Spilled to Local Storage", f"{spill_to_disk:.2f} GB")
    st.metric("Total Spilled to Remote Storage", f"{spill_to_remote:.2f} GB")

    if spill_to_disk > 0 or spill_to_remote > 0:
        st.warning("⚠️ Data spilling detected - consider increasing warehouse size for better performance")

# Partition pruning efficiency
st.subheader("Partition Pruning Efficiency")

queries_with_partitions = successful_queries[
    (successful_queries['PARTITIONS_TOTAL'] > 0) &
    (successful_queries['PARTITIONS_SCANNED'] > 0)
].copy()

if not queries_with_partitions.empty:
    queries_with_partitions['PRUNING_EFFICIENCY'] = (
        1 - (queries_with_partitions['PARTITIONS_SCANNED'] / queries_with_partitions['PARTITIONS_TOTAL'])
    ) * 100

    avg_pruning = queries_with_partitions['PRUNING_EFFICIENCY'].mean()
    st.metric("Average Partition Pruning Efficiency", f"{avg_pruning:.1f}%")

    # Queries with poor pruning
    poor_pruning = queries_with_partitions[queries_with_partitions['PRUNING_EFFICIENCY'] < 50].nlargest(
        10, 'PARTITIONS_SCANNED'
    )[['QUERY_ID', 'USER_NAME', 'PARTITIONS_TOTAL', 'PARTITIONS_SCANNED', 'PRUNING_EFFICIENCY', 'EXECUTION_TIME_SECONDS']]

    if not poor_pruning.empty:
        st.warning("⚠️ Queries with Poor Partition Pruning (< 50% efficiency)")
        st.dataframe(poor_pruning, use_container_width=True, hide_index=True)
else:
    st.info("No partition information available")

# Failed queries summary
st.header("❌ Failed Queries Summary")
failed_queries = query_data[query_data['EXECUTION_STATUS'] == 'FAILED']

if not failed_queries.empty:
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Total Failed Queries", len(failed_queries))

        # Error code distribution
        error_dist = failed_queries['ERROR_CODE'].value_counts().head(5)
        fig_errors = px.bar(
            x=error_dist.values,
            y=error_dist.index,
            orientation='h',
            title='Top 5 Error Codes',
            labels={'x': 'Count', 'y': 'Error Code'}
        )
        st.plotly_chart(fig_errors, use_container_width=True)

    with col2:
        # Recent failures
        st.subheader("Recent Failed Queries")
        recent_failures = failed_queries.head(5)[
            ['QUERY_ID', 'USER_NAME', 'ERROR_CODE', 'ERROR_MESSAGE', 'START_TIME']
        ]
        st.dataframe(recent_failures, use_container_width=True, hide_index=True)
else:
    st.success("✅ No failed queries in the selected time range")
