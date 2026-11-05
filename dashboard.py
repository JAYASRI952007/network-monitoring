import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time
import config

st.set_page_config(
    page_title="Network Monitoring Dashboard",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1d29 0%, #23273a 100%);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #2d3348;
        text-align: center;
    }
    .status-up {
        background-color: #0d3320;
        color: #4ade80;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 13px;
    }
    .status-down {
        background-color: #3d0d0d;
        color: #f87171;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 13px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.6; }
        100% { opacity: 1; }
    }
    h1, h2, h3 {
        font-family: 'Segoe UI', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

def load_latest_status():
    """Gets the most recent status for each device."""
    conn = sqlite3.connect(config.DB_PATH)
    query = """
        SELECT device_name, ip, status, response_time_ms, packet_loss_percent, checked_at
        FROM status_log
        WHERE id IN (
            SELECT MAX(id) FROM status_log GROUP BY device_name
        )
        ORDER BY device_name
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def load_history(hours=1):
    """Gets full status history for charting, limited to recent hours."""
    conn = sqlite3.connect(config.DB_PATH)
    query = "SELECT * FROM status_log ORDER BY checked_at DESC LIMIT 500"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def load_incidents():
    """Gets all incidents, most recent first."""
    conn = sqlite3.connect(config.DB_PATH)
    query = "SELECT * FROM incidents ORDER BY id DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.title("🛰️ Network Monitoring Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

latest = load_latest_status()

total_devices = len(latest)
up_count = len(latest[latest["status"] == "UP"])
down_count = len(latest[latest["status"] == "DOWN"])
avg_response = latest["response_time_ms"].dropna().mean()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Devices", total_devices)
with col2:
    st.metric("Devices UP", up_count, delta=None)
with col3:
    st.metric("Devices DOWN", down_count, delta=None)
with col4:
    st.metric("Avg Response Time", f"{avg_response:.1f} ms" if avg_response else "N/A")

if down_count > 0:
    down_devices = latest[latest["status"] == "DOWN"]["device_name"].tolist()
    st.error(f"⚠️ ALERT: {down_count} device(s) DOWN — {', '.join(down_devices)}")
else:
    st.success("✅ All systems operational")

st.subheader("📋 Device Status")

def style_status(val):
    if val == "UP":
        return "background-color: #0d3320; color: #4ade80; font-weight: 600;"
    elif val == "DOWN":
        return "background-color: #3d0d0d; color: #f87171; font-weight: 600;"
    return ""

display_df = latest.rename(columns={
    "device_name": "Device",
    "ip": "IP Address",
    "status": "Status",
    "response_time_ms": "Response (ms)",
    "packet_loss_percent": "Packet Loss (%)",
    "checked_at": "Last Checked"
})

styled = display_df.style.map(style_status, subset=["Status"])
st.dataframe(styled, use_container_width=True, hide_index=True)

st.subheader("📈 Response Time Trend")

history = load_history()
if not history.empty:
    history["checked_at"] = pd.to_datetime(history["checked_at"])
    history = history.sort_values("checked_at")

    fig = go.Figure()
    for device_name in history["device_name"].unique():
        device_data = history[history["device_name"] == device_name]
        fig.add_trace(go.Scatter(
            x=device_data["checked_at"],
            y=device_data["response_time_ms"],
            mode="lines+markers",
            name=device_name,
            line=dict(width=2)
        ))

    fig.update_layout(
        template="plotly_dark",
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="Time",
        yaxis_title="Response Time (ms)"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No history data yet — run monitor.py to start collecting data.")

st.subheader("📊 Current Packet Loss by Device")

fig2 = px.bar(
    latest,
    x="device_name",
    y="packet_loss_percent",
    color="status",
    color_discrete_map={"UP": "#4ade80", "DOWN": "#f87171"},
    labels={"device_name": "Device", "packet_loss_percent": "Packet Loss (%)"}
)
fig2.update_layout(template="plotly_dark", height=350, margin=dict(l=20, r=20, t=30, b=20))
st.plotly_chart(fig2, use_container_width=True)

st.subheader("🕒 Incident History")

incidents = load_incidents()
if not incidents.empty:
    incidents_display = incidents.rename(columns={
        "device_name": "Device",
        "ip": "IP Address",
        "went_down_at": "Went Down",
        "recovered_at": "Recovered",
        "duration_seconds": "Duration (s)"
    })
    incidents_display["Recovered"] = incidents_display["Recovered"].fillna("Ongoing")
    incidents_display["Duration (s)"] = incidents_display["Duration (s)"].fillna("—")
    st.dataframe(incidents_display, use_container_width=True, hide_index=True)
else:
    st.info("No incidents recorded yet.")

st.divider()
refresh_rate = st.sidebar.slider("Auto-refresh interval (seconds)", 5, 60, 10)
st.sidebar.write(f"Dashboard refreshes every {refresh_rate}s")
time.sleep(refresh_rate)
st.rerun()