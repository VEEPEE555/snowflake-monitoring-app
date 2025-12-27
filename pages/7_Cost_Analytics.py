import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from utils.queries import (
    get_credit_consumption_detailed,
    get_cost_by_user,
    get_cost_by_database,
    get_storage_cost_breakdown
)

st.set_page_config(
    page_title="Cost Analytics",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Cost Analytics & Budget Monitoring")
st.markdown("Track credit consumption, analyze costs by dimension, and monitor budget trends")

# Sidebar controls
st.sidebar.header("Configuration")
time_range = st.sidebar.selectbox(
    "Time Range",
    options=[7, 14, 30, 60, 90],
    index=2,
    format_func=lambda x: f"Last {x} days"
)

# Cost configuration
credit_price = st.sidebar.number_input(
    "Credit Price ($)",
    min_value=0.01,
    max_value=10.0,
    value=2.0,
    step=0.1,
    help="Enter your Snowflake credit price per credit"
)

monthly_budget = st.sidebar.number_input(
    "Monthly Budget ($)",
    min_value=0,
    max_value=1000000,
    value=10000,
    step=1000,
    help="Enter your monthly budget for Snowflake costs"
)

refresh = st.sidebar.button("🔄 Refresh Data")

# Fetch data
with st.spinner("Loading cost analytics..."):
    credit_data = get_credit_consumption_detailed(time_range)
    user_costs = get_cost_by_user(min(time_range, 30))
    database_costs = get_cost_by_database(min(time_range, 30))
    storage_costs = get_storage_cost_breakdown()

# =============================================================================
# SECTION 1: OVERALL COST SUMMARY
# =============================================================================
st.header("📊 Cost Summary")

if not credit_data.empty:
    total_credits = credit_data['TOTAL_CREDITS'].sum()
    total_compute = credit_data['COMPUTE_CREDITS'].sum()
    total_cloud = credit_data['CLOUD_SERVICE_CREDITS'].sum()
    total_cost = total_credits * credit_price

    # Calculate daily average for budget projection
    days_in_period = credit_data['DATE'].nunique()
    daily_avg_cost = total_cost / days_in_period if days_in_period > 0 else 0
    projected_monthly_cost = daily_avg_cost * 30

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Credits Used", f"{total_credits:,.2f}")
        st.caption(f"${total_cost:,.2f}")

    with col2:
        st.metric("Compute Credits", f"{total_compute:,.2f}")
        st.caption(f"${total_compute * credit_price:,.2f}")

    with col3:
        st.metric("Cloud Service Credits", f"{total_cloud:,.2f}")
        st.caption(f"${total_cloud * credit_price:,.2f}")

    with col4:
        budget_utilization = (projected_monthly_cost / monthly_budget * 100) if monthly_budget > 0 else 0
        st.metric(
            "Projected Monthly Cost",
            f"${projected_monthly_cost:,.2f}",
            delta=f"{budget_utilization:.1f}% of budget"
        )

    # Budget alert
    if budget_utilization > 100:
        st.error(f"⚠️ **Budget Alert:** Projected monthly cost (${projected_monthly_cost:,.2f}) exceeds budget (${monthly_budget:,.2f}) by {budget_utilization - 100:.1f}%")
    elif budget_utilization > 80:
        st.warning(f"⚠️ **Budget Warning:** Using {budget_utilization:.1f}% of monthly budget")
    else:
        st.success(f"✅ Budget on track: {budget_utilization:.1f}% of monthly budget")

    # Daily cost trend
    st.subheader("Daily Cost Trend")

    credit_data['DATE'] = pd.to_datetime(credit_data['DATE'])
    daily_costs = credit_data.groupby('DATE').agg({
        'TOTAL_CREDITS': 'sum',
        'COMPUTE_CREDITS': 'sum',
        'CLOUD_SERVICE_CREDITS': 'sum'
    }).reset_index()

    daily_costs['TOTAL_COST'] = daily_costs['TOTAL_CREDITS'] * credit_price
    daily_costs['COMPUTE_COST'] = daily_costs['COMPUTE_CREDITS'] * credit_price
    daily_costs['CLOUD_COST'] = daily_costs['CLOUD_SERVICE_CREDITS'] * credit_price

    # Calculate 7-day moving average
    daily_costs['MA_7'] = daily_costs['TOTAL_COST'].rolling(window=7, min_periods=1).mean()

    fig_daily = go.Figure()

    fig_daily.add_trace(go.Scatter(
        x=daily_costs['DATE'],
        y=daily_costs['TOTAL_COST'],
        name='Daily Cost',
        mode='lines+markers',
        line=dict(color='#1f77b4')
    ))

    fig_daily.add_trace(go.Scatter(
        x=daily_costs['DATE'],
        y=daily_costs['MA_7'],
        name='7-Day Moving Average',
        mode='lines',
        line=dict(color='red', dash='dash')
    ))

    # Add daily budget line
    daily_budget = monthly_budget / 30
    fig_daily.add_hline(
        y=daily_budget,
        line_dash="dot",
        line_color="green",
        annotation_text=f"Daily Budget: ${daily_budget:.2f}"
    )

    fig_daily.update_layout(
        title='Daily Cost Trend',
        xaxis_title='Date',
        yaxis_title='Cost ($)',
        height=500
    )

    st.plotly_chart(fig_daily, use_container_width=True)

    # Weekly and monthly aggregation
    st.subheader("Cost Breakdown by Period")

    col1, col2 = st.columns(2)

    with col1:
        # Weekly costs
        credit_data['WEEK'] = credit_data['DATE'].dt.to_period('W').dt.start_time
        weekly_costs = credit_data.groupby('WEEK')['TOTAL_CREDITS'].sum() * credit_price

        fig_weekly = px.bar(
            x=weekly_costs.index,
            y=weekly_costs.values,
            title='Weekly Cost Trend',
            labels={'x': 'Week', 'y': 'Cost ($)'}
        )
        st.plotly_chart(fig_weekly, use_container_width=True)

    with col2:
        # Monthly costs (if data available)
        if time_range >= 60:
            credit_data['MONTH'] = credit_data['DATE'].dt.to_period('M').dt.start_time
            monthly_costs = credit_data.groupby('MONTH')['TOTAL_CREDITS'].sum() * credit_price

            fig_monthly = px.bar(
                x=monthly_costs.index,
                y=monthly_costs.values,
                title='Monthly Cost Trend',
                labels={'x': 'Month', 'y': 'Cost ($)'},
                color=monthly_costs.values,
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
        else:
            st.info("Extend time range to 60+ days to see monthly breakdown")

    # Cost anomaly detection
    st.subheader("🔍 Cost Anomaly Detection")

    # Calculate mean and standard deviation
    mean_cost = daily_costs['TOTAL_COST'].mean()
    std_cost = daily_costs['TOTAL_COST'].std()
    anomaly_threshold = mean_cost + (2 * std_cost)  # 2 standard deviations

    anomalies = daily_costs[daily_costs['TOTAL_COST'] > anomaly_threshold]

    if not anomalies.empty:
        st.warning(f"⚠️ Found {len(anomalies)} anomalous cost days (> ${anomaly_threshold:.2f})")

        col1, col2 = st.columns([2, 1])

        with col1:
            fig_anomaly = go.Figure()

            # Normal days
            normal_days = daily_costs[daily_costs['TOTAL_COST'] <= anomaly_threshold]
            fig_anomaly.add_trace(go.Scatter(
                x=normal_days['DATE'],
                y=normal_days['TOTAL_COST'],
                mode='markers',
                name='Normal',
                marker=dict(color='blue', size=8)
            ))

            # Anomaly days
            fig_anomaly.add_trace(go.Scatter(
                x=anomalies['DATE'],
                y=anomalies['TOTAL_COST'],
                mode='markers',
                name='Anomaly',
                marker=dict(color='red', size=12, symbol='x')
            ))

            # Threshold line
            fig_anomaly.add_hline(
                y=anomaly_threshold,
                line_dash="dash",
                line_color="orange",
                annotation_text=f"Anomaly Threshold: ${anomaly_threshold:.2f}"
            )

            fig_anomaly.update_layout(
                title='Cost Anomaly Detection',
                xaxis_title='Date',
                yaxis_title='Cost ($)',
                height=400
            )

            st.plotly_chart(fig_anomaly, use_container_width=True)

        with col2:
            st.dataframe(
                anomalies[['DATE', 'TOTAL_COST']].sort_values('TOTAL_COST', ascending=False),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.success("✅ No cost anomalies detected")

else:
    st.warning("No credit consumption data available")

# =============================================================================
# SECTION 2: COST BY WAREHOUSE
# =============================================================================
st.header("🏭 Cost by Warehouse")

if not credit_data.empty:
    warehouse_costs = credit_data.groupby('WAREHOUSE_NAME').agg({
        'TOTAL_CREDITS': 'sum',
        'COMPUTE_CREDITS': 'sum',
        'CLOUD_SERVICE_CREDITS': 'sum'
    }).reset_index()

    warehouse_costs['TOTAL_COST'] = warehouse_costs['TOTAL_CREDITS'] * credit_price
    warehouse_costs['COMPUTE_COST'] = warehouse_costs['COMPUTE_CREDITS'] * credit_price
    warehouse_costs['CLOUD_COST'] = warehouse_costs['CLOUD_SERVICE_CREDITS'] * credit_price

    warehouse_costs = warehouse_costs.sort_values('TOTAL_COST', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_wh_cost = px.bar(
            warehouse_costs,
            x='TOTAL_COST',
            y='WAREHOUSE_NAME',
            orientation='h',
            title='Total Cost by Warehouse',
            labels={'TOTAL_COST': 'Cost ($)', 'WAREHOUSE_NAME': 'Warehouse'},
            color='TOTAL_COST',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_wh_cost, use_container_width=True)

    with col2:
        fig_wh_pie = px.pie(
            warehouse_costs,
            values='TOTAL_COST',
            names='WAREHOUSE_NAME',
            title='Cost Distribution by Warehouse'
        )
        st.plotly_chart(fig_wh_pie, use_container_width=True)

    # Warehouse cost breakdown
    st.subheader("Warehouse Cost Breakdown (Compute vs Cloud Services)")

    fig_wh_breakdown = go.Figure()

    fig_wh_breakdown.add_trace(go.Bar(
        name='Compute',
        x=warehouse_costs['WAREHOUSE_NAME'][:10],
        y=warehouse_costs['COMPUTE_COST'][:10],
        marker_color='#1f77b4'
    ))

    fig_wh_breakdown.add_trace(go.Bar(
        name='Cloud Services',
        x=warehouse_costs['WAREHOUSE_NAME'][:10],
        y=warehouse_costs['CLOUD_COST'][:10],
        marker_color='#ff7f0e'
    ))

    fig_wh_breakdown.update_layout(
        title='Top 10 Warehouses: Compute vs Cloud Services Cost',
        xaxis_title='Warehouse',
        yaxis_title='Cost ($)',
        barmode='stack',
        height=500
    )

    st.plotly_chart(fig_wh_breakdown, use_container_width=True)

    # Cost table
    with st.expander("📋 View Detailed Warehouse Costs"):
        st.dataframe(
            warehouse_costs.round(2),
            use_container_width=True,
            hide_index=True
        )

# =============================================================================
# SECTION 3: COST BY USER
# =============================================================================
st.header("👤 Cost by User")

if not user_costs.empty:
    user_costs['COST'] = user_costs['CREDITS_USED'] * credit_price

    user_summary = user_costs.groupby('USER_NAME').agg({
        'COST': 'sum',
        'QUERY_COUNT': 'sum',
        'GB_SCANNED': 'sum'
    }).sort_values('COST', ascending=False).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        fig_user_cost = px.bar(
            user_summary.head(15),
            x='COST',
            y='USER_NAME',
            orientation='h',
            title='Top 15 Users by Cost',
            labels={'COST': 'Cost ($)', 'USER_NAME': 'User'},
            color='COST',
            color_continuous_scale='Greens'
        )
        st.plotly_chart(fig_user_cost, use_container_width=True)

    with col2:
        fig_user_pie = px.pie(
            user_summary.head(10),
            values='COST',
            names='USER_NAME',
            title='Top 10 Users Cost Distribution'
        )
        st.plotly_chart(fig_user_pie, use_container_width=True)

    # Cost per query analysis
    st.subheader("Cost Efficiency by User")

    user_summary['COST_PER_QUERY'] = user_summary['COST'] / user_summary['QUERY_COUNT']

    fig_efficiency = px.scatter(
        user_summary.head(20),
        x='QUERY_COUNT',
        y='COST_PER_QUERY',
        size='COST',
        hover_data=['USER_NAME'],
        title='User Efficiency: Cost per Query vs Query Volume',
        labels={
            'QUERY_COUNT': 'Total Queries',
            'COST_PER_QUERY': 'Cost per Query ($)',
            'COST': 'Total Cost'
        }
    )

    st.plotly_chart(fig_efficiency, use_container_width=True)

    with st.expander("📋 View Detailed User Costs"):
        st.dataframe(
            user_summary.round(2),
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("No user cost data available")

# =============================================================================
# SECTION 4: COST BY DATABASE
# =============================================================================
st.header("🗄️ Cost by Database")

if not database_costs.empty:
    database_costs['COST'] = database_costs['CREDITS_USED'] * credit_price
    database_costs = database_costs.sort_values('COST', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_db_cost = px.bar(
            database_costs.head(15),
            x='COST',
            y='DATABASE_NAME',
            orientation='h',
            title='Cost by Database',
            labels={'COST': 'Cost ($)', 'DATABASE_NAME': 'Database'},
            color='COST',
            color_continuous_scale='Purples'
        )
        st.plotly_chart(fig_db_cost, use_container_width=True)

    with col2:
        database_costs['COST_PER_QUERY'] = database_costs['COST'] / database_costs['QUERY_COUNT']

        fig_db_efficiency = px.bar(
            database_costs.head(15),
            x='COST_PER_QUERY',
            y='DATABASE_NAME',
            orientation='h',
            title='Cost per Query by Database',
            labels={'COST_PER_QUERY': 'Cost per Query ($)', 'DATABASE_NAME': 'Database'}
        )
        st.plotly_chart(fig_db_efficiency, use_container_width=True)

    with st.expander("📋 View Detailed Database Costs"):
        st.dataframe(
            database_costs.round(2),
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("No database cost data available")

# =============================================================================
# SECTION 5: STORAGE COSTS
# =============================================================================
st.header("💾 Storage Costs")

if not storage_costs.empty:
    storage_costs['USAGE_DATE'] = pd.to_datetime(storage_costs['USAGE_DATE'])

    latest_storage = storage_costs.iloc[0]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Data Storage", f"{latest_storage['DATA_STORAGE_GB']:.2f} GB")
        st.caption(f"${latest_storage['DAILY_DATA_COST']:.2f}/day")

    with col2:
        st.metric("Stage Storage", f"{latest_storage['STAGE_STORAGE_GB']:.2f} GB")
        st.caption(f"${latest_storage['DAILY_STAGE_COST']:.2f}/day")

    with col3:
        st.metric("Fail-safe Storage", f"{latest_storage['FAILSAFE_STORAGE_GB']:.2f} GB")
        st.caption(f"${latest_storage['DAILY_FAILSAFE_COST']:.2f}/day")

    with col4:
        total_storage_cost = (
            latest_storage['DAILY_DATA_COST'] +
            latest_storage['DAILY_STAGE_COST'] +
            latest_storage['DAILY_FAILSAFE_COST']
        )
        monthly_storage_cost = total_storage_cost * 30
        st.metric("Projected Monthly", f"${monthly_storage_cost:.2f}")

    # Storage cost trends
    st.subheader("Storage Cost Trends")

    storage_costs['TOTAL_DAILY_COST'] = (
        storage_costs['DAILY_DATA_COST'] +
        storage_costs['DAILY_STAGE_COST'] +
        storage_costs['DAILY_FAILSAFE_COST']
    )

    fig_storage = px.area(
        storage_costs,
        x='USAGE_DATE',
        y=['DAILY_DATA_COST', 'DAILY_STAGE_COST', 'DAILY_FAILSAFE_COST'],
        title='Daily Storage Costs by Type',
        labels={'value': 'Cost ($)', 'USAGE_DATE': 'Date', 'variable': 'Storage Type'}
    )

    st.plotly_chart(fig_storage, use_container_width=True)

    # Storage breakdown
    col1, col2 = st.columns(2)

    with col1:
        latest_breakdown = {
            'Data': latest_storage['DATA_STORAGE_GB'],
            'Stage': latest_storage['STAGE_STORAGE_GB'],
            'Fail-safe': latest_storage['FAILSAFE_STORAGE_GB']
        }

        fig_storage_pie = px.pie(
            values=list(latest_breakdown.values()),
            names=list(latest_breakdown.keys()),
            title='Storage Distribution (GB)'
        )
        st.plotly_chart(fig_storage_pie, use_container_width=True)

    with col2:
        cost_breakdown = {
            'Data': latest_storage['DAILY_DATA_COST'],
            'Stage': latest_storage['DAILY_STAGE_COST'],
            'Fail-safe': latest_storage['DAILY_FAILSAFE_COST']
        }

        fig_cost_pie = px.pie(
            values=list(cost_breakdown.values()),
            names=list(cost_breakdown.keys()),
            title='Daily Cost Distribution'
        )
        st.plotly_chart(fig_cost_pie, use_container_width=True)

else:
    st.info("No storage cost data available")

# =============================================================================
# COST FORECAST
# =============================================================================
st.header("📈 Cost Forecast")

if not daily_costs.empty and len(daily_costs) >= 7:
    st.subheader("Next 7 Days Projection")

    # Simple linear regression for forecast
    from sklearn.linear_model import LinearRegression

    # Prepare data
    X = np.arange(len(daily_costs)).reshape(-1, 1)
    y = daily_costs['TOTAL_COST'].values

    # Train model
    model = LinearRegression()
    model.fit(X, y)

    # Forecast next 7 days
    future_days = np.arange(len(daily_costs), len(daily_costs) + 7).reshape(-1, 1)
    forecast = model.predict(future_days)

    # Create forecast dataframe
    last_date = daily_costs['DATE'].max()
    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=7)
    forecast_df = pd.DataFrame({
        'DATE': forecast_dates,
        'FORECAST_COST': forecast
    })

    # Combine historical and forecast
    fig_forecast = go.Figure()

    fig_forecast.add_trace(go.Scatter(
        x=daily_costs['DATE'],
        y=daily_costs['TOTAL_COST'],
        name='Historical',
        mode='lines+markers',
        line=dict(color='blue')
    ))

    fig_forecast.add_trace(go.Scatter(
        x=forecast_df['DATE'],
        y=forecast_df['FORECAST_COST'],
        name='Forecast',
        mode='lines+markers',
        line=dict(color='red', dash='dash')
    ))

    fig_forecast.update_layout(
        title='7-Day Cost Forecast',
        xaxis_title='Date',
        yaxis_title='Cost ($)',
        height=400
    )

    st.plotly_chart(fig_forecast, use_container_width=True)

    total_forecast = forecast.sum()
    st.info(f"📊 Projected cost for next 7 days: **${total_forecast:.2f}**")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    <small>Data from Snowflake ACCOUNT_USAGE views • Storage costs estimated at $40/TB/month • Updates may have 45min-3hr latency</small>
    </div>
    """,
    unsafe_allow_html=True
)
