# 🛰️ Network Monitoring Dashboard

A real-time network uptime monitoring tool built in Python that tracks 10+ IP
devices for response time, packet loss, and UP/DOWN status. Automated incident
logging into SQLite with a live Streamlit alert dashboard — replicating NOC
(Network Operations Center) monitoring workflows similar to Nagios/Zabbix.

## 👤 Author

**JAYASRI952007**
- GitHub: [@JAYASRI952007](https://github.com/JAYASRI952007)

## 🔧 Tech Stack
- **Python** — core application logic
- **Ping3** — ICMP ping-based connectivity checks
- **SQLite** — persistent storage for status history and incident logs
- **Streamlit** — live, auto-refreshing web dashboard
- **Plotly** — interactive response time and packet loss charts
- **Linux basics** — designed for systemd-based deployment on Linux servers

## 📸 Features
- Continuous monitoring of 10+ network devices at configurable intervals
- UP/DOWN status detection with consecutive-failure threshold (avoids false alarms)
- Packet loss percentage calculation per monitoring cycle
- Automated incident logging — records when a device goes down and recovers,
  including downtime duration
- Live dashboard with:
  - Color-coded device status table
  - Real-time alert banners
  - Response time trend charts (per device)
  - Packet loss comparison chart
  - Full incident history log

## 🏗️ Architecture

| File | Purpose |
|---|---|
| `config.py` | Device list and monitoring settings (interval, timeout, thresholds) |
| `ping_engine.py` | Core ping logic — checks host status, response time, packet loss |
| `db_manager.py` | SQLite schema setup, status logging, incident open/close logic |
| `monitor.py` | Continuous monitoring loop — detects UP/DOWN transitions |
| `dashboard.py` | Streamlit dashboard — visualizes live and historical data |

## 🚀 How to Run Locally

**1. Clone the repository**
```
git clone https://github.com/JAYASRI952007/network-monitoring.git
cd network-monitoring
```

**2. Create a virtual environment and install dependencies**
```
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

**3. Start the monitoring loop (in one terminal)**
```
python monitor.py
```

**4. Start the dashboard (in a second terminal)**
```
streamlit run dashboard.py
```

**5. Open the dashboard in your browser**
```
http://localhost:8501
```

## 📊 How It Works

1. Every `PING_INTERVAL` seconds, the monitor pings each configured device.
2. Response time and packet loss are calculated per device per cycle.
3. A device is marked DOWN only after `FAILURE_THRESHOLD` consecutive failed
   pings — this avoids false alerts from single dropped packets.
4. Every check is logged to `status_log` in SQLite for historical trend charts.
5. When a device's status changes (UP→DOWN or DOWN→UP), an incident is
   opened/closed in the `incidents` table, recording downtime duration.
6. The Streamlit dashboard reads from this database and auto-refreshes,
   displaying live status, alerts, and historical charts.

## 🐧 Production Deployment Notes

For 24/7 production use on a Linux server, `monitor.py` is designed to run as
a **systemd service** with automatic restart on failure:

```ini
[Unit]
Description=Network Monitoring Service
After=network.target

[Service]
Type=simple
ExecStart=/opt/network-monitor/venv/bin/python /opt/network-monitor/monitor.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

This ensures the monitor survives crashes and restarts automatically after
server reboots, matching real-world NOC monitoring uptime requirements.

## 📈 Future Enhancements
- Email/SMS/Slack alerts on device DOWN events
- Parallel ping checks for scaling to hundreds of devices
- User authentication for the dashboard
- Configurable alert thresholds per device