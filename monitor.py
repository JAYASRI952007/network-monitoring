import time
import config
from ping_engine import get_status
from db_manager import init_db, log_status, open_incident, close_incident

device_states = {}

for device in config.DEVICES:
    device_states[device["ip"]] = "UNKNOWN"

def run_monitor_loop():
    """
    Continuously checks all devices, logs every status to the database,
    and opens/closes incidents when a device's status changes.
    """
    init_db()
    print("Monitoring started. Press Ctrl+C to stop.")

    try:
        while True:
            for device in config.DEVICES:
                name = device["name"]
                ip = device["ip"]

                result = get_status(ip)
                current_status = result["status"]
                previous_status = device_states[ip]

                log_status(
                    device_name=name,
                    ip=ip,
                    status=current_status,
                    response_time_ms=result["avg_response_ms"],
                    packet_loss_percent=result["packet_loss_percent"]
                )

                if previous_status != "DOWN" and current_status == "DOWN":
                    open_incident(name, ip)
                    print(f"[ALERT] {name} ({ip}) went DOWN")

                elif previous_status == "DOWN" and current_status == "UP":
                    close_incident(name, ip)
                    print(f"[RECOVERED] {name} ({ip}) is back UP")

                device_states[ip] = current_status

            time.sleep(config.PING_INTERVAL)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")

if __name__ == "__main__":
    run_monitor_loop()