import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.queries import get_pipe_usage

st.set_page_config(
    page_title="Snowpipe Monitoring",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Snowpipe Usage Monitoring")
st.markdown("Monitor Snowpipe data ingestion performance and status")

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
with st.spinner("Loading Snowpipe usage data..."):
    pipe_data = get_pipe_usage(time_range)

if pipe_data.empty:
    st.warning("No Snowpipe data available for the selected time range")
    st.info("Snowpipe may not be configured or no data has been loaded in this time period")
    st.stop()

# Convert timestamp
pipe_data['PIPE_RECEIVED_TIME'] = pd.to_datetime(pipe_data['PIPE_RECEIVED_TIME'])

# Key Metrics
st.header("Overview")
col1, col2, col3, col4 = st.columns(4)

total_files = len(pipe_data)
total_rows = pipe_data['ROW_COUNT'].sum()
total_parsed = pipe_data['ROW_PARSED'].sum()
num_pipes = pipe_data['PIPE_NAME'].nunique()

with col1:
    st.metric("Total Files Loaded", f"{total_files:,}")

with col2:
    st.metric("Total Rows", f"{total_rows:,}")

with col3:
    st.metric("Rows Parsed", f"{total_parsed:,}")

with col4:
    st.metric("Active Pipes", num_pipes)

# Status analysis
st.header("Load Status")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Status Distribution")
    status_counts = pipe_data['STATUS'].value_counts()

    fig_status = px.pie(
        values=status_counts.values,
        names=status_counts.index,
        title='Load Status Distribution',
        color=status_counts.index,
        color_discrete_map={
            'LOADED': 'green',
            'LOAD_FAILED': 'red',
            'PARTIALLY_LOADED': 'orange'
        }
    )
    st.plotly_chart(fig_status, use_container_width=True)

with col2:
    st.subheader("Success Rate by Pipe")
    pipe_success = pipe_data.groupby('PIPE_NAME').apply(
        lambda x: (x['STATUS'] == 'LOADED').sum() / len(x) * 100
    ).sort_values(ascending=False).head(10)

    fig_success = px.bar(
        x=pipe_success.values,
        y=pipe_success.index,
        orientation='h',
        labels={'x': 'Success Rate (%)', 'y': 'Pipe Name'},
        color=pipe_success.values,
        color_continuous_scale='RdYlGn',
        range_color=[0, 100]
    )
    fig_success.update_layout(showlegend=False)
    st.plotly_chart(fig_success, use_container_width=True)

# Data ingestion trends
st.header("Data Ingestion Trends")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Files Loaded Over Time")
    files_timeline = pipe_data.set_index('PIPE_RECEIVED_TIME').resample('1H').size()

    fig_files = px.line(
        x=files_timeline.index,
        y=files_timeline.values,
        labels={'x': 'Time', 'y': 'Files Loaded'}
    )
    st.plotly_chart(fig_files, use_container_width=True)

with col2:
    st.subheader("Rows Loaded Over Time")
    rows_timeline = pipe_data.set_index('PIPE_RECEIVED_TIME').resample('1H')['ROW_COUNT'].sum()

    fig_rows = px.line(
        x=rows_timeline.index,
        y=rows_timeline.values,
        labels={'x': 'Time', 'y': 'Rows Loaded'},
        color_discrete_sequence=['green']
    )
    st.plotly_chart(fig_rows, use_container_width=True)

# Pipe performance
st.header("Pipe Performance")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Files Loaded by Pipe")
    pipe_files = pipe_data['PIPE_NAME'].value_counts().head(10)

    fig_pipe_files = px.bar(
        x=pipe_files.values,
        y=pipe_files.index,
        orientation='h',
        labels={'x': 'Files Loaded', 'y': 'Pipe Name'},
        color=pipe_files.values,
        color_continuous_scale='Blues'
    )
    fig_pipe_files.update_layout(showlegend=False)
    st.plotly_chart(fig_pipe_files, use_container_width=True)

with col2:
    st.subheader("Total Rows by Pipe")
    pipe_rows = pipe_data.groupby('PIPE_NAME')['ROW_COUNT'].sum().sort_values(ascending=False).head(10)

    fig_pipe_rows = px.bar(
        x=pipe_rows.values,
        y=pipe_rows.index,
        orientation='h',
        labels={'x': 'Total Rows', 'y': 'Pipe Name'},
        color=pipe_rows.values,
        color_continuous_scale='Greens'
    )
    fig_pipe_rows.update_layout(showlegend=False)
    st.plotly_chart(fig_pipe_rows, use_container_width=True)

# Parse efficiency
st.header("Parse Efficiency")
pipe_data['PARSE_RATE'] = (pipe_data['ROW_PARSED'] / pipe_data['ROW_COUNT'] * 100).fillna(0)

avg_parse_rate = pipe_data['PARSE_RATE'].mean()
st.metric("Average Parse Rate", f"{avg_parse_rate:.1f}%")

parse_efficiency = pipe_data.groupby('PIPE_NAME')['PARSE_RATE'].mean().sort_values(ascending=True).head(10)

fig_parse = px.bar(
    x=parse_efficiency.values,
    y=parse_efficiency.index,
    orientation='h',
    labels={'x': 'Parse Rate (%)', 'y': 'Pipe Name'},
    title='Parse Efficiency by Pipe (Lowest)',
    color=parse_efficiency.values,
    color_continuous_scale='RdYlGn',
    range_color=[0, 100]
)
fig_parse.update_layout(showlegend=False)
st.plotly_chart(fig_parse, use_container_width=True)

# Failed loads
failed_loads = pipe_data[pipe_data['STATUS'] == 'LOAD_FAILED']

if not failed_loads.empty:
    st.header("Failed Loads Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Failed Loads by Pipe")
        failed_by_pipe = failed_loads['PIPE_NAME'].value_counts().head(10)

        fig_failed = px.bar(
            x=failed_by_pipe.values,
            y=failed_by_pipe.index,
            orientation='h',
            labels={'x': 'Failed Loads', 'y': 'Pipe Name'},
            color=failed_by_pipe.values,
            color_continuous_scale='Reds'
        )
        fig_failed.update_layout(showlegend=False)
        st.plotly_chart(fig_failed, use_container_width=True)

    with col2:
        st.subheader("Failed Loads Timeline")
        failed_timeline = failed_loads.set_index('PIPE_RECEIVED_TIME').resample('1H').size()

        fig_failed_timeline = px.area(
            x=failed_timeline.index,
            y=failed_timeline.values,
            labels={'x': 'Time', 'y': 'Failed Loads'},
            color_discrete_sequence=['red']
        )
        st.plotly_chart(fig_failed_timeline, use_container_width=True)

    # Recent failures
    st.subheader("Recent Failed Loads")
    recent_failures = failed_loads[['PIPE_RECEIVED_TIME', 'PIPE_NAME', 'FILE_NAME', 'ERROR_MESSAGE']].sort_values('PIPE_RECEIVED_TIME', ascending=False).head(20)
    st.dataframe(recent_failures, use_container_width=True, hide_index=True)

# File-level details
st.header("Recent File Loads")

# Summary statistics
col1, col2, col3 = st.columns(3)

with col1:
    avg_rows_per_file = pipe_data['ROW_COUNT'].mean()
    st.metric("Avg Rows per File", f"{avg_rows_per_file:,.0f}")

with col2:
    max_rows = pipe_data['ROW_COUNT'].max()
    st.metric("Max Rows in File", f"{max_rows:,}")

with col3:
    min_rows = pipe_data[pipe_data['ROW_COUNT'] > 0]['ROW_COUNT'].min()
    st.metric("Min Rows in File", f"{min_rows:,}")

# Detailed file log
st.subheader("Detailed Load History")
st.dataframe(
    pipe_data.sort_values('PIPE_RECEIVED_TIME', ascending=False),
    use_container_width=True,
    hide_index=True
)
