import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from utils.queries import (
    get_row_count_trends,
    get_data_freshness,
    get_schema_evolution,
    get_pipe_validation_metrics
)

st.set_page_config(
    page_title="Data Quality Monitoring",
    page_icon="✅",
    layout="wide"
)

st.title("✅ Data Quality Monitoring")
st.markdown("Monitor data freshness, row count trends, schema changes, and pipeline validation")

# Sidebar controls
st.sidebar.header("Filters")
time_range = st.sidebar.selectbox(
    "Time Range",
    options=[7, 14, 30, 60, 90],
    index=2,
    format_func=lambda x: f"Last {x} days"
)

refresh = st.sidebar.button("🔄 Refresh Data")

# Fetch data
with st.spinner("Loading data quality metrics..."):
    row_trends = get_row_count_trends(min(time_range, 30))
    freshness_data = get_data_freshness()
    schema_changes = get_schema_evolution(min(time_range, 30))
    pipe_metrics = get_pipe_validation_metrics(24)

# =============================================================================
# SECTION 1: DATA FRESHNESS MONITORING
# =============================================================================
st.header("🕐 Data Freshness Monitoring")

if not freshness_data.empty:
    freshness_data['LAST_ALTERED'] = pd.to_datetime(freshness_data['LAST_ALTERED'])

    # Freshness metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_tables = len(freshness_data)
        st.metric("Total Tables", f"{total_tables:,}")

    with col2:
        recent_updates = len(freshness_data[freshness_data['HOURS_SINCE_UPDATE'] < 24])
        st.metric("Updated Last 24h", f"{recent_updates:,}")

    with col3:
        stale_tables = len(freshness_data[freshness_data['HOURS_SINCE_UPDATE'] > 168])  # 7 days
        st.metric("Stale Tables (>7d)", f"{stale_tables:,}")

    with col4:
        avg_age = freshness_data['HOURS_SINCE_UPDATE'].mean()
        st.metric("Avg Hours Since Update", f"{avg_age:.1f}")

    # Freshness distribution
    st.subheader("Data Freshness Distribution")

    freshness_bins = pd.cut(
        freshness_data['HOURS_SINCE_UPDATE'],
        bins=[0, 1, 6, 24, 72, 168, float('inf')],
        labels=['< 1 hour', '1-6 hours', '6-24 hours', '1-3 days', '3-7 days', '> 7 days']
    )

    freshness_dist = freshness_bins.value_counts().sort_index()

    col1, col2 = st.columns(2)

    with col1:
        fig_fresh_pie = px.pie(
            values=freshness_dist.values,
            names=freshness_dist.index,
            title='Table Freshness Distribution',
            color_discrete_sequence=px.colors.sequential.RdYlGn_r
        )
        st.plotly_chart(fig_fresh_pie, use_container_width=True)

    with col2:
        fig_fresh_bar = px.bar(
            x=freshness_dist.index,
            y=freshness_dist.values,
            title='Tables by Freshness Category',
            labels={'x': 'Freshness Category', 'y': 'Table Count'},
            color=freshness_dist.values,
            color_continuous_scale='RdYlGn_r'
        )
        st.plotly_chart(fig_fresh_bar, use_container_width=True)

    # Stale tables alert
    if stale_tables > 0:
        st.subheader("⚠️ Stale Tables (Not Updated in 7+ Days)")

        stale_data = freshness_data[freshness_data['HOURS_SINCE_UPDATE'] > 168].sort_values(
            'HOURS_SINCE_UPDATE',
            ascending=False
        ).head(50)

        stale_data['DAYS_SINCE_UPDATE'] = stale_data['HOURS_SINCE_UPDATE'] / 24

        st.warning(f"Found {stale_tables} tables that haven't been updated in over 7 days")

        st.dataframe(
            stale_data[['DATABASE_NAME', 'SCHEMA_NAME', 'TABLE_NAME', 'DAYS_SINCE_UPDATE', 'ROW_COUNT', 'LAST_ALTERED']].round(2),
            use_container_width=True,
            hide_index=True
        )

        st.info("**Recommendation:** Review these tables to determine if they're still needed or should be archived")
    else:
        st.success("✅ All tables updated within the last 7 days")

    # Most recently updated tables
    with st.expander("📋 Recently Updated Tables"):
        recent = freshness_data.sort_values('LAST_ALTERED', ascending=False).head(50)
        st.dataframe(
            recent[['DATABASE_NAME', 'SCHEMA_NAME', 'TABLE_NAME', 'HOURS_SINCE_UPDATE', 'ROW_COUNT', 'LAST_ALTERED']],
            use_container_width=True,
            hide_index=True
        )

