import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.queries import (
    get_table_storage,
    get_clustering_depth,
    get_staged_files,
    get_database_storage
)

st.set_page_config(
    page_title="Storage Analytics",
    page_icon="💾",
    layout="wide"
)

st.title("💾 Storage Analytics & Optimization")
st.markdown("Analyze storage consumption, table-level breakdown, clustering efficiency, and optimization opportunities")

# Sidebar controls
st.sidebar.header("Filters")
refresh = st.sidebar.button("🔄 Refresh Data")

# Fetch data
with st.spinner("Loading storage analytics..."):
    table_storage = get_table_storage()
    clustering_data = get_clustering_depth()
    staged_files = get_staged_files()
    database_storage = get_database_storage()

# =============================================================================
# SECTION 1: DATABASE-LEVEL STORAGE
# =============================================================================
st.header("🗄️ Database Storage Overview")

if not database_storage.empty:
    # Total storage metrics
    total_active = database_storage['ACTIVE_GB'].sum()
    total_time_travel = database_storage['TIME_TRAVEL_GB'].sum()
    total_failsafe = database_storage['FAILSAFE_GB'].sum()
    total_storage = database_storage['TOTAL_GB'].sum()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Storage", f"{total_storage:,.2f} GB")

    with col2:
        st.metric("Active Data", f"{total_active:,.2f} GB")
        st.caption(f"{(total_active/total_storage*100):.1f}% of total")

    with col3:
        st.metric("Time Travel", f"{total_time_travel:,.2f} GB")
        st.caption(f"{(total_time_travel/total_storage*100):.1f}% of total")

    with col4:
        st.metric("Fail-safe", f"{total_failsafe:,.2f} GB")
        st.caption(f"{(total_failsafe/total_storage*100):.1f}% of total")

    # Storage distribution by database
    col1, col2 = st.columns(2)

    with col1:
        database_storage_sorted = database_storage.sort_values('TOTAL_GB', ascending=False)

        fig_db_storage = px.bar(
            database_storage_sorted,
            x='TOTAL_GB',
            y='DATABASE_NAME',
            orientation='h',
            title='Total Storage by Database',
            labels={'TOTAL_GB': 'Storage (GB)', 'DATABASE_NAME': 'Database'},
            color='TOTAL_GB',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_db_storage, use_container_width=True)

    with col2:
        fig_db_pie = px.pie(
            database_storage_sorted.head(10),
            values='TOTAL_GB',
            names='DATABASE_NAME',
            title='Top 10 Databases by Storage'
        )
        st.plotly_chart(fig_db_pie, use_container_width=True)

    # Storage composition breakdown
    st.subheader("Storage Composition by Database")

    fig_composition = go.Figure()

    fig_composition.add_trace(go.Bar(
        name='Active Data',
        x=database_storage_sorted['DATABASE_NAME'][:10],
        y=database_storage_sorted['ACTIVE_GB'][:10],
        marker_color='#1f77b4'
    ))

    fig_composition.add_trace(go.Bar(
        name='Time Travel',
        x=database_storage_sorted['DATABASE_NAME'][:10],
        y=database_storage_sorted['TIME_TRAVEL_GB'][:10],
        marker_color='#ff7f0e'
    ))

    fig_composition.add_trace(go.Bar(
        name='Fail-safe',
        x=database_storage_sorted['DATABASE_NAME'][:10],
        y=database_storage_sorted['FAILSAFE_GB'][:10],
        marker_color='#2ca02c'
    ))

    fig_composition.update_layout(
        title='Top 10 Databases: Storage Composition',
        xaxis_title='Database',
        yaxis_title='Storage (GB)',
        barmode='stack',
        height=500
    )

    st.plotly_chart(fig_composition, use_container_width=True)

    # Time-travel optimization opportunities
    st.subheader("💡 Time-Travel Storage Optimization")

    database_storage['TIME_TRAVEL_PCT'] = (database_storage['TIME_TRAVEL_GB'] / database_storage['TOTAL_GB'] * 100)
    high_time_travel = database_storage[database_storage['TIME_TRAVEL_PCT'] > 30].sort_values('TIME_TRAVEL_GB', ascending=False)

    if not high_time_travel.empty:
        st.warning(f"⚠️ Found {len(high_time_travel)} databases with >30% time-travel storage")
        st.dataframe(
            high_time_travel[['DATABASE_NAME', 'ACTIVE_GB', 'TIME_TRAVEL_GB', 'TIME_TRAVEL_PCT']].round(2),
            use_container_width=True,
            hide_index=True
        )
        st.markdown("**Recommendation:** Consider reducing time-travel retention period for these databases if not needed")
    else:
        st.success("✅ Time-travel storage is well optimized")

else:
    st.warning("No database storage data available")

# =============================================================================
# SECTION 2: TABLE-LEVEL STORAGE
# =============================================================================
st.header("📊 Table-Level Storage Analysis")

