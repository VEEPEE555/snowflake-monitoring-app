import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.queries import (
    get_active_sessions,
    get_session_metrics,
    get_query_patterns_by_user,
    get_access_control_changes,
    get_network_policy_checks,
    get_login_history
)

st.set_page_config(
    page_title="Security & Sessions",
    page_icon="🔐",
    layout="wide"
)

st.title("🔐 Security & Session Monitoring")
st.markdown("Monitor user sessions, authentication patterns, access control changes, and security alerts")

# Sidebar controls
st.sidebar.header("Filters")
session_hours = st.sidebar.selectbox(
    "Session Time Range",
    options=[1, 6, 12, 24],
    index=3,
    format_func=lambda x: f"Last {x} hours"
)

security_days = st.sidebar.selectbox(
    "Security Events Range",
    options=[7, 14, 30],
    index=0,
    format_func=lambda x: f"Last {x} days"
)

refresh = st.sidebar.button("🔄 Refresh Data")

# Fetch data
with st.spinner("Loading security and session data..."):
    active_sessions = get_active_sessions(session_hours)
    session_metrics = get_session_metrics(security_days)
    query_patterns = get_query_patterns_by_user(security_days)
    access_changes = get_access_control_changes(security_days)
    network_blocks = get_network_policy_checks(session_hours)
    login_history = get_login_history(session_hours)

# =============================================================================
# SECTION 1: ACTIVE SESSIONS
# =============================================================================
st.header("👥 Active Sessions & Connections")

if not active_sessions.empty:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_sessions = len(active_sessions)
        st.metric("Active Sessions", f"{total_sessions:,}")

    with col2:
        unique_users = active_sessions['USER_NAME'].nunique()
        st.metric("Unique Users", f"{unique_users:,}")

    with col3:
        unique_ips = active_sessions['CLIENT_NET_ADDRESS'].nunique()
        st.metric("Unique IP Addresses", f"{unique_ips:,}")

    with col4:
        unique_apps = active_sessions['CLIENT_APPLICATION_ID'].nunique()
        st.metric("Client Applications", f"{unique_apps:,}")

    # Sessions over time
    st.subheader("Session Activity Timeline")

    active_sessions['CREATED_ON'] = pd.to_datetime(active_sessions['CREATED_ON'])
    sessions_over_time = active_sessions.set_index('CREATED_ON').resample('15min').size().reset_index()
    sessions_over_time.columns = ['TIME', 'SESSION_COUNT']

    fig_sessions = px.line(
        sessions_over_time,
        x='TIME',
        y='SESSION_COUNT',
        title='New Sessions Over Time',
        labels={'SESSION_COUNT': 'Sessions Created', 'TIME': 'Time'}
    )
    fig_sessions.update_layout(height=400)
    st.plotly_chart(fig_sessions, use_container_width=True)

    # Top users and applications
    col1, col2 = st.columns(2)

    with col1:
        user_sessions = active_sessions['USER_NAME'].value_counts().head(15)

        fig_users = px.bar(
            x=user_sessions.values,
            y=user_sessions.index,
            orientation='h',
            title='Top Users by Active Sessions',
            labels={'x': 'Session Count', 'y': 'User'}
        )
        st.plotly_chart(fig_users, use_container_width=True)

    with col2:
        app_sessions = active_sessions['CLIENT_APPLICATION_ID'].value_counts().head(10)

        fig_apps = px.pie(
            values=app_sessions.values,
            names=app_sessions.index,
            title='Sessions by Client Application'
        )
        st.plotly_chart(fig_apps, use_container_width=True)

    # Recent sessions detail
    with st.expander("📋 View Recent Sessions"):
        recent = active_sessions.sort_values('CREATED_ON', ascending=False).head(50)[[
            'CREATED_ON', 'USER_NAME', 'CLIENT_NET_ADDRESS', 'CLIENT_APPLICATION_ID',
            'CLIENT_ENVIRONMENT', 'AUTHENTICATION_METHOD'
        ]]
        st.dataframe(recent, use_container_width=True, hide_index=True)