else:
    st.warning("No data freshness information available")

# =============================================================================
# SECTION 2: ROW COUNT TRENDS & ANOMALY DETECTION
# =============================================================================
st.header("📊 Row Count Trends & Anomaly Detection")

if not row_trends.empty:
    row_trends['USAGE_DATE'] = pd.to_datetime(row_trends['USAGE_DATE'])

    # Select top tables for trend analysis
    top_tables = row_trends.groupby(['DATABASE_NAME', 'SCHEMA_NAME', 'TABLE_NAME'])['ROW_COUNT'].last().nlargest(20)

    st.subheader("Row Count Trends for Top Tables")

    # Table selector
    selected_table = st.selectbox(
        "Select table to analyze",
        options=[f"{db}.{schema}.{table}" for (db, schema, table) in top_tables.index]
    )

    if selected_table:
        db, schema, table = selected_table.split('.')

        table_data = row_trends[
            (row_trends['DATABASE_NAME'] == db) &
            (row_trends['SCHEMA_NAME'] == schema) &
            (row_trends['TABLE_NAME'] == table)
        ].sort_values('USAGE_DATE')

        if not table_data.empty:
            # Calculate statistics for anomaly detection
            mean_rows = table_data['ROW_COUNT'].mean()
            std_rows = table_data['ROW_COUNT'].std()

            # Detect anomalies (> 2 standard deviations)
            table_data['IS_ANOMALY'] = abs(table_data['ROW_COUNT'] - mean_rows) > (2 * std_rows)

            col1, col2, col3 = st.columns(3)

            with col1:
                current_rows = table_data['ROW_COUNT'].iloc[-1]
                st.metric("Current Row Count", f"{current_rows:,}")

            with col2:
                prev_rows = table_data['ROW_COUNT'].iloc[-2] if len(table_data) > 1 else current_rows
                delta = current_rows - prev_rows
                st.metric("Change from Previous", f"{delta:+,}")

            with col3:
                anomalies = table_data['IS_ANOMALY'].sum()
                st.metric("Anomalies Detected", anomalies)

            # Plot trend with anomalies
            fig_trend = go.Figure()

            # Normal points
            normal_data = table_data[~table_data['IS_ANOMALY']]
            fig_trend.add_trace(go.Scatter(
                x=normal_data['USAGE_DATE'],
                y=normal_data['ROW_COUNT'],
                mode='lines+markers',
                name='Row Count',
                line=dict(color='blue'),
                marker=dict(size=8)
            ))

            # Anomaly points
            anomaly_data = table_data[table_data['IS_ANOMALY']]
            if not anomaly_data.empty:
                fig_trend.add_trace(go.Scatter(
                    x=anomaly_data['USAGE_DATE'],
                    y=anomaly_data['ROW_COUNT'],
                    mode='markers',
                    name='Anomaly',
                    marker=dict(size=15, color='red', symbol='x')
                ))

            # Add mean and std deviation bands
            fig_trend.add_hline(
                y=mean_rows,
                line_dash="dash",
                line_color="green",
                annotation_text="Mean"
            )

            fig_trend.add_hrect(
                y0=mean_rows - (2 * std_rows),
                y1=mean_rows + (2 * std_rows),
                fillcolor="green",
                opacity=0.1,
                line_width=0,
                annotation_text="Normal Range"
            )

            fig_trend.update_layout(
                title=f'Row Count Trend: {selected_table}',
                xaxis_title='Date',
                yaxis_title='Row Count',
                height=500
            )

            st.plotly_chart(fig_trend, use_container_width=True)

            if anomalies > 0:
                st.warning(f"⚠️ {anomalies} anomalies detected in row count trend")
                st.dataframe(
                    anomaly_data[['USAGE_DATE', 'ROW_COUNT', 'SIZE_GB']],
                    use_container_width=True,
                    hide_index=True
                )

    # Growth/shrinkage analysis
    st.subheader("📈 Table Growth Analysis")

    growth_analysis = []

    for (db, schema, table) in top_tables.head(20).index:
        table_data = row_trends[
            (row_trends['DATABASE_NAME'] == db) &
            (row_trends['SCHEMA_NAME'] == schema) &
            (row_trends['TABLE_NAME'] == table)
        ].sort_values('USAGE_DATE')

        if len(table_data) >= 2:
            first_count = table_data['ROW_COUNT'].iloc[0]
            last_count = table_data['ROW_COUNT'].iloc[-1]
            change = last_count - first_count
            pct_change = (change / first_count * 100) if first_count > 0 else 0

            growth_analysis.append({
                'Table': f"{db}.{schema}.{table}",
                'Initial Rows': first_count,
                'Current Rows': last_count,
                'Change': change,
                'Change %': pct_change
            })

    if growth_analysis:
        growth_df = pd.DataFrame(growth_analysis).sort_values('Change', ascending=False)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Fastest Growing Tables**")
            growing = growth_df[growth_df['Change'] > 0].head(10)
            if not growing.empty:
                fig_growth = px.bar(
                    growing,
                    x='Change %',
                    y='Table',
                    orientation='h',
                    title='Top Growing Tables',
                    labels={'Change %': 'Growth %', 'Table': 'Table'},
                    color='Change %',
                    color_continuous_scale='Greens'
                )
                st.plotly_chart(fig_growth, use_container_width=True)
            else:
                st.info("No growing tables")

        with col2:
            st.markdown("**Shrinking Tables**")
            shrinking = growth_df[growth_df['Change'] < 0].head(10)
            if not shrinking.empty:
                fig_shrink = px.bar(
                    shrinking,
                    x='Change %',
                    y='Table',
                    orientation='h',
                    title='Top Shrinking Tables',
                    labels={'Change %': 'Shrinkage %', 'Table': 'Table'},
                    color='Change %',
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig_shrink, use_container_width=True)
            else:
                st.info("No shrinking tables")

        with st.expander("📋 View All Growth Analysis"):
            st.dataframe(growth_df.round(2), use_container_width=True, hide_index=True)

