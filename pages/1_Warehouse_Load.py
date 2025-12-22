import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.queries import get_warehouse_load

st.set_page_config(
    page_title="Warehouse Load Monitoring",
    page_icon="🏭",
    layout="wide"
)

st.title("🏭 Warehouse Load Monitoring")
st.markdown("Monitor warehouse utilization and query distribution over time")

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
with st.spinner("Loading warehouse load data..."):
    warehouse_data = get_warehouse_load(time_range)

if warehouse_data.empty:
    st.warning("No warehouse load data available for the selected time range")
    st.stop()

# Key Metrics
st.header("Overview")
col1, col2, col3, col4 = st.columns(4)

total_queries = warehouse_data['QUERY_COUNT'].sum()
avg_exec_time = warehouse_data['AVG_EXECUTION_TIME_SECONDS'].mean()
total_exec_time = warehouse_data['TOTAL_EXECUTION_TIME_SECONDS'].sum()
num_warehouses = warehouse_data['WAREHOUSE_NAME'].nunique()

with col1:
    st.metric("Total Queries", f"{total_queries:,}")

with col2:
    st.metric("Avg Execution Time", f"{avg_exec_time:.2f}s")

with col3:
    st.metric("Total Execution Time", f"{total_exec_time/3600:.1f}h")

with col4:
    st.metric("Active Warehouses", num_warehouses)

# Query count over time by warehouse
st.header("Query Count Over Time")
fig_queries = px.line(
    warehouse_data,
    x='HOUR',
    y='QUERY_COUNT',
    color='WAREHOUSE_NAME',
    title='Queries per Hour by Warehouse',
    labels={'QUERY_COUNT': 'Query Count', 'HOUR': 'Time', 'WAREHOUSE_NAME': 'Warehouse'}
)
fig_queries.update_layout(height=500)
st.plotly_chart(fig_queries, use_container_width=True)

# Execution time analysis
col1, col2 = st.columns(2)

with col1:
    st.subheader("Average Execution Time by Warehouse")
    avg_by_warehouse = warehouse_data.groupby('WAREHOUSE_NAME')['AVG_EXECUTION_TIME_SECONDS'].mean().sort_values(ascending=False)

    fig_avg = px.bar(
        x=avg_by_warehouse.values,
        y=avg_by_warehouse.index,
        orientation='h',
        labels={'x': 'Avg Execution Time (seconds)', 'y': 'Warehouse'},
        color=avg_by_warehouse.values,
        color_continuous_scale='Reds'
    )
    fig_avg.update_layout(showlegend=False)
    st.plotly_chart(fig_avg, use_container_width=True)

with col2:
    st.subheader("Total Execution Time by Warehouse")
    total_by_warehouse = warehouse_data.groupby('WAREHOUSE_NAME')['TOTAL_EXECUTION_TIME_SECONDS'].sum().sort_values(ascending=False)

    fig_total = px.bar(
        x=total_by_warehouse.values,
        y=total_by_warehouse.index,
        orientation='h',
        labels={'x': 'Total Execution Time (seconds)', 'y': 'Warehouse'},
        color=total_by_warehouse.values,
        color_continuous_scale='Blues'
    )
    fig_total.update_layout(showlegend=False)
    st.plotly_chart(fig_total, use_container_width=True)

# Query distribution
st.header("Query Distribution")
query_dist = warehouse_data.groupby('WAREHOUSE_NAME')['QUERY_COUNT'].sum().sort_values(ascending=False)

fig_dist = px.pie(
    values=query_dist.values,
    names=query_dist.index,
    title='Query Distribution by Warehouse'
)
st.plotly_chart(fig_dist, use_container_width=True)

# Heatmap of activity
st.header("Warehouse Activity Heatmap")
pivot_data = warehouse_data.pivot_table(
    values='QUERY_COUNT',
    index='WAREHOUSE_NAME',
    columns='HOUR',
    aggfunc='sum',
    fill_value=0
)

fig_heatmap = go.Figure(data=go.Heatmap(
    z=pivot_data.values,
    x=pivot_data.columns,
    y=pivot_data.index,
    colorscale='YlOrRd',
    hoverongaps=False
))

fig_heatmap.update_layout(
    title='Query Count Heatmap',
    xaxis_title='Hour',
    yaxis_title='Warehouse',
    height=400
)
st.plotly_chart(fig_heatmap, use_container_width=True)

# Detailed table
st.header("Detailed Warehouse Load Data")
st.dataframe(
    warehouse_data.sort_values('HOUR', ascending=False),
    use_container_width=True,
    hide_index=True
)
