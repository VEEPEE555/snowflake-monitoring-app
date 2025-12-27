import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.queries import (
    get_warehouse_credit_breakdown,
    get_warehouse_utilization,
    get_warehouse_state_changes,
    get_warehouse_events,
    get_warehouse_queue_depth,
    get_multi_warehouse_load_distribution
)

st.set_page_config(
    page_title="Compute Resource Monitoring",
    page_icon="💻",
    layout="wide"
)

st.title("💻 Compute Resource Monitoring")
st.markdown("Comprehensive monitoring of Snowflake compute resources, warehouse utilization, and performance metrics")

# Sidebar controls
st.sidebar.header("Filters")
time_range = st.sidebar.selectbox(
    "Time Range",
    options=[1, 6, 12, 24, 48, 72, 168],
    index=3,
    format_func=lambda x: f"Last {x} hours" if x < 168 else "Last 7 days"
)

credit_days = st.sidebar.selectbox(
    "Credit Analysis Period",
    options=[1, 3, 7, 14, 30],
    index=2,
    format_func=lambda x: f"Last {x} days"
)

refresh = st.sidebar.button("🔄 Refresh Data")

# Create tabs for different monitoring aspects
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💰 Credit Consumption",
    "📊 Utilization %",
    "🔄 Auto-Suspend/Resume",
    "⏳ Queue Depth",
    "⚖️ Load Distribution"
])

# Tab 1: Warehouse Credit Consumption
with tab1:
    st.header("Warehouse Credit Consumption Analysis")

    with st.spinner("Loading credit consumption data..."):
        credit_data = get_warehouse_credit_breakdown(credit_days)

    if not credit_data.empty:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)

        total_credits = credit_data['TOTAL_CREDITS'].sum()
        total_compute = credit_data['COMPUTE_CREDITS'].sum()
        total_cloud = credit_data['CLOUD_SERVICES_CREDITS'].sum()
        avg_hourly = credit_data.groupby('HOUR')['TOTAL_CREDITS'].sum().mean()

        with col1:
            st.metric("Total Credits Used", f"{total_credits:.2f}")

        with col2:
            st.metric("Compute Credits", f"{total_compute:.2f}")

        with col3:
            st.metric("Cloud Services Credits", f"{total_cloud:.2f}")

        with col4:
            st.metric("Avg Credits/Hour", f"{avg_hourly:.2f}")

        # Credits over time
        st.subheader("Credit Consumption Over Time")
        fig_credits_time = px.line(
            credit_data,
            x='HOUR',
            y='TOTAL_CREDITS',
            color='WAREHOUSE_NAME',
            title='Hourly Credit Consumption by Warehouse',
            labels={'TOTAL_CREDITS': 'Credits Used', 'HOUR': 'Time'}
        )
        fig_credits_time.update_layout(height=500)
        st.plotly_chart(fig_credits_time, use_container_width=True)

        # Credit breakdown
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Credits by Warehouse")
            warehouse_credits = credit_data.groupby('WAREHOUSE_NAME').agg({
                'TOTAL_CREDITS': 'sum',
                'COMPUTE_CREDITS': 'sum',
                'CLOUD_SERVICES_CREDITS': 'sum'
            }).sort_values('TOTAL_CREDITS', ascending=False)

            fig_warehouse = px.bar(
                warehouse_credits,
                y=warehouse_credits.index,
                x='TOTAL_CREDITS',
                orientation='h',
                title='Total Credits by Warehouse',
                labels={'TOTAL_CREDITS': 'Credits', 'y': 'Warehouse'}
            )
            st.plotly_chart(fig_warehouse, use_container_width=True)

        with col2:
            st.subheader("Compute vs Cloud Services")
            credit_breakdown = pd.DataFrame({
                'Type': ['Compute', 'Cloud Services'],
                'Credits': [total_compute, total_cloud]
            })

            fig_breakdown = px.pie(
                credit_breakdown,
                values='Credits',
                names='Type',
                title='Credit Distribution',
                color_discrete_sequence=['#636EFA', '#EF553B']
            )
            st.plotly_chart(fig_breakdown, use_container_width=True)

        # Stacked area chart
        st.subheader("Credit Consumption Breakdown Over Time")
        fig_stacked = go.Figure()

        for warehouse in credit_data['WAREHOUSE_NAME'].unique():
            warehouse_data = credit_data[credit_data['WAREHOUSE_NAME'] == warehouse]
            fig_stacked.add_trace(go.Scatter(
                x=warehouse_data['HOUR'],
                y=warehouse_data['TOTAL_CREDITS'],
                name=warehouse,
                stackgroup='one',
                mode='lines'
            ))

        fig_stacked.update_layout(
            title='Stacked Credit Consumption by Warehouse',
            xaxis_title='Time',
            yaxis_title='Credits Used',
            height=400
        )
        st.plotly_chart(fig_stacked, use_container_width=True)

    else:
        st.warning("No credit consumption data available for the selected time range")