else:
    st.warning("No row count trend data available")

# =============================================================================
# SECTION 3: SCHEMA EVOLUTION TRACKING
# =============================================================================
st.header("🔧 Schema Evolution Tracking")

if not schema_changes.empty:
    schema_changes['LAST_ALTERED'] = pd.to_datetime(schema_changes['LAST_ALTERED'])

    col1, col2, col3 = st.columns(3)

    with col1:
        total_changes = len(schema_changes)
        st.metric("Total Column Changes", f"{total_changes:,}")

    with col2:
        tables_modified = schema_changes[['DATABASE_NAME', 'SCHEMA_NAME', 'TABLE_NAME']].drop_duplicates()
        st.metric("Tables Modified", len(tables_modified))

    with col3:
        deleted_columns = schema_changes[schema_changes['DELETED'].notna()]
        st.metric("Deleted Columns", len(deleted_columns))

    # Recent schema changes
    st.subheader("Recent Schema Changes")

    recent_changes = schema_changes.sort_values('LAST_ALTERED', ascending=False).head(50)

    st.dataframe(
        recent_changes[[
            'LAST_ALTERED', 'DATABASE_NAME', 'SCHEMA_NAME', 'TABLE_NAME',
            'COLUMN_NAME', 'DATA_TYPE', 'IS_NULLABLE', 'DELETED'
        ]],
        use_container_width=True,
        hide_index=True
    )

    # Tables with most changes
    st.subheader("Tables with Most Schema Changes")

    table_change_counts = schema_changes.groupby(['DATABASE_NAME', 'SCHEMA_NAME', 'TABLE_NAME']).size().sort_values(ascending=False).head(15)

    fig_changes = px.bar(
        x=table_change_counts.values,
        y=[f"{db}.{schema}.{table}" for (db, schema, table) in table_change_counts.index],
        orientation='h',
        title='Tables with Most Schema Changes',
        labels={'x': 'Change Count', 'y': 'Table'}
    )

    st.plotly_chart(fig_changes, use_container_width=True)

    # Deleted columns warning
    if len(deleted_columns) > 0:
        st.warning(f"⚠️ {len(deleted_columns)} columns have been deleted")

        with st.expander("View Deleted Columns"):
            st.dataframe(
                deleted_columns[['DATABASE_NAME', 'SCHEMA_NAME', 'TABLE_NAME', 'COLUMN_NAME', 'DELETED']],
                use_container_width=True,
                hide_index=True
            )

else:
    st.info("No schema changes detected in the selected time range")

# =============================================================================
# SECTION 4: PIPELINE VALIDATION (SNOWPIPE)
# =============================================================================
st.header("🚰 Data Pipeline Validation (Snowpipe)")

