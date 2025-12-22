import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from utils.queries import (
    get_query_history,
    get_warehouse_metering,
    get_login_history,
    get_storage_usage
)

st.set_page_config(
    page_title="Snowflake Monitoring Dashboard",
    page_icon="❄️",
    layout="wide"
)

st.title("❄️ Snowflake Monitoring Dashboard")
st.markdown("Real-time monitoring and analytics for your Snowflake account")

# Sidebar controls
st.sidebar.header("Dashboard Controls")
time_range = st.sidebar.selectbox(
    "Time Range",
    options=[1, 6, 12, 24, 48, 72],
    index=3,
    format_func=lambda x: f"Last {x} hours"
)

refresh = st.sidebar.button("🔄 Refresh Data")

# Create tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Query Performance", "Warehouse Usage", "Login Activity"])

with tab1:
    st.header("Account Overview")

    col1, col2, col3, col4 = st.columns(4)

    # Fetch data
    with st.spinner("Loading account metrics..."):
        query_history = get_query_history(time_range)
        warehouse_metering = get_warehouse_metering(7)
        login_history = get_login_history(time_range)
        storage_usage = get_storage_usage()

    # Display key metrics
    with col1:
        if not query_history.empty:
            total_queries = len(query_history)
            st.metric("Total Queries", f"{total_queries:,}")
        else:
            st.metric("Total Queries", "N/A")

    with col2:
        if not query_history.empty:
            failed_queries = len(query_history[query_history['EXECUTION_STATUS'] != 'SUCCESS'])
            success_rate = ((total_queries - failed_queries) / total_queries * 100) if total_queries > 0 else 0
            st.metric("Success Rate", f"{success_rate:.1f}%")
        else:
            st.metric("Success Rate", "N/A")

    with col3:
        if not warehouse_metering.empty:
            total_credits = warehouse_metering['CREDITS_USED'].sum()
            st.metric("Credits Used (7d)", f"{total_credits:.2f}")
        else:
            st.metric("Credits Used (7d)", "N/A")

    with col4:
        if not login_history.empty:
            failed_logins = len(login_history[login_history['IS_SUCCESS'] == 'NO'])
            st.metric("Failed Logins", f"{failed_logins:,}")
        else:
            st.metric("Failed Logins", "N/A")

    # Storage usage chart
    st.subheader("Storage Usage Trend")
    if not storage_usage.empty:
        fig_storage = px.area(
            storage_usage,
            x='USAGE_DATE',
            y=['STORAGE_GB', 'STAGE_GB', 'FAILSAFE_GB'],
            title='Storage Usage Over Time (GB)',
            labels={'value': 'Storage (GB)', 'variable': 'Type'}
        )
        st.plotly_chart(fig_storage, use_container_width=True)
    else:
        st.info("No storage data available")

with tab2:
    st.header("Query Performance")

    if not query_history.empty:
        col1, col2 = st.columns(2)

        with col1:
            # Average execution time
            avg_time = query_history['EXECUTION_TIME_SECONDS'].mean()
            st.metric("Avg Execution Time", f"{avg_time:.2f}s")

            # Query status distribution
            status_counts = query_history['EXECUTION_STATUS'].value_counts()
            fig_status = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title='Query Status Distribution'
            )
            st.plotly_chart(fig_status, use_container_width=True)

        with col2:
            # Top warehouses by query count
            warehouse_counts = query_history['WAREHOUSE_NAME'].value_counts().head(10)
            fig_warehouse = px.bar(
                x=warehouse_counts.values,
                y=warehouse_counts.index,
                orientation='h',
                title='Top Warehouses by Query Count',
                labels={'x': 'Query Count', 'y': 'Warehouse'}
            )
            st.plotly_chart(fig_warehouse, use_container_width=True)

        # Recent slow queries
        st.subheader("Slowest Queries")
        slow_queries = query_history.nlargest(10, 'EXECUTION_TIME_SECONDS')[
            ['QUERY_ID', 'USER_NAME', 'WAREHOUSE_NAME', 'EXECUTION_TIME_SECONDS', 'START_TIME']
        ]
        st.dataframe(slow_queries, use_container_width=True)
    else:
        st.info("No query history available for the selected time range")

with tab3:
    st.header("Warehouse Credit Usage")

    if not warehouse_metering.empty:
        # Credits over time
        fig_credits = px.line(
            warehouse_metering,
            x='START_TIME',
            y='CREDITS_USED',
            color='WAREHOUSE_NAME',
            title='Credit Usage Over Time',
            labels={'CREDITS_USED': 'Credits', 'START_TIME': 'Time'}
        )
        st.plotly_chart(fig_credits, use_container_width=True)

        # Breakdown by warehouse
        warehouse_credits = warehouse_metering.groupby('WAREHOUSE_NAME')['CREDITS_USED'].sum().sort_values(ascending=False)

        col1, col2 = st.columns(2)

        with col1:
            fig_warehouse_credits = px.bar(
                x=warehouse_credits.values,
                y=warehouse_credits.index,
                orientation='h',
                title='Total Credits by Warehouse',
                labels={'x': 'Credits Used', 'y': 'Warehouse'}
            )
            st.plotly_chart(fig_warehouse_credits, use_container_width=True)

        with col2:
            # Compute vs Cloud Services
            total_compute = warehouse_metering['CREDITS_USED_COMPUTE'].sum()
            total_cloud = warehouse_metering['CREDITS_USED_CLOUD_SERVICES'].sum()

            fig_breakdown = px.pie(
                values=[total_compute, total_cloud],
                names=['Compute', 'Cloud Services'],
                title='Credit Usage Breakdown'
            )
            st.plotly_chart(fig_breakdown, use_container_width=True)
    else:
        st.info("No warehouse metering data available")

with tab4:
    st.header("Login Activity")

    if not login_history.empty:
        col1, col2 = st.columns(2)

        with col1:
            # Success vs failed logins
            login_status = login_history['IS_SUCCESS'].value_counts()
            fig_login = px.pie(
                values=login_status.values,
                names=login_status.index,
                title='Login Success Rate'
            )
            st.plotly_chart(fig_login, use_container_width=True)

        with col2:
            # Top users by login count
            user_logins = login_history['USER_NAME'].value_counts().head(10)
            fig_users = px.bar(
                x=user_logins.values,
                y=user_logins.index,
                orientation='h',
                title='Most Active Users',
                labels={'x': 'Login Count', 'y': 'User'}
            )
            st.plotly_chart(fig_users, use_container_width=True)

        # Recent failed logins
        st.subheader("Recent Failed Logins")
        failed_logins_df = login_history[login_history['IS_SUCCESS'] == 'NO'][
            ['EVENT_TIMESTAMP', 'USER_NAME', 'CLIENT_IP', 'ERROR_MESSAGE']
        ].head(20)

        if not failed_logins_df.empty:
            st.dataframe(failed_logins_df, use_container_width=True)
        else:
            st.success("No failed logins in the selected time range")
    else:
        st.info("No login history available for the selected time range")

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
