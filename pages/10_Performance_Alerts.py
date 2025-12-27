import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.queries import (
    get_long_running_queries,
    get_cache_metrics,
    get_warehouse_queue_depth,
    get_detailed_query_performance
)

st.set_page_config(
    page_title="Performance Alerts",
    page_icon="⚠️",
    layout="wide"
)

st.title("⚠️ Performance Alerts & Monitoring")
st.markdown("Real-time performance monitoring, alerts, and optimization recommendations")

# Sidebar controls
st.sidebar.header("Alert Configuration")
time_range = st.sidebar.selectbox(
    "Time Range",
    options=[1, 6, 12, 24, 48],
    index=3,
    format_func=lambda x: f"Last {x} hours"
)

long_query_threshold = st.sidebar.slider(
    "Long Query Threshold (minutes)",
    min_value=1,
    max_value=60,
    value=5,
    step=1
)

refresh = st.sidebar.button("🔄 Refresh Data")

# Fetch data
with st.spinner("Loading performance alerts..."):
    long_queries = get_long_running_queries(time_range, long_query_threshold)
    cache_metrics = get_cache_metrics(time_range)
    queue_depth = get_warehouse_queue_depth(time_range)
    query_performance = get_detailed_query_performance(time_range)

# =============================================================================
# SECTION 1: ALERT SUMMARY DASHBOARD
# =============================================================================
st.header("🚨 Alert Summary")

alerts = []

# Check for long-running queries
if not long_queries.empty:
    alerts.append({
        'type': 'Long-Running Queries',
        'severity': 'High',
        'count': len(long_queries),
        'message': f"{len(long_queries)} queries exceeded {long_query_threshold} minutes"
    })

# Check for warehouse overload
if not queue_depth.empty:
    high_queue = queue_depth[queue_depth['AVG_QUEUE_SECONDS'] > 10]
    if not high_queue.empty:
        alerts.append({
            'type': 'Warehouse Overload',
            'severity': 'High',
            'count': len(high_queue),
            'message': f"{len(high_queue)} warehouse periods with queue time > 10s"
        })

# Check for data spilling
if not query_performance.empty:
    spill_queries = query_performance[
        (query_performance['BYTES_SPILLED_TO_LOCAL_STORAGE'] > 0) |
        (query_performance['BYTES_SPILLED_TO_REMOTE_STORAGE'] > 0)
    ]
    if not spill_queries.empty:
        alerts.append({
            'type': 'Data Spilling',
            'severity': 'Medium',
            'count': len(spill_queries),
            'message': f"{len(spill_queries)} queries spilled data to disk"
        })

# Check for poor cache hit rate
if not cache_metrics.empty:
    low_cache = cache_metrics[cache_metrics['CACHE_HIT_RATE'] < 20]
    if not low_cache.empty:
        alerts.append({
            'type': 'Low Cache Hit Rate',
            'severity': 'Medium',
            'count': len(low_cache),
            'message': f"{len(low_cache)} periods with cache hit rate < 20%"
        })

# Display alerts
if alerts:
    st.error(f"⚠️ **{len(alerts)} Active Alerts**")

    cols = st.columns(len(alerts))

    for idx, alert in enumerate(alerts):
        with cols[idx]:
            severity_color = {
                'High': '🔴',
                'Medium': '🟡',
                'Low': '🟢'
            }

            st.metric(
                f"{severity_color[alert['severity']]} {alert['type']}",
                alert['count'],
                delta=alert['message']
            )

else:
    st.success("✅ **No Active Alerts** - System performing well")

# =============================================================================
# SECTION 2: LONG-RUNNING QUERIES
# =============================================================================
st.header("⏱️ Long-Running Queries")

