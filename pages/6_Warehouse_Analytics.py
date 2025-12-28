import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.queries import (
    get_warehouse_utilization,
    get_warehouse_load_events,
    get_warehouse_queue_depth
)

st.set_page_config(
    page_title="Warehouse Analytics",
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 Advanced Warehouse Analytics")
st.markdown("Deep dive into warehouse utilization, auto-suspend patterns, and efficiency metrics")

# Sidebar controls
st.sidebar.header("Filters")
time_range_days = st.sidebar.selectbox(
    "Time Range",
    options=[1, 3, 7, 14, 30],
    index=2,
    format_func=lambda x: f"Last {x} days"
)

time_range_hours = st.sidebar.selectbox(
    "Events Time Range",
    options=[6, 12, 24, 48, 72],
    index=2,
    format_func=lambda x: f"Last {x} hours"
)

refresh = st.sidebar.button("🔄 Refresh Data")

# Fetch data
with st.spinner("Loading warehouse analytics..."):
    utilization_data = get_warehouse_utilization(time_range_days)
    load_events = get_warehouse_load_events(time_range_hours)
    queue_depth = get_warehouse_queue_depth(time_range_hours)

# =============================================================================
# SECTION 1: WAREHOUSE UTILIZATION
# =============================================================================
st.header("📊 Warehouse Utilization Analysis")

if not utilization_data.empty:
    # Calculate overall metrics
    avg_utilization = utilization_data['UTILIZATION_PCT'].mean()
    total_credits = utilization_data['CREDITS_USED'].sum()
    total_compute = utilization_data['CREDITS_COMPUTE'].sum()
    total_cloud = utilization_data['CREDITS_CLOUD'].sum()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Avg Utilization", f"{avg_utilization:.1f}%")

    with col2:
        st.metric("Total Credits", f"{total_credits:.2f}")

    with col3:
        st.metric("Compute Credits", f"{total_compute:.2f}")

    with col4:
        st.metric("Cloud Services Credits", f"{total_cloud:.2f}")

    # Utilization over time
    st.subheader("Warehouse Utilization Over Time")
    utilization_data['HOUR'] = pd.to_datetime(utilization_data['HOUR'])

    fig_utilization = px.line(
        utilization_data,
        x='HOUR',
        y='UTILIZATION_PCT',
        color='WAREHOUSE_NAME',
        title='Warehouse Utilization Percentage Over Time',
        labels={'UTILIZATION_PCT': 'Utilization (%)', 'HOUR': 'Time'}
    )

    # Add horizontal line at 100% utilization
    fig_utilization.add_hline(
        y=100,
        line_dash="dash",
        line_color="red",
        annotation_text="100% Utilization"
    )

    fig_utilization.update_layout(height=500)
    st.plotly_chart(fig_utilization, use_container_width=True)

    # Average utilization by warehouse
    st.subheader("Average Utilization by Warehouse")

    warehouse_avg_util = utilization_data.groupby('WAREHOUSE_NAME').agg({
        'UTILIZATION_PCT': 'mean',
        'CREDITS_USED': 'sum',
        'QUERY_COUNT': 'sum'
    }).sort_values('UTILIZATION_PCT', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_util_bar = px.bar(
            x=warehouse_avg_util['UTILIZATION_PCT'],
            y=warehouse_avg_util.index,
            orientation='h',
            title='Average Utilization by Warehouse',
            labels={'x': 'Avg Utilization (%)', 'y': 'Warehouse'},
            color=warehouse_avg_util['UTILIZATION_PCT'],
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig_util_bar, use_container_width=True)

    with col2:
        fig_credits_pie = px.pie(
            values=warehouse_avg_util['CREDITS_USED'],
            names=warehouse_avg_util.index,
            title='Credit Distribution by Warehouse'
        )
        st.plotly_chart(fig_credits_pie, use_container_width=True)

    # Idle time analysis (low utilization periods)
    st.subheader("⏸️ Idle Time Analysis")
    st.markdown("Periods where warehouses are running but underutilized (< 20% utilization)")

    idle_periods = utilization_data[
        (utilization_data['UTILIZATION_PCT'] < 20) &
        (utilization_data['CREDITS_USED'] > 0)
    ]

    if not idle_periods.empty:
        col1, col2 = st.columns(2)

        with col1:
            idle_hours = len(idle_periods)
            wasted_credits = idle_periods['CREDITS_USED'].sum()
            st.metric("Idle Hours", f"{idle_hours:,}")
            st.metric("Credits in Idle Periods", f"{wasted_credits:.2f}")

        with col2:
            idle_by_warehouse = idle_periods.groupby('WAREHOUSE_NAME')['CREDITS_USED'].sum().sort_values(ascending=False)
            fig_idle = px.bar(
                x=idle_by_warehouse.values,
                y=idle_by_warehouse.index,
                orientation='h',
                title='Credits Used During Idle Periods',
                labels={'x': 'Credits', 'y': 'Warehouse'},
                color=idle_by_warehouse.values,
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_idle, use_container_width=True)

        # Show idle periods table
        with st.expander("📋 View Detailed Idle Periods"):
            idle_details = idle_periods.sort_values('HOUR', ascending=False)[[
                'WAREHOUSE_NAME', 'HOUR', 'UTILIZATION_PCT', 'CREDITS_USED', 'QUERY_COUNT'
            ]]
            st.dataframe(idle_details, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No significant idle periods detected")

    # Right-sizing recommendations
    st.subheader("💡 Right-Sizing Recommendations")

    warehouse_stats = utilization_data.groupby('WAREHOUSE_NAME').agg({
        'UTILIZATION_PCT': 'mean',
        'CREDITS_USED': 'sum',
        'QUERY_COUNT': 'sum'
    }).reset_index()

    recommendations = []
    for _, row in warehouse_stats.iterrows():
        warehouse = row['WAREHOUSE_NAME']
        util = row['UTILIZATION_PCT']
        credits = row['CREDITS_USED']

        if util < 30:
            recommendations.append({
                'Warehouse': warehouse,
                'Avg Utilization': f"{util:.1f}%",
                'Credits Used': f"{credits:.2f}",
                'Recommendation': '🔻 Consider downsizing or increasing auto-suspend time',
                'Priority': 'High'
            })
        elif util > 80:
            recommendations.append({
                'Warehouse': warehouse,
                'Avg Utilization': f"{util:.1f}%",
                'Credits Used': f"{credits:.2f}",
                'Recommendation': '🔺 Consider upsizing for better performance',
                'Priority': 'Medium'
            })
        elif util > 50 and util <= 80:
            recommendations.append({
                'Warehouse': warehouse,
                'Avg Utilization': f"{util:.1f}%",
                'Credits Used': f"{credits:.2f}",
                'Recommendation': '✅ Well-sized',
                'Priority': 'Low'
            })

    if recommendations:
        recommendations_df = pd.DataFrame(recommendations)
        st.dataframe(recommendations_df, use_container_width=True, hide_index=True)

else:
    st.warning("No utilization data available")

# =============================================================================
# SECTION 2: AUTO-SUSPEND/RESUME PATTERNS
# =============================================================================
st.header("🔄 Auto-Suspend/Resume Patterns")

if not load_events.empty:
    load_events['TIMESTAMP'] = pd.to_datetime(load_events['TIMESTAMP'])

    # Event counts
    event_counts = load_events['EVENT_NAME'].value_counts()

    col1, col2, col3 = st.columns(3)

    with col1:
        total_events = len(load_events)
        st.metric("Total Events", f"{total_events:,}")

    with col2:
        suspend_count = len(load_events[load_events['EVENT_NAME'] == 'SUSPEND_WAREHOUSE'])
        st.metric("Suspend Events", f"{suspend_count:,}")

    with col3:
        resume_count = len(load_events[load_events['EVENT_NAME'] == 'RESUME_WAREHOUSE'])
        st.metric("Resume Events", f"{resume_count:,}")

    # Event timeline
    st.subheader("Warehouse Events Timeline")

    events_over_time = load_events.set_index('TIMESTAMP').resample('30min')['EVENT_NAME'].count().reset_index()

    fig_events = px.line(
        events_over_time,
        x='TIMESTAMP',
        y='EVENT_NAME',
        title='Warehouse Events Over Time',
        labels={'EVENT_NAME': 'Event Count', 'TIMESTAMP': 'Time'}
    )
    fig_events.update_layout(height=400)
    st.plotly_chart(fig_events, use_container_width=True)

    # Events by warehouse
    st.subheader("Events by Warehouse")

    col1, col2 = st.columns(2)

    with col1:
        warehouse_events = load_events.groupby('WAREHOUSE_NAME')['EVENT_NAME'].count().sort_values(ascending=False).head(10)

        fig_wh_events = px.bar(
            x=warehouse_events.values,
            y=warehouse_events.index,
            orientation='h',
            title='Total Events by Warehouse',
            labels={'x': 'Event Count', 'y': 'Warehouse'}
        )
        st.plotly_chart(fig_wh_events, use_container_width=True)

    with col2:
        event_type_dist = load_events['EVENT_NAME'].value_counts()

        fig_event_types = px.pie(
            values=event_type_dist.values,
            names=event_type_dist.index,
            title='Event Type Distribution'
        )
        st.plotly_chart(fig_event_types, use_container_width=True)

    # Recent events
    st.subheader("Recent Warehouse Events")
    recent_events = load_events.sort_values('TIMESTAMP', ascending=False).head(50)[[
        'TIMESTAMP', 'WAREHOUSE_NAME', 'EVENT_NAME', 'EVENT_STATE', 'EVENT_REASON', 'USER_NAME'
    ]]
    st.dataframe(recent_events, use_container_width=True, hide_index=True)

else:
    st.info("No warehouse load events available for the selected time range")

# =============================================================================
# SECTION 3: WAREHOUSE QUEUE DEPTH
# =============================================================================
st.header("⏳ Warehouse Queue Depth Analysis")

if not queue_depth.empty:
    queue_depth['TIME_BUCKET'] = pd.to_datetime(queue_depth['TIME_BUCKET'])

    # Queue metrics
    total_queued = queue_depth['QUERIES_IN_QUEUE'].sum()
    avg_queue_time = queue_depth['AVG_QUEUE_SECONDS'].mean()
    max_queue_time = queue_depth['MAX_QUEUE_SECONDS'].max()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Queued Queries", f"{total_queued:,}")

    with col2:
        st.metric("Avg Queue Wait Time", f"{avg_queue_time:.2f}s")

    with col3:
        st.metric("Max Queue Wait Time", f"{max_queue_time:.2f}s")

    # Queue depth over time
    st.subheader("Queue Depth Over Time")

    fig_queue = px.line(
        queue_depth,
        x='TIME_BUCKET',
        y='QUERIES_IN_QUEUE',
        color='WAREHOUSE_NAME',
        title='Queued Queries Over Time',
        labels={'QUERIES_IN_QUEUE': 'Queries in Queue', 'TIME_BUCKET': 'Time'}
    )
    fig_queue.update_layout(height=500)
    st.plotly_chart(fig_queue, use_container_width=True)

    # Queue times by warehouse
    st.subheader("Average Queue Times by Warehouse")

    warehouse_queue = queue_depth.groupby('WAREHOUSE_NAME').agg({
        'QUERIES_IN_QUEUE': 'sum',
        'AVG_QUEUE_SECONDS': 'mean',
        'MAX_QUEUE_SECONDS': 'max'
    }).sort_values('AVG_QUEUE_SECONDS', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_queue_avg = px.bar(
            x=warehouse_queue['AVG_QUEUE_SECONDS'],
            y=warehouse_queue.index,
            orientation='h',
            title='Average Queue Wait Time by Warehouse',
            labels={'x': 'Avg Wait Time (seconds)', 'y': 'Warehouse'},
            color=warehouse_queue['AVG_QUEUE_SECONDS'],
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_queue_avg, use_container_width=True)

    with col2:
        fig_queue_count = px.bar(
            x=warehouse_queue['QUERIES_IN_QUEUE'],
            y=warehouse_queue.index,
            orientation='h',
            title='Total Queued Queries by Warehouse',
            labels={'x': 'Queued Queries', 'y': 'Warehouse'}
        )
        st.plotly_chart(fig_queue_count, use_container_width=True)

    # Warehouses with high queue times (potential overload)
    st.subheader("⚠️ Potential Warehouse Overload")

    high_queue = warehouse_queue[warehouse_queue['AVG_QUEUE_SECONDS'] > 5]

    if not high_queue.empty:
        st.warning("The following warehouses have average queue wait times > 5 seconds:")
        st.dataframe(high_queue.round(2), use_container_width=True)
        st.markdown("**Recommendation:** Consider scaling up these warehouses or enabling multi-cluster mode")
    else:
        st.success("✅ No warehouse overload detected")

else:
    st.info("No queue depth data available - queries are executing without queuing")

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