else:
    st.info("No active session data available")

# =============================================================================
# SECTION 2: AUTHENTICATION METHODS
# =============================================================================
st.header("🔑 Authentication Methods & Patterns")

if not session_metrics.empty:
    # Authentication method distribution
    auth_dist = session_metrics.groupby('AUTHENTICATION_METHOD')['SESSION_COUNT'].sum().sort_values(ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_auth = px.pie(
            values=auth_dist.values,
            names=auth_dist.index,
            title='Authentication Methods Distribution'
        )
        st.plotly_chart(fig_auth, use_container_width=True)

    with col2:
        fig_auth_bar = px.bar(
            x=auth_dist.values,
            y=auth_dist.index,
            orientation='h',
            title='Sessions by Authentication Method',
            labels={'x': 'Session Count', 'y': 'Method'}
        )
        st.plotly_chart(fig_auth_bar, use_container_width=True)

    # User authentication patterns
    st.subheader("User Authentication Patterns")

    user_auth = session_metrics.sort_values('SESSION_COUNT', ascending=False).head(20)

    fig_user_auth = px.bar(
        user_auth,
        x='SESSION_COUNT',
        y='USER_NAME',
        color='AUTHENTICATION_METHOD',
        orientation='h',
        title='Top 20 Users by Session Count',
        labels={'SESSION_COUNT': 'Sessions', 'USER_NAME': 'User'}
    )
    fig_user_auth.update_layout(height=600)
    st.plotly_chart(fig_user_auth, use_container_width=True)

else:
    st.info("No session metrics available")

# =============================================================================
# SECTION 3: LOGIN ACTIVITY & FAILED LOGINS
# =============================================================================
st.header("🚪 Login Activity & Security Events")

if not login_history.empty:
    login_history['EVENT_TIMESTAMP'] = pd.to_datetime(login_history['EVENT_TIMESTAMP'])

    total_logins = len(login_history)
    failed_logins = len(login_history[login_history['IS_SUCCESS'] == 'NO'])
    success_rate = ((total_logins - failed_logins) / total_logins * 100) if total_logins > 0 else 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Login Attempts", f"{total_logins:,}")

    with col2:
        st.metric("Failed Logins", f"{failed_logins:,}")

    with col3:
        st.metric("Success Rate", f"{success_rate:.1f}%")

    # Failed login analysis
    if failed_logins > 0:
        st.subheader("❌ Failed Login Analysis")

        failed_df = login_history[login_history['IS_SUCCESS'] == 'NO']

        col1, col2 = st.columns(2)

        with col1:
            # Failed logins by user
            failed_users = failed_df['USER_NAME'].value_counts().head(15)

            fig_failed_users = px.bar(
                x=failed_users.values,
                y=failed_users.index,
                orientation='h',
                title='Top Users with Failed Logins',
                labels={'x': 'Failed Attempts', 'y': 'User'},
                color=failed_users.values,
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_failed_users, use_container_width=True)

        with col2:
            # Failed logins by IP
            failed_ips = failed_df['CLIENT_IP'].value_counts().head(15)

            fig_failed_ips = px.bar(
                x=failed_ips.values,
                y=failed_ips.index,
                orientation='h',
                title='Top IPs with Failed Logins',
                labels={'x': 'Failed Attempts', 'y': 'IP Address'},
                color=failed_ips.values,
                color_continuous_scale='Oranges'
            )
            st.plotly_chart(fig_failed_ips, use_container_width=True)

        # Failed login timeline
        st.subheader("Failed Login Timeline")

        failed_timeline = failed_df.set_index('EVENT_TIMESTAMP').resample('30min').size().reset_index()
        failed_timeline.columns = ['TIME', 'FAILED_COUNT']

        fig_timeline = px.area(
            failed_timeline,
            x='TIME',
            y='FAILED_COUNT',
            title='Failed Logins Over Time',
            labels={'FAILED_COUNT': 'Failed Attempts', 'TIME': 'Time'},
            color_discrete_sequence=['red']
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

        # Suspicious activity (multiple failures from same IP)
        st.subheader("🚨 Potential Security Threats")

        ip_failures = failed_df.groupby('CLIENT_IP').agg({
            'USER_NAME': 'count',
            'EVENT_TIMESTAMP': ['min', 'max'],
            'ERROR_MESSAGE': 'first'
        }).reset_index()

        ip_failures.columns = ['CLIENT_IP', 'FAILURE_COUNT', 'FIRST_ATTEMPT', 'LAST_ATTEMPT', 'ERROR_MESSAGE']
        ip_failures = ip_failures[ip_failures['FAILURE_COUNT'] >= 5].sort_values('FAILURE_COUNT', ascending=False)

        if not ip_failures.empty:
            st.error(f"⚠️ Found {len(ip_failures)} IP addresses with 5+ failed login attempts")
            st.dataframe(ip_failures, use_container_width=True, hide_index=True)
            st.markdown("**Recommendation:** Consider blocking these IP addresses or investigating the activity")
        else:
            st.success("✅ No suspicious login patterns detected")

        # Recent failed logins
        with st.expander("📋 View Recent Failed Logins"):
            recent_failed = failed_df.sort_values('EVENT_TIMESTAMP', ascending=False).head(50)[[
                'EVENT_TIMESTAMP', 'USER_NAME', 'CLIENT_IP', 'REPORTED_CLIENT_TYPE', 'ERROR_MESSAGE'
            ]]
            st.dataframe(recent_failed, use_container_width=True, hide_index=True)

    else:
        st.success("✅ No failed logins in the selected time range")

# =============================================================================
# SECTION 4: QUERY PATTERNS BY USER & ROLE
# =============================================================================
st.header("📊 Query Patterns by User & Role")

if not query_patterns.empty:
    # Top users by query count
    user_totals = query_patterns.groupby('USER_NAME').agg({
        'QUERY_COUNT': 'sum',
        'GB_SCANNED': 'sum',
        'TOTAL_ROWS_PRODUCED': 'sum'
    }).sort_values('QUERY_COUNT', ascending=False).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        top_users = user_totals.head(15)

        fig_user_queries = px.bar(
            top_users,
            x='QUERY_COUNT',
            y='USER_NAME',
            orientation='h',
            title='Top 15 Users by Query Count',
            labels={'QUERY_COUNT': 'Queries', 'USER_NAME': 'User'},
            color='QUERY_COUNT',
            color_continuous_scale='Greens'
        )
        st.plotly_chart(fig_user_queries, use_container_width=True)

    with col2:
        fig_user_data = px.bar(
            top_users.head(15),
            x='GB_SCANNED',
            y='USER_NAME',
            orientation='h',
            title='Top 15 Users by Data Scanned',
            labels={'GB_SCANNED': 'GB Scanned', 'USER_NAME': 'User'},
            color='GB_SCANNED',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_user_data, use_container_width=True)

    # Query types by user
    st.subheader("Query Type Distribution by User")

    top_10_users = user_totals.head(10)['USER_NAME'].tolist()
    user_query_types = query_patterns[query_patterns['USER_NAME'].isin(top_10_users)]

    fig_query_types = px.bar(
        user_query_types,
        x='QUERY_COUNT',
        y='USER_NAME',
        color='QUERY_TYPE',
        orientation='h',
        title='Query Types by Top 10 Users',
        labels={'QUERY_COUNT': 'Query Count', 'USER_NAME': 'User'}
    )
    fig_query_types.update_layout(height=500)
    st.plotly_chart(fig_query_types, use_container_width=True)

    # Role-based analysis
    st.subheader("Activity by Role")

    role_activity = query_patterns.groupby('ROLE_NAME')['QUERY_COUNT'].sum().sort_values(ascending=False).head(15)

    fig_roles = px.bar(
        x=role_activity.values,
        y=role_activity.index,
        orientation='h',
        title='Top 15 Roles by Query Activity',
        labels={'x': 'Query Count', 'y': 'Role'}
    )
    st.plotly_chart(fig_roles, use_container_width=True)

else:
    st.info("No query pattern data available")

# =============================================================================
# SECTION 5: ACCESS CONTROL CHANGES & PRIVILEGE ESCALATION
# =============================================================================
st.header("🔐 Access Control Changes")

if not access_changes.empty:
    st.subheader("Recent Grant Activity")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Total Grants", len(access_changes))

    with col2:
        unique_roles = access_changes['ROLE_NAME'].nunique()
        st.metric("Roles Modified", unique_roles)

    # Grants by object type
    col1, col2 = st.columns(2)

    with col1:
        object_types = access_changes['OBJECT_TYPE'].value_counts()

        fig_objects = px.pie(
            values=object_types.values,
            names=object_types.index,
            title='Grants by Object Type'
        )
        st.plotly_chart(fig_objects, use_container_width=True)

    with col2:
        privilege_types = access_changes['PRIVILEGE'].value_counts().head(10)

        fig_privileges = px.bar(
            x=privilege_types.values,
            y=privilege_types.index,
            orientation='h',
            title='Top 10 Privilege Types Granted',
            labels={'x': 'Count', 'y': 'Privilege'}
        )
        st.plotly_chart(fig_privileges, use_container_width=True)

    # Recent changes
    with st.expander("📋 View Recent Access Control Changes"):
        recent_changes = access_changes.head(100)[[
            'TIMESTAMP', 'ROLE_NAME', 'PRIVILEGE', 'OBJECT_TYPE', 'OBJECT_NAME', 'GRANTED_BY'
        ]]
        st.dataframe(recent_changes, use_container_width=True, hide_index=True)

    # Potential privilege escalation
    st.subheader("⚠️ Potential Privilege Escalation Events")

    high_risk_privileges = access_changes[
        access_changes['PRIVILEGE'].isin(['OWNERSHIP', 'CREATE ROLE', 'MANAGE GRANTS', 'CREATE USER'])
    ]

    if not high_risk_privileges.empty:
        st.warning(f"Found {len(high_risk_privileges)} high-risk privilege grants")
        st.dataframe(
            high_risk_privileges[['TIMESTAMP', 'ROLE_NAME', 'PRIVILEGE', 'OBJECT_NAME', 'GRANTED_BY']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ No high-risk privilege escalations detected")

else:
    st.info("No access control change data available")

# =============================================================================
# SECTION 6: NETWORK POLICY EFFECTIVENESS
# =============================================================================
st.header("🌐 Network Policy Effectiveness")

if not network_blocks.empty:
    st.subheader("Blocked Login Attempts")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Network Policy Blocks", len(network_blocks))

    with col2:
        blocked_ips = network_blocks['CLIENT_IP'].nunique()
        st.metric("Unique Blocked IPs", blocked_ips)

    # Blocked IPs
    blocked_ip_counts = network_blocks['CLIENT_IP'].value_counts()

    fig_blocked = px.bar(
        x=blocked_ip_counts.values,
        y=blocked_ip_counts.index,
        orientation='h',
        title='Network Policy Blocks by IP',
        labels={'x': 'Block Count', 'y': 'IP Address'},
        color=blocked_ip_counts.values,
        color_continuous_scale='Reds'
    )
    st.plotly_chart(fig_blocked, use_container_width=True)

    # Blocked attempts detail
    with st.expander("📋 View Network Policy Blocks"):
        st.dataframe(
            network_blocks[['EVENT_TIMESTAMP', 'USER_NAME', 'CLIENT_IP', 'REPORTED_CLIENT_TYPE', 'ERROR_MESSAGE']],
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("✅ No network policy blocks detected - all login attempts from allowed IPs")

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