if not pipe_metrics.empty:
    pipe_metrics['HOUR'] = pd.to_datetime(pipe_metrics['HOUR'])

    # Pipeline metrics
    total_files = pipe_metrics['FILE_COUNT'].sum()
    loaded_files = pipe_metrics['LOADED_FILES'].sum()
    failed_files = pipe_metrics['FAILED_FILES'].sum()
    total_rows = pipe_metrics['TOTAL_ROWS'].sum()
    total_parsed = pipe_metrics['TOTAL_PARSED'].sum()

    load_success_rate = (loaded_files / total_files * 100) if total_files > 0 else 0
    parse_rate = (total_parsed / total_rows * 100) if total_rows > 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Files", f"{total_files:,}")

    with col2:
        st.metric("Load Success Rate", f"{load_success_rate:.1f}%")

    with col3:
        st.metric("Total Rows Loaded", f"{total_rows:,}")

    with col4:
        st.metric("Parse Success Rate", f"{parse_rate:.1f}%")

    # Ingestion by pipe
    st.subheader("Ingestion by Pipe")

    pipe_summary = pipe_metrics.groupby('PIPE_NAME').agg({
        'FILE_COUNT': 'sum',
        'TOTAL_ROWS': 'sum',
        'LOADED_FILES': 'sum',
        'FAILED_FILES': 'sum',
        'TOTAL_SIZE_MB': 'sum'
    }).reset_index()

    pipe_summary['SUCCESS_RATE'] = (pipe_summary['LOADED_FILES'] / pipe_summary['FILE_COUNT'] * 100)

    col1, col2 = st.columns(2)

    with col1:
        fig_pipe_rows = px.bar(
            pipe_summary.sort_values('TOTAL_ROWS', ascending=False).head(10),
            x='TOTAL_ROWS',
            y='PIPE_NAME',
            orientation='h',
            title='Top 10 Pipes by Rows Loaded',
            labels={'TOTAL_ROWS': 'Rows Loaded', 'PIPE_NAME': 'Pipe'},
            color='TOTAL_ROWS',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_pipe_rows, use_container_width=True)

    with col2:
        fig_pipe_success = px.bar(
            pipe_summary.sort_values('SUCCESS_RATE').head(10),
            x='SUCCESS_RATE',
            y='PIPE_NAME',
            orientation='h',
            title='Pipes with Lowest Success Rate',
            labels={'SUCCESS_RATE': 'Success Rate (%)', 'PIPE_NAME': 'Pipe'},
            color='SUCCESS_RATE',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig_pipe_success, use_container_width=True)

    # Failed loads
    if failed_files > 0:
        st.subheader("⚠️ Failed File Loads")

        pipes_with_failures = pipe_summary[pipe_summary['FAILED_FILES'] > 0].sort_values('FAILED_FILES', ascending=False)

        st.warning(f"Found {failed_files} failed file loads across {len(pipes_with_failures)} pipes")

        st.dataframe(
            pipes_with_failures[['PIPE_NAME', 'FILE_COUNT', 'LOADED_FILES', 'FAILED_FILES', 'SUCCESS_RATE']].round(2),
            use_container_width=True,
            hide_index=True
        )

    # Ingestion timeline
    st.subheader("Ingestion Timeline")

    timeline = pipe_metrics.groupby('HOUR').agg({
        'TOTAL_ROWS': 'sum',
        'FILE_COUNT': 'sum'
    }).reset_index()

    fig_timeline = go.Figure()

    fig_timeline.add_trace(go.Scatter(
        x=timeline['HOUR'],
        y=timeline['TOTAL_ROWS'],
        name='Rows Loaded',
        mode='lines+markers',
        yaxis='y',
        line=dict(color='blue')
    ))

    fig_timeline.add_trace(go.Scatter(
        x=timeline['HOUR'],
        y=timeline['FILE_COUNT'],
        name='Files Processed',
        mode='lines+markers',
        yaxis='y2',
        line=dict(color='orange')
    ))

    fig_timeline.update_layout(
        title='Snowpipe Ingestion Timeline',
        xaxis_title='Time',
        yaxis=dict(title='Rows Loaded', side='left'),
        yaxis2=dict(title='Files Processed', side='right', overlaying='y'),
        height=400
    )

    st.plotly_chart(fig_timeline, use_container_width=True)

else:
    st.info("No Snowpipe metrics available for the last 24 hours")

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
