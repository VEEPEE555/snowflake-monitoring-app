import streamlit as st
import pandas as pd
import plotly.express as px
from utils.queries import get_access_history
import json

st.set_page_config(
    page_title="Data Access History",
    page_icon="🔐",
    layout="wide"
)

st.title("🔐 Data Access History")
st.markdown("Track data access patterns and object usage for governance and security")

# Sidebar controls
st.sidebar.header("Filters")
time_range = st.sidebar.selectbox(
    "Time Range",
    options=[1, 6, 12, 24, 48, 72],
    index=3,
    format_func=lambda x: f"Last {x} hours"
)

refresh = st.sidebar.button("🔄 Refresh Data")

# Fetch data
with st.spinner("Loading access history..."):
    access_data = get_access_history(time_range)

if access_data.empty:
    st.warning("No access history data available for the selected time range")
    st.stop()

# Key Metrics
st.header("Overview")
col1, col2, col3 = st.columns(3)

total_accesses = len(access_data)
unique_users = access_data['USER_NAME'].nunique()
queries_with_modifications = access_data['OBJECTS_MODIFIED'].notna().sum()

with col1:
    st.metric("Total Access Events", f"{total_accesses:,}")

with col2:
    st.metric("Unique Users", unique_users)

with col3:
    st.metric("Queries with Modifications", f"{queries_with_modifications:,}")

# User activity
st.header("User Activity")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Most Active Users")
    user_activity = access_data['USER_NAME'].value_counts().head(15)

    fig_users = px.bar(
        x=user_activity.values,
        y=user_activity.index,
        orientation='h',
        labels={'x': 'Access Count', 'y': 'User'},
        color=user_activity.values,
        color_continuous_scale='Viridis'
    )
    fig_users.update_layout(showlegend=False, height=500)
    st.plotly_chart(fig_users, use_container_width=True)

with col2:
    st.subheader("Access Timeline")
    access_data['QUERY_START_TIME'] = pd.to_datetime(access_data['QUERY_START_TIME'])
    access_timeline = access_data.set_index('QUERY_START_TIME').resample('1H').size()

    fig_timeline = px.line(
        x=access_timeline.index,
        y=access_timeline.values,
        labels={'x': 'Time', 'y': 'Access Events'}
    )
    fig_timeline.update_layout(height=500)
    st.plotly_chart(fig_timeline, use_container_width=True)

# Object access analysis
st.header("Object Access Analysis")

# Helper function to parse JSON arrays
def parse_json_array(json_str):
    if pd.isna(json_str):
        return []
    try:
        return json.loads(json_str) if isinstance(json_str, str) else json_str
    except:
        return []

# Extract object information
def extract_objects(row, column_name):
    objects = parse_json_array(row[column_name])
    result = []
    for obj in objects:
        if isinstance(obj, dict):
            # Extract objectName or objectDomain
            obj_name = obj.get('objectName', obj.get('objectDomain', 'Unknown'))
            result.append(obj_name)
    return result

# Create tabs for different object types
tab1, tab2, tab3 = st.tabs(["Direct Access", "Base Objects", "Modified Objects"])

with tab1:
    st.subheader("Directly Accessed Objects")
    direct_objects = []
    for _, row in access_data.iterrows():
        objects = extract_objects(row, 'DIRECT_OBJECTS_ACCESSED')
        direct_objects.extend(objects)

    if direct_objects:
        direct_df = pd.Series(direct_objects).value_counts().head(20)
        fig_direct = px.bar(
            x=direct_df.values,
            y=direct_df.index,
            orientation='h',
            labels={'x': 'Access Count', 'y': 'Object'},
            title='Top 20 Directly Accessed Objects'
        )
        fig_direct.update_layout(height=600)
        st.plotly_chart(fig_direct, use_container_width=True)
    else:
        st.info("No direct object access data available")

with tab2:
    st.subheader("Base Objects Accessed")
    base_objects = []
    for _, row in access_data.iterrows():
        objects = extract_objects(row, 'BASE_OBJECTS_ACCESSED')
        base_objects.extend(objects)

    if base_objects:
        base_df = pd.Series(base_objects).value_counts().head(20)
        fig_base = px.bar(
            x=base_df.values,
            y=base_df.index,
            orientation='h',
            labels={'x': 'Access Count', 'y': 'Object'},
            title='Top 20 Base Objects Accessed'
        )
        fig_base.update_layout(height=600)
        st.plotly_chart(fig_base, use_container_width=True)
    else:
        st.info("No base object access data available")

with tab3:
    st.subheader("Modified Objects")
    modified_data = access_data[access_data['OBJECTS_MODIFIED'].notna()]

    if not modified_data.empty:
        st.write(f"Found {len(modified_data)} queries that modified objects")

        modified_objects = []
        for _, row in modified_data.iterrows():
            objects = extract_objects(row, 'OBJECTS_MODIFIED')
            modified_objects.extend(objects)

        if modified_objects:
            modified_df = pd.Series(modified_objects).value_counts().head(20)
            fig_modified = px.bar(
                x=modified_df.values,
                y=modified_df.index,
                orientation='h',
                labels={'x': 'Modification Count', 'y': 'Object'},
                title='Top 20 Modified Objects',
                color=modified_df.values,
                color_continuous_scale='Reds'
            )
            fig_modified.update_layout(height=600)
            st.plotly_chart(fig_modified, use_container_width=True)

        # Show recent modifications
        st.subheader("Recent Modifications")
        st.dataframe(
            modified_data[['QUERY_START_TIME', 'USER_NAME', 'QUERY_ID', 'OBJECTS_MODIFIED']].head(20),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No object modifications in the selected time range")

# Detailed access log
st.header("Detailed Access Log")
st.dataframe(
    access_data.sort_values('QUERY_START_TIME', ascending=False),
    use_container_width=True,
    hide_index=True
)