if not table_storage.empty:
    # Top tables by size
    st.subheader("Largest Tables")

    col1, col2 = st.columns([2, 1])

    with col1:
        top_tables = table_storage.head(20)

        fig_tables = px.bar(
            top_tables,
            x='SIZE_GB',
            y=top_tables['DATABASE_NAME'] + '.' + top_tables['SCHEMA_NAME'] + '.' + top_tables['TABLE_NAME'],
            orientation='h',
            title='Top 20 Tables by Total Size',
            labels={'SIZE_GB': 'Size (GB)', 'y': 'Table'},
            color='SIZE_GB',
            color_continuous_scale='Viridis'
        )
        fig_tables.update_layout(height=600)
        st.plotly_chart(fig_tables, use_container_width=True)

    with col2:
        st.metric("Total Tables", f"{len(table_storage):,}")
        st.metric("Largest Table", f"{table_storage.iloc[0]['SIZE_GB']:.2f} GB")
        st.metric("Avg Table Size", f"{table_storage['SIZE_GB'].mean():.2f} GB")

    # Table storage composition
    st.subheader("Table Storage Composition")

    top_tables_comp = table_storage.head(15).copy()
    top_tables_comp['TABLE_FULL_NAME'] = (
        top_tables_comp['DATABASE_NAME'] + '.' +
        top_tables_comp['SCHEMA_NAME'] + '.' +
        top_tables_comp['TABLE_NAME']
    )

    fig_table_comp = go.Figure()

    fig_table_comp.add_trace(go.Bar(
        name='Active',
        x=top_tables_comp['TABLE_FULL_NAME'],
        y=top_tables_comp['ACTIVE_GB'],
        marker_color='#1f77b4'
    ))

    fig_table_comp.add_trace(go.Bar(
        name='Time Travel',
        x=top_tables_comp['TABLE_FULL_NAME'],
        y=top_tables_comp['TIME_TRAVEL_GB'],
        marker_color='#ff7f0e'
    ))

    fig_table_comp.add_trace(go.Bar(
        name='Fail-safe',
        x=top_tables_comp['TABLE_FULL_NAME'],
        y=top_tables_comp['FAILSAFE_GB'],
        marker_color='#2ca02c'
    ))

    fig_table_comp.update_layout(
        title='Top 15 Tables: Storage Composition',
        xaxis_title='Table',
        yaxis_title='Storage (GB)',
        barmode='stack',
        height=500,
        xaxis={'tickangle': -45}
    )

    st.plotly_chart(fig_table_comp, use_container_width=True)

    # Schema-level aggregation
    st.subheader("Storage by Schema")

    schema_storage = table_storage.groupby(['DATABASE_NAME', 'SCHEMA_NAME']).agg({
        'SIZE_GB': 'sum',
        'ACTIVE_GB': 'sum',
        'TIME_TRAVEL_GB': 'sum',
        'FAILSAFE_GB': 'sum',
        'ROW_COUNT': 'sum'
    }).reset_index().sort_values('SIZE_GB', ascending=False).head(20)

    schema_storage['SCHEMA_FULL_NAME'] = schema_storage['DATABASE_NAME'] + '.' + schema_storage['SCHEMA_NAME']

    fig_schema = px.bar(
        schema_storage,
        x='SIZE_GB',
        y='SCHEMA_FULL_NAME',
        orientation='h',
        title='Top 20 Schemas by Storage',
        labels={'SIZE_GB': 'Size (GB)', 'SCHEMA_FULL_NAME': 'Schema'},
        color='SIZE_GB',
        color_continuous_scale='Oranges'
    )

    st.plotly_chart(fig_schema, use_container_width=True)

    # Tables with clustering keys
    st.subheader("🔑 Clustered Tables")

    clustered_tables = table_storage[table_storage['CLUSTERING_KEY'].notna()]

    if not clustered_tables.empty:
        st.info(f"Found {len(clustered_tables)} tables with clustering keys")

        clustered_summary = clustered_tables.head(20)[[
            'DATABASE_NAME', 'SCHEMA_NAME', 'TABLE_NAME', 'SIZE_GB', 'ROW_COUNT', 'CLUSTERING_KEY'
        ]]

        st.dataframe(clustered_summary, use_container_width=True, hide_index=True)
    else:
        st.info("No tables with clustering keys found")

    # Detailed table list
    with st.expander("📋 View All Tables"):
        st.dataframe(
            table_storage[[
                'DATABASE_NAME', 'SCHEMA_NAME', 'TABLE_NAME', 'TABLE_TYPE',
                'SIZE_GB', 'ACTIVE_GB', 'TIME_TRAVEL_GB', 'FAILSAFE_GB', 'ROW_COUNT'
            ]].round(2),
            use_container_width=True,
            hide_index=True
        )

else:
    st.warning("No table storage data available")

# =============================================================================
# SECTION 3: CLUSTERING DEPTH MONITORING
# =============================================================================
st.header("📐 Clustering Depth Analysis")

