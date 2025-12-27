import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from utils.queries import (
    get_cost_by_warehouse,
    get_cost_by_user,
    get_cost_by_database,
    get_storage_costs_detailed,
    get_daily_credit_consumption,
    get_weekly_credit_consumption,
    get_monthly_credit_consumption,
    get_cost_anomalies,
    get_warehouse_cost_trends
)

st.set_page_config(
    page_title="Cost Tracking & Analytics",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Cost Tracking & Analytics")
st.markdown("Comprehensive cost monitoring, budgeting, and forecasting for Snowflake usage")

# Sidebar controls
st.sidebar.header("Configuration")

# Cost per credit configuration
credit_cost = st.sidebar.number_input(
    "Cost per Credit ($)",
    min_value=0.0,
    max_value=10.0,
    value=2.0,
    step=0.1,
    help="Enter your Snowflake credit cost (typically $2-$4 depending on edition)"
)

# Storage cost configuration
storage_cost_per_tb = st.sidebar.number_input(
    "Storage Cost per TB/Month ($)",
    min_value=0.0,
    max_value=100.0,
    value=23.0,
    step=1.0,
    help="Enter your storage cost per TB per month (typically $23-$40)"
)

# Time range selection
time_range = st.sidebar.selectbox(
    "Analysis Period",
    options=[7, 14, 30, 60, 90],
    index=2,
    format_func=lambda x: f"Last {x} days"
)

# Budget settings
st.sidebar.subheader("Budget Settings")
daily_budget = st.sidebar.number_input(
    "Daily Budget ($)",
    min_value=0.0,
    value=100.0,
    step=10.0
)

monthly_budget = st.sidebar.number_input(
    "Monthly Budget ($)",
    min_value=0.0,
    value=3000.0,
    step=100.0
)

# Anomaly detection threshold
anomaly_threshold = st.sidebar.slider(
    "Anomaly Detection Sensitivity",
    min_value=1.0,
    max_value=3.0,
    value=2.0,
    step=0.1,
    help="Standard deviations from mean (lower = more sensitive)"
)

refresh = st.sidebar.button("🔄 Refresh Data")

# Create tabs for different views
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Overview",
    "Daily/Weekly/Monthly Trends",
    "Cost by Dimension",
    "Storage Costs",
    "Budget Tracking",
    "Anomaly Detection"
])

with tab1:
    st.header("Cost Overview")

    # Fetch overview data
    with st.spinner("Loading cost overview..."):
        daily_consumption = get_daily_credit_consumption(time_range)
        storage_costs = get_storage_costs_detailed(time_range)

    if not daily_consumption.empty:
        # Calculate key metrics
        total_credits = daily_consumption['TOTAL_CREDITS'].sum()
        total_cost = total_credits * credit_cost
        avg_daily_credits = daily_consumption['TOTAL_CREDITS'].mean()
        avg_daily_cost = avg_daily_credits * credit_cost

        # Display key metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Credits",
                f"{total_credits:,.2f}",
                help=f"Total credits consumed in the last {time_range} days"
            )

        with col2:
            st.metric(
                "Total Cost",
                f"${total_cost:,.2f}",
                help=f"Total cost based on ${credit_cost} per credit"
            )

        with col3:
            st.metric(
                "Avg Daily Credits",
                f"{avg_daily_credits:,.2f}",
                help="Average daily credit consumption"
            )

        with col4:
            st.metric(
                "Avg Daily Cost",
                f"${avg_daily_cost:,.2f}",
                help="Average daily cost"
            )

        # Cost breakdown
        st.subheader("Cost Breakdown")
        col1, col2 = st.columns(2)

        with col1:
            total_compute = daily_consumption['COMPUTE_CREDITS'].sum()
            total_cloud = daily_consumption['CLOUD_SERVICES_CREDITS'].sum()

            fig_breakdown = px.pie(
                values=[total_compute, total_cloud],
                names=['Compute', 'Cloud Services'],
                title='Credit Distribution',
                hole=0.4
            )
            fig_breakdown.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Credits: %{value:,.2f}<br>Percentage: %{percent}<extra></extra>'
            )
            st.plotly_chart(fig_breakdown, use_container_width=True)

        with col2:
            compute_cost = total_compute * credit_cost
            cloud_cost = total_cloud * credit_cost

            cost_data = pd.DataFrame({
                'Category': ['Compute', 'Cloud Services'],
                'Cost': [compute_cost, cloud_cost]
            })

            fig_cost = px.bar(
                cost_data,
                x='Category',
                y='Cost',
                title='Cost by Category',
                color='Category',
                text='Cost'
            )
            fig_cost.update_traces(
                texttemplate='$%{text:,.2f}',
                textposition='outside'
            )
            fig_cost.update_layout(showlegend=False)
            st.plotly_chart(fig_cost, use_container_width=True)

        # Storage costs
        if not storage_costs.empty:
            latest_storage = storage_costs.iloc[0]
            storage_tb = latest_storage['TOTAL_STORAGE_GB'] / 1024
            monthly_storage_cost = storage_tb * storage_cost_per_tb

            st.subheader("Storage Costs")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Storage", f"{latest_storage['TOTAL_STORAGE_GB']:,.2f} GB")

            with col2:
                st.metric("Data Storage", f"{latest_storage['STORAGE_GB']:,.2f} GB")

            with col3:
                st.metric("Fail-Safe Storage", f"{latest_storage['FAILSAFE_GB']:,.2f} GB")

            with col4:
                st.metric("Est. Monthly Storage Cost", f"${monthly_storage_cost:,.2f}")
    else:
        st.info("No cost data available for the selected time range")

