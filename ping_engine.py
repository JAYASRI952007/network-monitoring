from ping3 import ping
import platform
import re
import subprocess
import config
def check_host(ip):
    """
    Sends a single ping to the given IP.
    Returns response time in milliseconds if successful, None if it failed.
    """
    try:
        response_time = ping(ip, timeout=config.PING_TIMEOUT, unit='ms')
        # ping3 returns False (not None) when the OS reports an error.
        return None if response_time is False else response_time
    except PermissionError:
        # Fallback to the system ping command (no raw-socket privileges).
        try:
            if platform.system() == "Windows":
                command = ["ping", "-n", "1", "-w", str(int(config.PING_TIMEOUT * 1000)), ip]
            else:
                command = ["ping", "-c", "1", "-W", str(int(config.PING_TIMEOUT)), ip]

            result = subprocess.run(command, capture_output=True, text=True, timeout=5)
            # Parse time=XXms from either Windows or Linux output.
            match = re.search(r"time[=<]\s*(\d+\.?\d*)\s*ms", result.stdout)
            if match:
                return float(match.group(1))
            else:
                return None
        except Exception:
            return None
    except Exception:
        return None
def get_packet_loss(ip, samples=None):
    """
    Sends multiple pings to calculate packet loss percentage.
    Returns (loss_percent, list_of_response_times).
    """
    if samples is None:
        samples = config.PACKET_SAMPLE

    results = []
    for _ in range(samples):
        rt = check_host(ip)
        results.append(rt)

    failed = results.count(None)
    loss_percent = (failed / samples) * 100

    return loss_percent, results
def get_status(ip):
    """
    Determines if a device is UP or DOWN based on FAILURE_THRESHOLD
    consecutive failed pings.
    Returns a dict with status, avg response time, and packet loss.
    """
    loss_percent, results = get_packet_loss(ip)

    consecutive_failures = 0
    max_consecutive_failures = 0
    for r in results:
        if r is None:
            consecutive_failures += 1
            max_consecutive_failures = max(max_consecutive_failures, consecutive_failures)
        else:
            consecutive_failures = 0

    status = "DOWN" if max_consecutive_failures >= config.FAILURE_THRESHOLD else "UP"

    successful_pings = [r for r in results if r is not None]
    avg_response_time = sum(successful_pings) / len(successful_pings) if successful_pings else None

    return {
        "ip": ip,
        "status": status,
        "avg_response_ms": round(avg_response_time, 2) if avg_response_time else None,
        "packet_loss_percent": round(loss_percent, 2),
    }
if __name__ == "__main__":
    import config
    for device in config.DEVICES:
        result = get_status(device["ip"])
        print(device["name"], "->", result)