if not long_queries.empty:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Long-Running Queries", len(long_queries))

    with col2:
        avg_duration = long_queries['ELAPSED_MINUTES'].mean()
        st.metric("Avg Duration", f"{avg_duration:.2f} min")

    with col3:
        max_duration = long_queries['ELAPSED_MINUTES'].max()
        st.metric("Longest Query", f"{max_duration:.2f} min")

    # Long queries by warehouse
    st.subheader("Long Queries by Warehouse")

    warehouse_long = long_queries.groupby('WAREHOUSE_NAME').agg({
        'QUERY_ID': 'count',
        'ELAPSED_MINUTES': 'mean'
    }).reset_index()
    warehouse_long.columns = ['WAREHOUSE_NAME', 'QUERY_COUNT', 'AVG_DURATION']
    warehouse_long = warehouse_long.sort_values('QUERY_COUNT', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_wh_long = px.bar(
            warehouse_long,
            x='QUERY_COUNT',
            y='WAREHOUSE_NAME',
            orientation='h',
            title='Long-Running Queries by Warehouse',
            labels={'QUERY_COUNT': 'Query Count', 'WAREHOUSE_NAME': 'Warehouse'},
            color='QUERY_COUNT',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_wh_long, use_container_width=True)

    with col2:
        fig_duration = px.bar(
            warehouse_long,
            x='AVG_DURATION',
            y='WAREHOUSE_NAME',
            orientation='h',
            title='Average Duration by Warehouse',
            labels={'AVG_DURATION': 'Avg Duration (min)', 'WAREHOUSE_NAME': 'Warehouse'}
        )
        st.plotly_chart(fig_duration, use_container_width=True)

    # Long queries by user
    st.subheader("Long Queries by User")

    user_long = long_queries.groupby('USER_NAME').size().sort_values(ascending=False).head(15)

    fig_user_long = px.bar(
        x=user_long.values,
        y=user_long.index,
        orientation='h',
        title='Top 15 Users with Long-Running Queries',
        labels={'x': 'Query Count', 'y': 'User'},
        color=user_long.values,
        color_continuous_scale='Oranges'
    )
    st.plotly_chart(fig_user_long, use_container_width=True)

    # Timeline of long queries
    st.subheader("Long Query Timeline")

    long_queries['START_TIME'] = pd.to_datetime(long_queries['START_TIME'])
    timeline = long_queries.set_index('START_TIME').resample('30min').size().reset_index()
    timeline.columns = ['TIME', 'COUNT']

    fig_timeline = px.area(
        timeline,
        x='TIME',
        y='COUNT',
        title='Long-Running Queries Over Time',
        labels={'COUNT': 'Query Count', 'TIME': 'Time'},
        color_discrete_sequence=['red']
    )
    st.plotly_chart(fig_timeline, use_container_width=True)

    # Detailed table
    st.subheader("Long-Running Queries Detail")

    display_cols = ['START_TIME', 'USER_NAME', 'WAREHOUSE_NAME', 'QUERY_TYPE',
                    'ELAPSED_MINUTES', 'EXECUTION_STATUS']

    if 'END_TIME' in long_queries.columns:
        display_cols.append('END_TIME')

    st.dataframe(
        long_queries[display_cols].sort_values('ELAPSED_MINUTES', ascending=False),
        use_container_width=True,
        hide_index=True
    )

    # Query text for slowest queries
    with st.expander("📝 View Query Text"):
        for idx, row in long_queries.nlargest(5, 'ELAPSED_MINUTES').iterrows():
            st.markdown(f"**Query ID:** `{row['QUERY_ID']}`")
            st.markdown(f"**Duration:** {row['ELAPSED_MINUTES']:.2f} minutes")
            st.markdown(f"**User:** {row['USER_NAME']} | **Warehouse:** {row['WAREHOUSE_NAME']}")
            if pd.notna(row.get('QUERY_TEXT')):
                st.code(str(row['QUERY_TEXT'])[:500], language='sql')
            st.markdown("---")

else:
    st.success(f"✅ No queries exceeded {long_query_threshold} minutes threshold")

# =============================================================================
# SECTION 3: WAREHOUSE OVERLOAD DETECTION
# =============================================================================
st.header("🔥 Warehouse Overload Detection")

if not queue_depth.empty:
    queue_depth['TIME_BUCKET'] = pd.to_datetime(queue_depth['TIME_BUCKET'])

    # Metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        total_queued = queue_depth['QUERIES_IN_QUEUE'].sum()
        st.metric("Total Queued Queries", f"{total_queued:,}")

    with col2:
        avg_wait = queue_depth['AVG_QUEUE_SECONDS'].mean()
        st.metric("Avg Queue Wait", f"{avg_wait:.2f}s")

    with col3:
        max_wait = queue_depth['MAX_QUEUE_SECONDS'].max()
        st.metric("Max Queue Wait", f"{max_wait:.2f}s")

    # Overloaded warehouses
    st.subheader("Overloaded Warehouses")

    warehouse_overload = queue_depth.groupby('WAREHOUSE_NAME').agg({
        'QUERIES_IN_QUEUE': 'sum',
        'AVG_QUEUE_SECONDS': 'mean',
        'MAX_QUEUE_SECONDS': 'max'
    }).sort_values('AVG_QUEUE_SECONDS', ascending=False)

    overloaded = warehouse_overload[warehouse_overload['AVG_QUEUE_SECONDS'] > 5]

    if not overloaded.empty:
        st.warning(f"⚠️ {len(overloaded)} warehouses with average queue time > 5 seconds")

        col1, col2 = st.columns(2)

        with col1:
            fig_overload = px.bar(
                x=overloaded['AVG_QUEUE_SECONDS'],
                y=overloaded.index,
                orientation='h',
                title='Average Queue Wait Time',
                labels={'x': 'Avg Wait (seconds)', 'y': 'Warehouse'},
                color=overloaded['AVG_QUEUE_SECONDS'],
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_overload, use_container_width=True)

        with col2:
            st.dataframe(
                overloaded.round(2),
                use_container_width=True
            )

        st.info("**Recommendation:** Consider scaling up these warehouses or enabling multi-cluster mode")
    else:
        st.success("✅ No warehouse overload detected")

    # Queue depth heatmap
    st.subheader("Queue Depth Heatmap")

    pivot_queue = queue_depth.pivot_table(
        values='QUERIES_IN_QUEUE',
        index='WAREHOUSE_NAME',
        columns='TIME_BUCKET',
        aggfunc='sum',
        fill_value=0
    )

    fig_heatmap = go.Figure(data=go.Heatmap(
        z=pivot_queue.values,
        x=pivot_queue.columns,
        y=pivot_queue.index,
        colorscale='YlOrRd',
        hoverongaps=False
    ))

    fig_heatmap.update_layout(
        title='Queue Depth Heatmap',
        xaxis_title='Time',
        yaxis_title='Warehouse',
        height=400
    )

    st.plotly_chart(fig_heatmap, use_container_width=True)

else:
    st.success("✅ No queuing detected - queries executing immediately")

# =============================================================================
# SECTION 4: QUERY RESULT CACHE HIT RATES
# =============================================================================
st.header("💾 Query Result Cache Performance")

if not cache_metrics.empty:
    cache_metrics['HOUR'] = pd.to_datetime(cache_metrics['HOUR'])

    # Overall cache metrics
    total_queries = cache_metrics['TOTAL_QUERIES'].sum()
    total_cache_hits = cache_metrics['CACHE_HITS'].sum()
    overall_hit_rate = (total_cache_hits / total_queries * 100) if total_queries > 0 else 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Overall Cache Hit Rate", f"{overall_hit_rate:.1f}%")

    with col2:
        st.metric("Total Queries", f"{total_queries:,}")

    with col3:
        st.metric("Cache Hits", f"{total_cache_hits:,}")

    # Cache hit rate over time
    st.subheader("Cache Hit Rate Trend")

    fig_cache_trend = px.line(
        cache_metrics,
        x='HOUR',
        y='CACHE_HIT_RATE',
        color='WAREHOUSE_NAME',
        title='Cache Hit Rate Over Time',
        labels={'CACHE_HIT_RATE': 'Cache Hit Rate (%)', 'HOUR': 'Time'}
    )

    # Add reference line at 50%
    fig_cache_trend.add_hline(
        y=50,
        line_dash="dash",
        line_color="orange",
        annotation_text="50% Target"
    )

    fig_cache_trend.update_layout(height=500)
    st.plotly_chart(fig_cache_trend, use_container_width=True)

    # Cache performance by warehouse
    st.subheader("Cache Performance by Warehouse")

    warehouse_cache = cache_metrics.groupby('WAREHOUSE_NAME').agg({
        'TOTAL_QUERIES': 'sum',
        'CACHE_HITS': 'sum'
    }).reset_index()

    warehouse_cache['HIT_RATE'] = (
        warehouse_cache['CACHE_HITS'] / warehouse_cache['TOTAL_QUERIES'] * 100
    )

    warehouse_cache = warehouse_cache.sort_values('HIT_RATE', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_wh_cache = px.bar(
            warehouse_cache,
            x='HIT_RATE',
            y='WAREHOUSE_NAME',
            orientation='h',
            title='Cache Hit Rate by Warehouse',
            labels={'HIT_RATE': 'Hit Rate (%)', 'WAREHOUSE_NAME': 'Warehouse'},
            color='HIT_RATE',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig_wh_cache, use_container_width=True)

    with col2:
        # Warehouses with low cache hit rate
        low_cache = warehouse_cache[warehouse_cache['HIT_RATE'] < 30]

        if not low_cache.empty:
            st.warning(f"⚠️ {len(low_cache)} warehouses with cache hit rate < 30%")
            st.dataframe(
                low_cache[['WAREHOUSE_NAME', 'HIT_RATE', 'TOTAL_QUERIES']].round(2),
                use_container_width=True,
                hide_index=True
            )
            st.info("**Tip:** Low cache hit rates may indicate unique queries or rapidly changing data")
        else:
            st.success("✅ All warehouses have healthy cache hit rates")

else:
    st.info("No cache metrics available")

# =============================================================================
# SECTION 5: DATA SPILLING ANALYSIS
# =============================================================================
st.header("💽 Data Spilling Analysis")

if not query_performance.empty:
    # Filter queries with spilling
    spill_queries = query_performance[
        (query_performance['BYTES_SPILLED_TO_LOCAL_STORAGE'] > 0) |
        (query_performance['BYTES_SPILLED_TO_REMOTE_STORAGE'] > 0)
    ].copy()

    if not spill_queries.empty:
        spill_queries['LOCAL_SPILL_GB'] = spill_queries['BYTES_SPILLED_TO_LOCAL_STORAGE'] / (1024**3)
        spill_queries['REMOTE_SPILL_GB'] = spill_queries['BYTES_SPILLED_TO_REMOTE_STORAGE'] / (1024**3)
        spill_queries['TOTAL_SPILL_GB'] = spill_queries['LOCAL_SPILL_GB'] + spill_queries['REMOTE_SPILL_GB']

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Queries with Spilling", len(spill_queries))

        with col2:
            total_local_spill = spill_queries['LOCAL_SPILL_GB'].sum()
            st.metric("Total Local Spill", f"{total_local_spill:.2f} GB")

        with col3:
            total_remote_spill = spill_queries['REMOTE_SPILL_GB'].sum()
            st.metric("Total Remote Spill", f"{total_remote_spill:.2f} GB")

        # Spilling by warehouse
        st.subheader("Data Spilling by Warehouse")

        warehouse_spill = spill_queries.groupby('WAREHOUSE_NAME').agg({
            'QUERY_ID': 'count',
            'LOCAL_SPILL_GB': 'sum',
            'REMOTE_SPILL_GB': 'sum',
            'TOTAL_SPILL_GB': 'sum'
        }).sort_values('TOTAL_SPILL_GB', ascending=False).reset_index()

        warehouse_spill.columns = ['WAREHOUSE_NAME', 'SPILL_QUERIES', 'LOCAL_GB', 'REMOTE_GB', 'TOTAL_GB']

        col1, col2 = st.columns(2)

        with col1:
            fig_spill = px.bar(
                warehouse_spill,
                x='TOTAL_GB',
                y='WAREHOUSE_NAME',
                orientation='h',
                title='Total Data Spilled by Warehouse',
                labels={'TOTAL_GB': 'Total Spilled (GB)', 'WAREHOUSE_NAME': 'Warehouse'},
                color='TOTAL_GB',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_spill, use_container_width=True)

        with col2:
            fig_spill_type = go.Figure()

            fig_spill_type.add_trace(go.Bar(
                name='Local Spill',
                x=warehouse_spill['WAREHOUSE_NAME'][:10],
                y=warehouse_spill['LOCAL_GB'][:10],
                marker_color='orange'
            ))

            fig_spill_type.add_trace(go.Bar(
                name='Remote Spill',
                x=warehouse_spill['WAREHOUSE_NAME'][:10],
                y=warehouse_spill['REMOTE_GB'][:10],
                marker_color='red'
            ))

            fig_spill_type.update_layout(
                title='Spill Type Breakdown (Top 10 Warehouses)',
                xaxis_title='Warehouse',
                yaxis_title='Spilled (GB)',
                barmode='stack'
            )

            st.plotly_chart(fig_spill_type, use_container_width=True)

        # Worst spilling queries
        st.subheader("Queries with Most Data Spilling")

        worst_spill = spill_queries.nlargest(20, 'TOTAL_SPILL_GB')[[
            'QUERY_ID', 'USER_NAME', 'WAREHOUSE_NAME', 'WAREHOUSE_SIZE',
            'LOCAL_SPILL_GB', 'REMOTE_SPILL_GB', 'TOTAL_SPILL_GB', 'EXECUTION_TIME_SECONDS'
        ]]

        st.dataframe(worst_spill.round(2), use_container_width=True, hide_index=True)

        st.warning("⚠️ **Data spilling indicates insufficient warehouse memory**")
        st.info("**Recommendation:** Consider increasing warehouse size for queries with significant spilling")

    else:
        st.success("✅ No data spilling detected - warehouses are properly sized")

else:
    st.info("No query performance data available for spilling analysis")

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
