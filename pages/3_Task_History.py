import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.queries import get_task_history

st.set_page_config(
    page_title="Task Execution Monitoring",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Task Execution Monitoring")
st.markdown("Monitor Snowflake task execution status and performance")

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
with st.spinner("Loading task history..."):
    task_data = get_task_history(time_range)

if task_data.empty:
    st.warning("No task execution data available for the selected time range")
    st.info("Tasks may not be scheduled or executed in the selected time range")
    st.stop()

# Calculate execution duration
task_data['SCHEDULED_TIME'] = pd.to_datetime(task_data['SCHEDULED_TIME'])
task_data['COMPLETED_TIME'] = pd.to_datetime(task_data['COMPLETED_TIME'])
task_data['DURATION_SECONDS'] = (task_data['COMPLETED_TIME'] - task_data['SCHEDULED_TIME']).dt.total_seconds()

# Key Metrics
st.header("Overview")
col1, col2, col3, col4 = st.columns(4)

total_executions = len(task_data)
successful = len(task_data[task_data['STATE'] == 'SUCCEEDED'])
failed = len(task_data[task_data['STATE'] == 'FAILED'])
success_rate = (successful / total_executions * 100) if total_executions > 0 else 0

with col1:
    st.metric("Total Executions", f"{total_executions:,}")

with col2:
    st.metric("Success Rate", f"{success_rate:.1f}%")

with col3:
    st.metric("Successful", f"{successful:,}")

with col4:
    st.metric("Failed", f"{failed:,}", delta=f"-{failed}" if failed > 0 else "0", delta_color="inverse")

# Task execution status
st.header("Task Execution Status")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Execution State Distribution")
    state_counts = task_data['STATE'].value_counts()

    fig_status = px.pie(
        values=state_counts.values,
        names=state_counts.index,
        title='Task Execution States',
        color=state_counts.index,
        color_discrete_map={
            'SUCCEEDED': 'green',
            'FAILED': 'red',
            'SKIPPED': 'orange',
            'CANCELLED': 'gray'
        }
    )
    st.plotly_chart(fig_status, use_container_width=True)

with col2:
    st.subheader("Executions Over Time")
    executions_timeline = task_data.set_index('SCHEDULED_TIME').resample('1H').size()

    fig_timeline = px.line(
        x=executions_timeline.index,
        y=executions_timeline.values,
        labels={'x': 'Time', 'y': 'Executions'}
    )
    st.plotly_chart(fig_timeline, use_container_width=True)

# Task performance
st.header("Task Performance")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Most Executed Tasks")
    task_counts = task_data['TASK_NAME'].value_counts().head(10)

    fig_tasks = px.bar(
        x=task_counts.values,
        y=task_counts.index,
        orientation='h',
        labels={'x': 'Execution Count', 'y': 'Task Name'},
        color=task_counts.values,
        color_continuous_scale='Blues'
    )
    fig_tasks.update_layout(showlegend=False)
    st.plotly_chart(fig_tasks, use_container_width=True)

with col2:
    st.subheader("Average Duration by Task")
    avg_duration = task_data.groupby('TASK_NAME')['DURATION_SECONDS'].mean().sort_values(ascending=False).head(10)

    fig_duration = px.bar(
        x=avg_duration.values,
        y=avg_duration.index,
        orientation='h',
        labels={'x': 'Avg Duration (seconds)', 'y': 'Task Name'},
        color=avg_duration.values,
        color_continuous_scale='Oranges'
    )
    fig_duration.update_layout(showlegend=False)
    st.plotly_chart(fig_duration, use_container_width=True)

# Failed tasks analysis
if failed > 0:
    st.header("Failed Tasks Analysis")

    failed_tasks = task_data[task_data['STATE'] == 'FAILED']

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Tasks with Most Failures")
        failed_counts = failed_tasks['TASK_NAME'].value_counts().head(10)

        fig_failed = px.bar(
            x=failed_counts.values,
            y=failed_counts.index,
            orientation='h',
            labels={'x': 'Failure Count', 'y': 'Task Name'},
            color=failed_counts.values,
            color_continuous_scale='Reds'
        )
        fig_failed.update_layout(showlegend=False)
        st.plotly_chart(fig_failed, use_container_width=True)

    with col2:
        st.subheader("Failure Timeline")
        failed_timeline = failed_tasks.set_index('SCHEDULED_TIME').resample('1H').size()

        fig_failed_timeline = px.area(
            x=failed_timeline.index,
            y=failed_timeline.values,
            labels={'x': 'Time', 'y': 'Failed Tasks'},
            color_discrete_sequence=['red']
        )
        st.plotly_chart(fig_failed_timeline, use_container_width=True)

    # Recent failures table
    st.subheader("Recent Task Failures")
    recent_failures = failed_tasks[['SCHEDULED_TIME', 'TASK_NAME', 'DATABASE_NAME', 'SCHEMA_NAME', 'ERROR_CODE', 'ERROR_MESSAGE']].sort_values('SCHEDULED_TIME', ascending=False).head(20)
    st.dataframe(recent_failures, use_container_width=True, hide_index=True)

# Database/Schema distribution
st.header("Task Distribution by Database and Schema")

col1, col2 = st.columns(2)

with col1:
    st.subheader("By Database")
    db_counts = task_data['DATABASE_NAME'].value_counts()

    fig_db = px.pie(
        values=db_counts.values,
        names=db_counts.index,
        title='Executions by Database'
    )
    st.plotly_chart(fig_db, use_container_width=True)

with col2:
    st.subheader("By Schema")
    schema_counts = task_data['SCHEMA_NAME'].value_counts().head(10)

    fig_schema = px.bar(
        x=schema_counts.values,
        y=schema_counts.index,
        orientation='h',
        labels={'x': 'Execution Count', 'y': 'Schema'}
    )
    st.plotly_chart(fig_schema, use_container_width=True)

# Detailed task log
st.header("Detailed Task Execution Log")
st.dataframe(
    task_data.sort_values('SCHEDULED_TIME', ascending=False),
    use_container_width=True,
    hide_index=True
)