# Tab 2: Warehouse Utilization Percentage
with tab2:
    st.header("Warehouse Utilization Percentage")

    with st.spinner("Loading utilization data..."):
        utilization_data = get_warehouse_utilization(time_range)

    if not utilization_data.empty:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)

        avg_utilization = utilization_data['UTILIZATION_PERCENTAGE'].mean()
        max_utilization = utilization_data['UTILIZATION_PERCENTAGE'].max()
        total_queries = utilization_data['QUERY_COUNT'].sum()
        warehouses = utilization_data['WAREHOUSE_NAME'].nunique()

        with col1:
            st.metric("Avg Utilization", f"{avg_utilization:.1f}%")

        with col2:
            st.metric("Peak Utilization", f"{max_utilization:.1f}%")

        with col3:
            st.metric("Total Queries", f"{total_queries:,}")

        with col4:
            st.metric("Active Warehouses", warehouses)

        # Utilization over time
        st.subheader("Utilization Percentage Over Time")
        fig_util_time = px.line(
            utilization_data,
            x='HOUR',
            y='UTILIZATION_PERCENTAGE',
            color='WAREHOUSE_NAME',
            title='Warehouse Utilization % by Hour',
            labels={'UTILIZATION_PERCENTAGE': 'Utilization %', 'HOUR': 'Time'}
        )
        fig_util_time.add_hline(y=100, line_dash="dash", line_color="red",
                                annotation_text="100% Capacity")
        fig_util_time.update_layout(height=500)
        st.plotly_chart(fig_util_time, use_container_width=True)

        # Average utilization by warehouse
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Average Utilization by Warehouse")
            avg_by_warehouse = utilization_data.groupby('WAREHOUSE_NAME')['UTILIZATION_PERCENTAGE'].mean().sort_values(ascending=False)

            # Color code by utilization level
            colors = ['red' if x > 80 else 'orange' if x > 60 else 'green' for x in avg_by_warehouse.values]

            fig_avg_util = go.Figure(go.Bar(
                x=avg_by_warehouse.values,
                y=avg_by_warehouse.index,
                orientation='h',
                marker=dict(color=colors)
            ))
            fig_avg_util.update_layout(
                title='Average Utilization % by Warehouse',
                xaxis_title='Utilization %',
                yaxis_title='Warehouse'
            )
            st.plotly_chart(fig_avg_util, use_container_width=True)

        with col2:
            st.subheader("Query Count vs Utilization")
            warehouse_summary = utilization_data.groupby('WAREHOUSE_NAME').agg({
                'QUERY_COUNT': 'sum',
                'UTILIZATION_PERCENTAGE': 'mean'
            }).reset_index()

            fig_scatter = px.scatter(
                warehouse_summary,
                x='QUERY_COUNT',
                y='UTILIZATION_PERCENTAGE',
                size='QUERY_COUNT',
                color='UTILIZATION_PERCENTAGE',
                hover_data=['WAREHOUSE_NAME'],
                title='Query Volume vs Utilization',
                labels={'QUERY_COUNT': 'Total Queries', 'UTILIZATION_PERCENTAGE': 'Avg Utilization %'},
                color_continuous_scale='RdYlGn_r'
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        # Utilization heatmap
        st.subheader("Utilization Heatmap")
        pivot_util = utilization_data.pivot_table(
            values='UTILIZATION_PERCENTAGE',
            index='WAREHOUSE_NAME',
            columns='HOUR',
            aggfunc='mean',
            fill_value=0
        )

        fig_heatmap = go.Figure(data=go.Heatmap(
            z=pivot_util.values,
            x=pivot_util.columns,
            y=pivot_util.index,
            colorscale='RdYlGn_r',
            zmid=50,
            zmin=0,
            zmax=100,
            hoverongaps=False,
            colorbar=dict(title="Utilization %")
        ))

        fig_heatmap.update_layout(
            title='Warehouse Utilization Heatmap',
            xaxis_title='Hour',
            yaxis_title='Warehouse',
            height=400
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

    else:
        st.warning("No utilization data available for the selected time range")

# Tab 3: Auto-Suspend/Resume Patterns
with tab3:
    st.header("Auto-Suspend/Resume Patterns")

    with st.spinner("Loading warehouse state change data..."):
        state_changes = get_warehouse_state_changes(time_range)
        warehouse_events = get_warehouse_events(time_range)

    if not state_changes.empty:
        # Calculate session statistics
        state_changes['DURATION_MINUTES'] = (
            pd.to_datetime(state_changes['END_TIME']) -
            pd.to_datetime(state_changes['START_TIME'])
        ).dt.total_seconds() / 60

        # Key metrics
        col1, col2, col3, col4 = st.columns(4)

        total_sessions = len(state_changes)
        avg_session_duration = state_changes['DURATION_MINUTES'].mean()
        total_idle_time = state_changes['DURATION_MINUTES'].sum()
        avg_credits_per_session = state_changes['CREDITS_USED'].mean()

        with col1:
            st.metric("Total Sessions", f"{total_sessions:,}")

        with col2:
            st.metric("Avg Session Duration", f"{avg_session_duration:.1f} min")

        with col3:
            st.metric("Total Runtime", f"{total_idle_time/60:.1f} hrs")

        with col4:
            st.metric("Avg Credits/Session", f"{avg_credits_per_session:.4f}")

        # Session timeline
        st.subheader("Warehouse Session Timeline")

        # Create timeline visualization
        timeline_data = []
        for _, row in state_changes.head(50).iterrows():
            timeline_data.append({
                'Warehouse': row['WAREHOUSE_NAME'],
                'Start': row['START_TIME'],
                'End': row['END_TIME'],
                'Credits': row['CREDITS_USED']
            })

        if timeline_data:
            timeline_df = pd.DataFrame(timeline_data)

            fig_timeline = px.timeline(
                timeline_df,
                x_start='Start',
                x_end='End',
                y='Warehouse',
                color='Credits',
                title='Recent Warehouse Active Sessions (Last 50)',
                labels={'Credits': 'Credits Used'}
            )
            fig_timeline.update_layout(height=500)
            st.plotly_chart(fig_timeline, use_container_width=True)

        # Session duration distribution
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Session Duration Distribution")
            fig_duration = px.histogram(
                state_changes,
                x='DURATION_MINUTES',
                nbins=30,
                title='Distribution of Session Durations',
                labels={'DURATION_MINUTES': 'Duration (minutes)', 'count': 'Frequency'}
            )
            st.plotly_chart(fig_duration, use_container_width=True)

        with col2:
            st.subheader("Sessions by Warehouse")
            sessions_by_warehouse = state_changes['WAREHOUSE_NAME'].value_counts().head(10)

            fig_sessions = px.bar(
                x=sessions_by_warehouse.values,
                y=sessions_by_warehouse.index,
                orientation='h',
                title='Number of Sessions by Warehouse',
                labels={'x': 'Session Count', 'y': 'Warehouse'}
            )
            st.plotly_chart(fig_sessions, use_container_width=True)

        # Average session duration by warehouse
        st.subheader("Average Session Metrics by Warehouse")
        session_metrics = state_changes.groupby('WAREHOUSE_NAME').agg({
            'DURATION_MINUTES': 'mean',
            'CREDITS_USED': 'mean',
            'CREDITS_USED_COMPUTE': 'mean',
            'CREDITS_USED_CLOUD_SERVICES': 'mean'
        }).round(2).sort_values('DURATION_MINUTES', ascending=False)

        st.dataframe(session_metrics, use_container_width=True)

    else:
        st.warning("No warehouse state change data available for the selected time range")

    # Warehouse load history events
    if not warehouse_events.empty:
        st.subheader("Warehouse Load Events")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Average Running Load")
            avg_running = warehouse_events.groupby('WAREHOUSE_NAME')['AVG_RUNNING'].mean().sort_values(ascending=False)

            fig_running = px.bar(
                x=avg_running.values,
                y=avg_running.index,
                orientation='h',
                title='Average Running Load by Warehouse',
                labels={'x': 'Avg Running Load', 'y': 'Warehouse'}
            )
            st.plotly_chart(fig_running, use_container_width=True)

        with col2:
            st.subheader("Average Queued Load")
            avg_queued = warehouse_events.groupby('WAREHOUSE_NAME')['AVG_QUEUED_LOAD'].mean().sort_values(ascending=False)

            fig_queued = px.bar(
                x=avg_queued.values,
                y=avg_queued.index,
                orientation='h',
                title='Average Queued Load by Warehouse',
                labels={'x': 'Avg Queued Load', 'y': 'Warehouse'},
                color=avg_queued.values,
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_queued, use_container_width=True)

# Tab 4: Warehouse Queuing Depth
with tab4:
    st.header("Warehouse Queue Depth Analysis")

    with st.spinner("Loading queue depth data..."):
        queue_data = get_warehouse_queue_depth(time_range)

    if not queue_data.empty:
        # Filter out rows with no queuing
        queued_data = queue_data[
            (queue_data['QUEUED_OVERLOAD_COUNT'] > 0) |
            (queue_data['QUEUED_PROVISIONING_COUNT'] > 0) |
            (queue_data['QUEUED_REPAIR_COUNT'] > 0)
        ]

        # Key metrics
        col1, col2, col3, col4 = st.columns(4)

        total_queued = queue_data[
            ['QUEUED_OVERLOAD_COUNT', 'QUEUED_PROVISIONING_COUNT', 'QUEUED_REPAIR_COUNT']
        ].sum().sum()

        avg_overload_time = queue_data['AVG_QUEUE_OVERLOAD_SECONDS'].mean()
        max_overload_time = queue_data['MAX_QUEUE_OVERLOAD_SECONDS'].max()
        affected_warehouses = queue_data[queue_data['QUEUED_OVERLOAD_COUNT'] > 0]['WAREHOUSE_NAME'].nunique()

        with col1:
            st.metric("Total Queued Queries", f"{int(total_queued):,}")

        with col2:
            st.metric("Avg Queue Time", f"{avg_overload_time:.2f}s")

        with col3:
            st.metric("Max Queue Time", f"{max_overload_time:.2f}s")

        with col4:
            st.metric("Warehouses with Queuing", affected_warehouses)

        if not queued_data.empty:
            # Queue counts over time
            st.subheader("Queuing Events Over Time")

            queue_summary = queued_data.groupby('TIME_BUCKET').agg({
                'QUEUED_OVERLOAD_COUNT': 'sum',
                'QUEUED_PROVISIONING_COUNT': 'sum',
                'QUEUED_REPAIR_COUNT': 'sum'
            }).reset_index()

            fig_queue_time = go.Figure()
            fig_queue_time.add_trace(go.Scatter(
                x=queue_summary['TIME_BUCKET'],
                y=queue_summary['QUEUED_OVERLOAD_COUNT'],
                name='Overload',
                mode='lines+markers',
                line=dict(color='red')
            ))
            fig_queue_time.add_trace(go.Scatter(
                x=queue_summary['TIME_BUCKET'],
                y=queue_summary['QUEUED_PROVISIONING_COUNT'],
                name='Provisioning',
                mode='lines+markers',
                line=dict(color='orange')
            ))
            fig_queue_time.add_trace(go.Scatter(
                x=queue_summary['TIME_BUCKET'],
                y=queue_summary['QUEUED_REPAIR_COUNT'],
                name='Repair',
                mode='lines+markers',
                line=dict(color='yellow')
            ))

            fig_queue_time.update_layout(
                title='Queued Queries by Type Over Time',
                xaxis_title='Time',
                yaxis_title='Queued Query Count',
                height=500
            )
            st.plotly_chart(fig_queue_time, use_container_width=True)

            # Queue analysis by warehouse
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Overload Queuing by Warehouse")
                overload_by_warehouse = queued_data.groupby('WAREHOUSE_NAME')['QUEUED_OVERLOAD_COUNT'].sum().sort_values(ascending=False).head(10)

                fig_overload = px.bar(
                    x=overload_by_warehouse.values,
                    y=overload_by_warehouse.index,
                    orientation='h',
                    title='Queries Queued Due to Overload',
                    labels={'x': 'Queued Query Count', 'y': 'Warehouse'},
                    color=overload_by_warehouse.values,
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig_overload, use_container_width=True)

            with col2:
                st.subheader("Average Queue Wait Time")
                avg_wait_by_warehouse = queued_data.groupby('WAREHOUSE_NAME')['AVG_QUEUE_OVERLOAD_SECONDS'].mean().sort_values(ascending=False).head(10)

                fig_wait = px.bar(
                    x=avg_wait_by_warehouse.values,
                    y=avg_wait_by_warehouse.index,
                    orientation='h',
                    title='Average Queue Wait Time by Warehouse',
                    labels={'x': 'Avg Wait Time (seconds)', 'y': 'Warehouse'},
                    color=avg_wait_by_warehouse.values,
                    color_continuous_scale='Oranges'
                )
                st.plotly_chart(fig_wait, use_container_width=True)

            # Detailed queue metrics table
            st.subheader("Detailed Queue Metrics by Warehouse")
            queue_summary_table = queued_data.groupby('WAREHOUSE_NAME').agg({
                'QUEUED_OVERLOAD_COUNT': 'sum',
                'QUEUED_PROVISIONING_COUNT': 'sum',
                'QUEUED_REPAIR_COUNT': 'sum',
                'AVG_QUEUE_OVERLOAD_SECONDS': 'mean',
                'MAX_QUEUE_OVERLOAD_SECONDS': 'max'
            }).round(2).sort_values('QUEUED_OVERLOAD_COUNT', ascending=False)

            st.dataframe(queue_summary_table, use_container_width=True)

        else:
            st.success("✅ No queuing detected in the selected time range - all warehouses are performing well!")

    else:
        st.warning("No queue depth data available for the selected time range")

# Tab 5: Multi-Warehouse Load Distribution
with tab5:
    st.header("Multi-Warehouse Load Distribution")

    with st.spinner("Loading load distribution data..."):
        distribution_data = get_multi_warehouse_load_distribution(time_range)

    if not distribution_data.empty:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)

        total_queries = distribution_data['QUERY_COUNT'].sum()
        total_users = distribution_data['UNIQUE_USERS'].sum()
        warehouses = distribution_data['WAREHOUSE_NAME'].nunique()
        avg_query_time = distribution_data['AVG_EXECUTION_TIME_SECONDS'].mean()

        with col1:
            st.metric("Total Queries", f"{total_queries:,}")

        with col2:
            st.metric("Total Unique Users", f"{total_users:,}")

        with col3:
            st.metric("Active Warehouses", warehouses)

        with col4:
            st.metric("Avg Query Time", f"{avg_query_time:.2f}s")

        # Query distribution across warehouses
        st.subheader("Query Distribution Across Warehouses")

        warehouse_query_dist = distribution_data.groupby('WAREHOUSE_NAME')['QUERY_COUNT'].sum().sort_values(ascending=False)

        fig_dist = px.pie(
            values=warehouse_query_dist.values,
            names=warehouse_query_dist.index,
            title='Query Distribution by Warehouse',
            hole=0.4
        )
        st.plotly_chart(fig_dist, use_container_width=True)

        # Load over time
        st.subheader("Query Load Over Time by Warehouse")

        fig_load_time = px.area(
            distribution_data,
            x='HOUR',
            y='QUERY_COUNT',
            color='WAREHOUSE_NAME',
            title='Query Volume Over Time',
            labels={'QUERY_COUNT': 'Query Count', 'HOUR': 'Time'}
        )
        fig_load_time.update_layout(height=500)
        st.plotly_chart(fig_load_time, use_container_width=True)

        # Warehouse comparison metrics
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Total Queries by Warehouse Size")
            size_distribution = distribution_data.groupby(['WAREHOUSE_SIZE', 'WAREHOUSE_NAME'])['QUERY_COUNT'].sum().reset_index()

            fig_size = px.bar(
                size_distribution,
                x='WAREHOUSE_SIZE',
                y='QUERY_COUNT',
                color='WAREHOUSE_NAME',
                title='Query Distribution by Warehouse Size',
                labels={'QUERY_COUNT': 'Total Queries', 'WAREHOUSE_SIZE': 'Warehouse Size'},
                barmode='group'
            )
            st.plotly_chart(fig_size, use_container_width=True)

        with col2:
            st.subheader("Data Scanned by Warehouse")
            bytes_by_warehouse = distribution_data.groupby('WAREHOUSE_NAME')['TOTAL_BYTES_SCANNED'].sum().sort_values(ascending=False)
            bytes_gb = bytes_by_warehouse / (1024**3)  # Convert to GB

            fig_bytes = px.bar(
                x=bytes_gb.values,
                y=bytes_gb.index,
                orientation='h',
                title='Total Data Scanned (GB) by Warehouse',
                labels={'x': 'Data Scanned (GB)', 'y': 'Warehouse'}
            )
            st.plotly_chart(fig_bytes, use_container_width=True)

        # Load balance score
        st.subheader("Load Balance Analysis")

        warehouse_totals = distribution_data.groupby('WAREHOUSE_NAME')['QUERY_COUNT'].sum()
        avg_load = warehouse_totals.mean()
        std_load = warehouse_totals.std()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Average Load", f"{avg_load:.0f} queries")

        with col2:
            st.metric("Std Deviation", f"{std_load:.0f}")

        with col3:
            balance_score = 100 - min((std_load / avg_load * 100), 100) if avg_load > 0 else 0
            st.metric("Balance Score", f"{balance_score:.1f}/100")
            st.caption("100 = perfectly balanced, 0 = highly imbalanced")

        # Warehouse comparison table
        st.subheader("Comprehensive Warehouse Metrics")
        warehouse_summary = distribution_data.groupby('WAREHOUSE_NAME').agg({
            'QUERY_COUNT': 'sum',
            'AVG_EXECUTION_TIME_SECONDS': 'mean',
            'TOTAL_EXECUTION_TIME_SECONDS': 'sum',
            'TOTAL_BYTES_SCANNED': 'sum',
            'UNIQUE_USERS': 'sum'
        }).round(2)

        warehouse_summary['TOTAL_BYTES_SCANNED_GB'] = (warehouse_summary['TOTAL_BYTES_SCANNED'] / (1024**3)).round(2)
        warehouse_summary = warehouse_summary.drop('TOTAL_BYTES_SCANNED', axis=1)
        warehouse_summary = warehouse_summary.sort_values('QUERY_COUNT', ascending=False)

        st.dataframe(warehouse_summary, use_container_width=True)

        # Hourly load distribution heatmap
        st.subheader("Hourly Load Distribution Heatmap")
        pivot_load = distribution_data.pivot_table(
            values='QUERY_COUNT',
            index='WAREHOUSE_NAME',
            columns='HOUR',
            aggfunc='sum',
            fill_value=0
        )

        fig_heatmap = go.Figure(data=go.Heatmap(
            z=pivot_load.values,
            x=pivot_load.columns,
            y=pivot_load.index,
            colorscale='YlOrRd',
            hoverongaps=False,
            colorbar=dict(title="Query Count")
        ))

        fig_heatmap.update_layout(
            title='Query Count Heatmap by Warehouse and Hour',
            xaxis_title='Hour',
            yaxis_title='Warehouse',
            height=400
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

    else:
        st.warning("No load distribution data available for the selected time range")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    <small>Compute Resource Monitoring • Data from ACCOUNT_USAGE views • 45min-3hr latency</small>
    </div>
    """,
    unsafe_allow_html=True
)