if not clustering_data.empty:
    st.subheader("Clustering Health")

    col1, col2, col3 = st.columns(3)

    with col1:
        avg_depth = clustering_data['AVG_DEPTH'].mean()
        st.metric("Avg Clustering Depth", f"{avg_depth:.2f}")
        if avg_depth > 5:
            st.caption("⚠️ High depth - consider reclustering")
        else:
            st.caption("✅ Good clustering health")

    with col2:
        tables_monitored = clustering_data['TABLE_NAME'].nunique()
        st.metric("Clustered Tables Monitored", tables_monitored)

    with col3:
        recently_reclustered = clustering_data[clustering_data['LAST_RECLUSTERED'].notna()]
        st.metric("Recently Reclustered", len(recently_reclustered))

    # Clustering depth distribution
    col1, col2 = st.columns(2)

    with col1:
        clustering_data['TABLE_FULL_NAME'] = (
            clustering_data['DATABASE_NAME'] + '.' +
            clustering_data['SCHEMA_NAME'] + '.' +
            clustering_data['TABLE_NAME']
        )

        top_depth = clustering_data.nlargest(15, 'AVG_DEPTH')

        fig_depth = px.bar(
            top_depth,
            x='AVG_DEPTH',
            y='TABLE_FULL_NAME',
            orientation='h',
            title='Tables with Highest Clustering Depth',
            labels={'AVG_DEPTH': 'Avg Depth', 'TABLE_FULL_NAME': 'Table'},
            color='AVG_DEPTH',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_depth, use_container_width=True)

    with col2:
        # Partition depth distribution
        depth_dist = clustering_data[[
            'PARTITION_DEPTH_1',
            'PARTITION_DEPTH_2_TO_4',
            'PARTITION_DEPTH_5_TO_16',
            'PARTITION_DEPTH_17_PLUS'
        ]].sum()

        fig_partition = px.pie(
            values=depth_dist.values,
            names=['Depth 1', 'Depth 2-4', 'Depth 5-16', 'Depth 17+'],
            title='Partition Depth Distribution'
        )
        st.plotly_chart(fig_partition, use_container_width=True)

    # Tables needing reclustering
    st.subheader("⚠️ Tables Needing Reclustering")

    needs_reclustering = clustering_data[clustering_data['AVG_DEPTH'] > 4].sort_values('AVG_DEPTH', ascending=False)

    if not needs_reclustering.empty:
        st.warning(f"Found {len(needs_reclustering)} tables with depth > 4")

        st.dataframe(
            needs_reclustering[[
                'DATABASE_NAME', 'SCHEMA_NAME', 'TABLE_NAME', 'AVG_DEPTH',
                'PARTITION_DEPTH_1', 'PARTITION_DEPTH_2_TO_4', 'PARTITION_DEPTH_5_TO_16', 'PARTITION_DEPTH_17_PLUS'
            ]].round(2),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("**Recommendation:** Consider manual reclustering for tables with depth > 4")
    else:
        st.success("✅ All clustered tables are well-maintained")

else:
    st.info("No clustering depth data available")

# =============================================================================
# SECTION 4: STAGED FILES
# =============================================================================
st.header("📦 Staged Files Monitoring")

if not staged_files.empty:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Stages", len(staged_files))

    with col2:
        internal_stages = len(staged_files[staged_files['STAGE_TYPE'] == 'INTERNAL'])
        st.metric("Internal Stages", internal_stages)

    with col3:
        external_stages = len(staged_files[staged_files['STAGE_TYPE'] == 'EXTERNAL'])
        st.metric("External Stages", external_stages)

    # Stage distribution
    col1, col2 = st.columns(2)

    with col1:
        stage_by_db = staged_files['DATABASE_NAME'].value_counts()

        fig_stage_db = px.bar(
            x=stage_by_db.values,
            y=stage_by_db.index,
            orientation='h',
            title='Stages by Database',
            labels={'x': 'Stage Count', 'y': 'Database'}
        )
        st.plotly_chart(fig_stage_db, use_container_width=True)

    with col2:
        stage_type_dist = staged_files['STAGE_TYPE'].value_counts()

        fig_stage_type = px.pie(
            values=stage_type_dist.values,
            names=stage_type_dist.index,
            title='Stage Type Distribution'
        )
        st.plotly_chart(fig_stage_type, use_container_width=True)

    # Recent stage activity
    st.subheader("Recent Stage Activity")

    staged_files['LAST_ALTERED'] = pd.to_datetime(staged_files['LAST_ALTERED'])
    recent_stages = staged_files.sort_values('LAST_ALTERED', ascending=False).head(20)

    st.dataframe(
        recent_stages[[
            'DATABASE_NAME', 'SCHEMA_NAME', 'STAGE_NAME', 'STAGE_TYPE', 'STAGE_REGION', 'LAST_ALTERED'
        ]],
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("No staged files data available")

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