with tab2:
    st.header("Daily/Weekly/Monthly Trends")

    # Period selection
    view_type = st.radio(
        "Select View",
        options=["Daily", "Weekly", "Monthly"],
        horizontal=True
    )

    with st.spinner(f"Loading {view_type.lower()} trends..."):
        if view_type == "Daily":
            trend_data = get_daily_credit_consumption(min(time_range, 90))
            time_col = 'USAGE_DATE'
        elif view_type == "Weekly":
            trend_data = get_weekly_credit_consumption(min(time_range // 7, 52))
            time_col = 'WEEK_START'
        else:
            trend_data = get_monthly_credit_consumption(min(time_range // 30, 12))
            time_col = 'MONTH_START'

    if not trend_data.empty:
        # Add cost column
        trend_data['TOTAL_COST'] = trend_data['TOTAL_CREDITS'] * credit_cost
        trend_data['COMPUTE_COST'] = trend_data['COMPUTE_CREDITS'] * credit_cost
        trend_data['CLOUD_SERVICES_COST'] = trend_data['CLOUD_SERVICES_CREDITS'] * credit_cost

        # Credit consumption trend
        st.subheader(f"{view_type} Credit Consumption")
        fig_credits = px.area(
            trend_data,
            x=time_col,
            y=['COMPUTE_CREDITS', 'CLOUD_SERVICES_CREDITS'],
            title=f'{view_type} Credit Usage Trend',
            labels={'value': 'Credits', time_col: 'Date', 'variable': 'Type'}
        )
        fig_credits.update_layout(hovermode='x unified', height=400)
        st.plotly_chart(fig_credits, use_container_width=True)

        # Cost trend
        st.subheader(f"{view_type} Cost Trend")
        fig_cost_trend = go.Figure()

        fig_cost_trend.add_trace(go.Scatter(
            x=trend_data[time_col],
            y=trend_data['TOTAL_COST'],
            mode='lines+markers',
            name='Total Cost',
            line=dict(color='#1f77b4', width=3),
            fill='tozeroy'
        ))

        if view_type == "Daily" and daily_budget > 0:
            fig_cost_trend.add_hline(
                y=daily_budget,
                line_dash="dash",
                line_color="red",
                annotation_text="Daily Budget",
                annotation_position="right"
            )

        fig_cost_trend.update_layout(
            title=f'{view_type} Cost Trend',
            xaxis_title='Date',
            yaxis_title='Cost ($)',
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_cost_trend, use_container_width=True)

        # Statistics
        col1, col2, col3 = st.columns(3)

        with col1:
            avg_cost = trend_data['TOTAL_COST'].mean()
            st.metric(f"Avg {view_type} Cost", f"${avg_cost:,.2f}")

        with col2:
            max_cost = trend_data['TOTAL_COST'].max()
            max_date = trend_data.loc[trend_data['TOTAL_COST'].idxmax(), time_col]
            st.metric(f"Peak {view_type} Cost", f"${max_cost:,.2f}", f"on {max_date.strftime('%Y-%m-%d')}")

        with col3:
            min_cost = trend_data['TOTAL_COST'].min()
            st.metric(f"Lowest {view_type} Cost", f"${min_cost:,.2f}")

        # Detailed table
        st.subheader(f"Detailed {view_type} Data")
        display_data = trend_data[[
            time_col, 'TOTAL_CREDITS', 'COMPUTE_CREDITS', 'CLOUD_SERVICES_CREDITS',
            'TOTAL_COST', 'ACTIVE_WAREHOUSES'
        ]].copy()
        display_data = display_data.sort_values(time_col, ascending=False)
        st.dataframe(display_data, use_container_width=True, hide_index=True)
    else:
        st.info("No trend data available")

with tab3:
    st.header("Cost by Dimension")

    dimension = st.selectbox(
        "Select Dimension",
        options=["Warehouse", "User", "Database"],
        index=0
    )

    with st.spinner(f"Loading cost data by {dimension.lower()}..."):
        if dimension == "Warehouse":
            dimension_data = get_cost_by_warehouse(time_range)
            groupby_col = 'WAREHOUSE_NAME'
        elif dimension == "User":
            dimension_data = get_cost_by_user(time_range)
            groupby_col = 'USER_NAME'
        else:
            dimension_data = get_cost_by_database(time_range)
            groupby_col = 'DATABASE_NAME'

    if not dimension_data.empty:
        # Add cost column
        if 'TOTAL_CREDITS' in dimension_data.columns:
            dimension_data['COST'] = dimension_data['TOTAL_CREDITS'] * credit_cost
        elif 'ESTIMATED_CREDITS' in dimension_data.columns:
            dimension_data['COST'] = dimension_data['ESTIMATED_CREDITS'] * credit_cost
        else:
            st.warning("Cost data not available for this dimension")
            st.stop()

        # Aggregate by dimension
        agg_data = dimension_data.groupby(groupby_col)['COST'].sum().sort_values(ascending=False)

        # Top consumers
        st.subheader(f"Top Cost Consumers by {dimension}")
        col1, col2 = st.columns(2)

        with col1:
            top_10 = agg_data.head(10)
            fig_top = px.bar(
                x=top_10.values,
                y=top_10.index,
                orientation='h',
                title=f'Top 10 {dimension}s by Cost',
                labels={'x': 'Cost ($)', 'y': dimension},
                color=top_10.values,
                color_continuous_scale='Reds'
            )
            fig_top.update_traces(texttemplate='$%{x:,.2f}', textposition='outside')
            fig_top.update_layout(showlegend=False)
            st.plotly_chart(fig_top, use_container_width=True)

        with col2:
            # Pie chart for distribution
            top_5 = agg_data.head(5)
            others = agg_data.iloc[5:].sum()

            if others > 0:
                pie_data = pd.concat([top_5, pd.Series({'Others': others})])
            else:
                pie_data = top_5

            fig_pie = px.pie(
                values=pie_data.values,
                names=pie_data.index,
                title='Cost Distribution',
                hole=0.4
            )
            fig_pie.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Cost: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>'
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # Trend over time
        st.subheader(f"Cost Trend by {dimension}")

        if 'USAGE_DATE' in dimension_data.columns:
            # Prepare data for time series
            top_entities = agg_data.head(5).index.tolist()
            filtered_data = dimension_data[dimension_data[groupby_col].isin(top_entities)]

            pivot_data = filtered_data.pivot_table(
                values='COST',
                index='USAGE_DATE',
                columns=groupby_col,
                aggfunc='sum',
                fill_value=0
            )

            fig_trend = px.line(
                pivot_data,
                x=pivot_data.index,
                y=pivot_data.columns,
                title=f'Cost Trend for Top 5 {dimension}s',
                labels={'value': 'Cost ($)', 'USAGE_DATE': 'Date', 'variable': dimension}
            )
            fig_trend.update_layout(hovermode='x unified', height=400)
            st.plotly_chart(fig_trend, use_container_width=True)

        # Summary statistics
        st.subheader("Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_cost = agg_data.sum()
            st.metric("Total Cost", f"${total_cost:,.2f}")

        with col2:
            avg_cost = agg_data.mean()
            st.metric(f"Avg Cost per {dimension}", f"${avg_cost:,.2f}")

        with col3:
            top_cost = agg_data.max()
            st.metric("Highest Cost", f"${top_cost:,.2f}")

        with col4:
            num_entities = len(agg_data)
            st.metric(f"Active {dimension}s", num_entities)

        # Detailed table
        st.subheader(f"Detailed Cost Data by {dimension}")
        detailed_table = dimension_data.copy()
        if 'USAGE_DATE' in detailed_table.columns:
            detailed_table = detailed_table.sort_values(['USAGE_DATE', 'COST'], ascending=[False, False])
        st.dataframe(detailed_table, use_container_width=True, hide_index=True)
    else:
        st.info(f"No cost data available by {dimension.lower()}")

with tab4:
    st.header("Storage Costs")

    with st.spinner("Loading storage cost data..."):
        storage_data = get_storage_costs_detailed(time_range)

    if not storage_data.empty:
        # Calculate costs
        storage_data['STORAGE_COST'] = (storage_data['STORAGE_GB'] / 1024) * storage_cost_per_tb
        storage_data['STAGE_COST'] = (storage_data['STAGE_GB'] / 1024) * storage_cost_per_tb
        storage_data['FAILSAFE_COST'] = (storage_data['FAILSAFE_GB'] / 1024) * storage_cost_per_tb
        storage_data['TOTAL_COST'] = storage_data['STORAGE_COST'] + storage_data['STAGE_COST'] + storage_data['FAILSAFE_COST']

        # Current storage metrics
        latest = storage_data.iloc[0]

        st.subheader("Current Storage Costs")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Data Storage Cost",
                f"${latest['STORAGE_COST']:,.2f}/month",
                help=f"{latest['STORAGE_GB']:,.2f} GB at ${storage_cost_per_tb}/TB/month"
            )

        with col2:
            st.metric(
                "Stage Storage Cost",
                f"${latest['STAGE_COST']:,.2f}/month",
                help=f"{latest['STAGE_GB']:,.2f} GB at ${storage_cost_per_tb}/TB/month"
            )

        with col3:
            st.metric(
                "Fail-Safe Cost",
                f"${latest['FAILSAFE_COST']:,.2f}/month",
                help=f"{latest['FAILSAFE_GB']:,.2f} GB at ${storage_cost_per_tb}/TB/month"
            )

        with col4:
            st.metric(
                "Total Storage Cost",
                f"${latest['TOTAL_COST']:,.2f}/month"
            )

        # Storage cost trends
        st.subheader("Storage Cost Trends")

        fig_storage_cost = go.Figure()

        fig_storage_cost.add_trace(go.Scatter(
            x=storage_data['USAGE_DATE'],
            y=storage_data['STORAGE_COST'],
            name='Data Storage',
            stackgroup='one',
            fill='tonexty'
        ))

        fig_storage_cost.add_trace(go.Scatter(
            x=storage_data['USAGE_DATE'],
            y=storage_data['STAGE_COST'],
            name='Stage Storage',
            stackgroup='one',
            fill='tonexty'
        ))

        fig_storage_cost.add_trace(go.Scatter(
            x=storage_data['USAGE_DATE'],
            y=storage_data['FAILSAFE_COST'],
            name='Fail-Safe',
            stackgroup='one',
            fill='tonexty'
        ))

        fig_storage_cost.update_layout(
            title='Storage Cost Trend by Type',
            xaxis_title='Date',
            yaxis_title='Monthly Cost ($)',
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_storage_cost, use_container_width=True)

        # Storage breakdown
        col1, col2 = st.columns(2)

        with col1:
            # GB breakdown
            gb_breakdown = pd.DataFrame({
                'Type': ['Data', 'Stage', 'Fail-Safe'],
                'Storage_GB': [latest['STORAGE_GB'], latest['STAGE_GB'], latest['FAILSAFE_GB']]
            })

            fig_gb = px.pie(
                gb_breakdown,
                values='Storage_GB',
                names='Type',
                title='Storage Distribution (GB)',
                hole=0.4
            )
            st.plotly_chart(fig_gb, use_container_width=True)

        with col2:
            # Cost breakdown
            cost_breakdown = pd.DataFrame({
                'Type': ['Data', 'Stage', 'Fail-Safe'],
                'Cost': [latest['STORAGE_COST'], latest['STAGE_COST'], latest['FAILSAFE_COST']]
            })

            fig_cost_pie = px.pie(
                cost_breakdown,
                values='Cost',
                names='Type',
                title='Storage Cost Distribution',
                hole=0.4
            )
            st.plotly_chart(fig_cost_pie, use_container_width=True)

        # Detailed table
        st.subheader("Storage Cost History")
        display_cols = ['USAGE_DATE', 'STORAGE_GB', 'STAGE_GB', 'FAILSAFE_GB',
                       'STORAGE_COST', 'STAGE_COST', 'FAILSAFE_COST', 'TOTAL_COST']
        st.dataframe(
            storage_data[display_cols].sort_values('USAGE_DATE', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No storage cost data available")

with tab5:
    st.header("Budget Tracking & Forecasting")

    with st.spinner("Loading budget data..."):
        daily_data = get_daily_credit_consumption(time_range)
        monthly_data = get_monthly_credit_consumption(12)

    # Daily budget tracking
    if not daily_data.empty and daily_budget > 0:
        st.subheader("Daily Budget Tracking")

        daily_data['DAILY_COST'] = daily_data['TOTAL_CREDITS'] * credit_cost
        daily_data['OVER_BUDGET'] = daily_data['DAILY_COST'] > daily_budget
        daily_data['BUDGET_VARIANCE'] = daily_data['DAILY_COST'] - daily_budget

        # Budget compliance
        total_days = len(daily_data)
        days_over = daily_data['OVER_BUDGET'].sum()
        compliance_rate = ((total_days - days_over) / total_days * 100) if total_days > 0 else 0

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Budget Compliance", f"{compliance_rate:.1f}%")

        with col2:
            st.metric("Days Over Budget", f"{days_over} / {total_days}")

        with col3:
            avg_variance = daily_data['BUDGET_VARIANCE'].mean()
            st.metric("Avg Daily Variance", f"${avg_variance:,.2f}",
                     delta=f"${abs(avg_variance):,.2f} {'over' if avg_variance > 0 else 'under'}")

        # Daily cost vs budget chart
        fig_budget = go.Figure()

        fig_budget.add_trace(go.Bar(
            x=daily_data['USAGE_DATE'],
            y=daily_data['DAILY_COST'],
            name='Actual Cost',
            marker_color=['red' if over else 'green' for over in daily_data['OVER_BUDGET']]
        ))

        fig_budget.add_hline(
            y=daily_budget,
            line_dash="dash",
            line_color="blue",
            annotation_text="Daily Budget",
            annotation_position="right"
        )

        fig_budget.update_layout(
            title='Daily Cost vs Budget',
            xaxis_title='Date',
            yaxis_title='Cost ($)',
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_budget, use_container_width=True)

    # Monthly budget tracking
    if not monthly_data.empty and monthly_budget > 0:
        st.subheader("Monthly Budget Tracking")

        monthly_data['MONTHLY_COST'] = monthly_data['TOTAL_CREDITS'] * credit_cost
        monthly_data['OVER_BUDGET'] = monthly_data['MONTHLY_COST'] > monthly_budget
        monthly_data['BUDGET_VARIANCE'] = monthly_data['MONTHLY_COST'] - monthly_budget

        # Monthly cost vs budget chart
        fig_monthly_budget = go.Figure()

        fig_monthly_budget.add_trace(go.Bar(
            x=monthly_data['MONTH_START'],
            y=monthly_data['MONTHLY_COST'],
            name='Actual Cost',
            marker_color=['red' if over else 'green' for over in monthly_data['OVER_BUDGET']]
        ))

        fig_monthly_budget.add_hline(
            y=monthly_budget,
            line_dash="dash",
            line_color="blue",
            annotation_text="Monthly Budget",
            annotation_position="right"
        )

        fig_monthly_budget.update_layout(
            title='Monthly Cost vs Budget',
            xaxis_title='Month',
            yaxis_title='Cost ($)',
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_monthly_budget, use_container_width=True)

        # Variance analysis
        st.subheader("Budget Variance Analysis")
        variance_data = monthly_data[['MONTH_START', 'MONTHLY_COST', 'BUDGET_VARIANCE']].copy()
        variance_data = variance_data.sort_values('MONTH_START', ascending=False)
        st.dataframe(variance_data, use_container_width=True, hide_index=True)

    # Forecasting
    st.subheader("Cost Forecasting")

    if not daily_data.empty:
        # Simple linear regression for forecasting
        daily_data_sorted = daily_data.sort_values('USAGE_DATE')
        daily_data_sorted['DAY_NUM'] = range(len(daily_data_sorted))
        daily_data_sorted['DAILY_COST'] = daily_data_sorted['TOTAL_CREDITS'] * credit_cost

        # Calculate trend
        from numpy.polynomial import Polynomial
        if len(daily_data_sorted) >= 7:
            p = Polynomial.fit(daily_data_sorted['DAY_NUM'], daily_data_sorted['DAILY_COST'], 1)
            trend_slope = p.convert().coef[1]

            # Forecast next 30 days
            last_day = daily_data_sorted['DAY_NUM'].max()
            forecast_days = np.arange(last_day + 1, last_day + 31)
            forecast_costs = p(forecast_days)

            # Create forecast dates
            last_date = daily_data_sorted['USAGE_DATE'].max()
            forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=30)

            # Display forecast
            col1, col2 = st.columns(2)

            with col1:
                next_30_forecast = forecast_costs.sum()
                st.metric(
                    "30-Day Forecast",
                    f"${next_30_forecast:,.2f}",
                    delta=f"${trend_slope:.2f}/day trend"
                )

            with col2:
                monthly_forecast = next_30_forecast
                variance_to_budget = monthly_forecast - monthly_budget
                st.metric(
                    "Forecast vs Monthly Budget",
                    f"${variance_to_budget:,.2f}",
                    delta=f"{'Over' if variance_to_budget > 0 else 'Under'} budget"
                )

            # Forecast chart
            fig_forecast = go.Figure()

            fig_forecast.add_trace(go.Scatter(
                x=daily_data_sorted['USAGE_DATE'],
                y=daily_data_sorted['DAILY_COST'],
                name='Historical',
                mode='lines+markers'
            ))

            fig_forecast.add_trace(go.Scatter(
                x=forecast_dates,
                y=forecast_costs,
                name='Forecast',
                mode='lines',
                line=dict(dash='dash')
            ))

            if daily_budget > 0:
                fig_forecast.add_hline(
                    y=daily_budget,
                    line_dash="dot",
                    line_color="red",
                    annotation_text="Daily Budget"
                )

            fig_forecast.update_layout(
                title='Cost Forecast (30 Days)',
                xaxis_title='Date',
                yaxis_title='Cost ($)',
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig_forecast, use_container_width=True)
        else:
            st.info("Insufficient data for forecasting (need at least 7 days)")

with tab6:
    st.header("Cost Anomaly Detection")

    with st.spinner("Detecting cost anomalies..."):
        anomalies = get_cost_anomalies(time_range, anomaly_threshold)
        daily_data_full = get_daily_credit_consumption(time_range)

    if not anomalies.empty:
        st.subheader("Detected Anomalies")

        # Add cost column
        anomalies['COST'] = anomalies['TOTAL_CREDITS'] * credit_cost
        anomalies['EXPECTED_COST'] = anomalies['MEAN_CREDITS'] * credit_cost

        # Count anomalies
        high_anomalies = len(anomalies[anomalies['ANOMALY_TYPE'] == 'HIGH'])
        low_anomalies = len(anomalies[anomalies['ANOMALY_TYPE'] == 'LOW'])

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Anomalies", len(anomalies))

        with col2:
            st.metric("High Cost Anomalies", high_anomalies, delta="⚠️", delta_color="inverse")

        with col3:
            st.metric("Low Cost Anomalies", low_anomalies, delta="✓", delta_color="normal")

        # Anomaly visualization
        if not daily_data_full.empty:
            daily_data_full['COST'] = daily_data_full['TOTAL_CREDITS'] * credit_cost

            # Merge with anomalies
            plot_data = daily_data_full.merge(
                anomalies[['USAGE_DATE', 'ANOMALY_TYPE', 'MEAN_CREDITS']],
                left_on='USAGE_DATE',
                right_on='USAGE_DATE',
                how='left'
            )

            plot_data['IS_ANOMALY'] = plot_data['ANOMALY_TYPE'].notna()

            fig_anomaly = go.Figure()

            # Normal days
            normal_data = plot_data[~plot_data['IS_ANOMALY']]
            fig_anomaly.add_trace(go.Scatter(
                x=normal_data['USAGE_DATE'],
                y=normal_data['COST'],
                name='Normal',
                mode='lines+markers',
                marker=dict(size=6, color='blue')
            ))

            # Anomaly days
            anomaly_data = plot_data[plot_data['IS_ANOMALY']]
            if not anomaly_data.empty:
                fig_anomaly.add_trace(go.Scatter(
                    x=anomaly_data['USAGE_DATE'],
                    y=anomaly_data['COST'],
                    name='Anomaly',
                    mode='markers',
                    marker=dict(size=12, color='red', symbol='x')
                ))

            # Mean line
            if 'MEAN_CREDITS' in anomalies.columns:
                mean_cost = anomalies['MEAN_CREDITS'].iloc[0] * credit_cost
                fig_anomaly.add_hline(
                    y=mean_cost,
                    line_dash="dash",
                    line_color="green",
                    annotation_text="Mean Cost",
                    annotation_position="right"
                )

            fig_anomaly.update_layout(
                title='Cost Anomaly Detection',
                xaxis_title='Date',
                yaxis_title='Cost ($)',
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig_anomaly, use_container_width=True)

        # Anomaly details table
        st.subheader("Anomaly Details")
        anomaly_table = anomalies[[
            'USAGE_DATE', 'COST', 'EXPECTED_COST', 'Z_SCORE', 'ANOMALY_TYPE'
        ]].copy()
        anomaly_table['VARIANCE'] = anomaly_table['COST'] - anomaly_table['EXPECTED_COST']
        anomaly_table = anomaly_table.sort_values('USAGE_DATE', ascending=False)

        st.dataframe(
            anomaly_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "USAGE_DATE": "Date",
                "COST": st.column_config.NumberColumn("Actual Cost", format="$%.2f"),
                "EXPECTED_COST": st.column_config.NumberColumn("Expected Cost", format="$%.2f"),
                "VARIANCE": st.column_config.NumberColumn("Variance", format="$%.2f"),
                "Z_SCORE": st.column_config.NumberColumn("Z-Score", format="%.2f"),
                "ANOMALY_TYPE": "Type"
            }
        )

        # Recommendations
        st.subheader("Recommendations")
        if high_anomalies > 0:
            st.warning(f"🔍 Investigate {high_anomalies} high-cost anomalies. Check for:")
            st.markdown("""
            - Unexpected large queries or data loads
            - Warehouse size increases
            - New users or applications
            - Query performance issues causing longer runtimes
            """)
    else:
        st.success("No cost anomalies detected in the selected time range")

        # Still show the trend
        if not daily_data_full.empty:
            daily_data_full['COST'] = daily_data_full['TOTAL_CREDITS'] * credit_cost

            fig_normal = px.line(
                daily_data_full,
                x='USAGE_DATE',
                y='COST',
                title='Daily Cost Trend (No Anomalies Detected)',
                labels={'COST': 'Cost ($)', 'USAGE_DATE': 'Date'}
            )
            fig_normal.update_layout(height=400)
            st.plotly_chart(fig_normal, use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    <small>Cost calculations based on configured rates • Data from Snowflake ACCOUNT_USAGE views • Updates may have 45min-3hr latency</small>
    </div>
    """,
    unsafe_allow_html=True
)
