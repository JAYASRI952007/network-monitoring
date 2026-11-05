from ping3 import ping
import subprocess
import config
def check_host(ip):
    """
    Sends a single ping to the given IP.
    Returns response time in milliseconds if successful, None if it failed.
    """
    try:
        response_time = ping(ip, timeout=config.PING_TIMEOUT, unit='ms')
        return response_time
    except PermissionError:
        # Fallback to system ping command (no admin required)
        try:
            result = subprocess.run(["ping", "-n", "1", ip], capture_output=True, text=True, timeout=5)
            output = result.stdout
            # Parse time=XXms from output
            import re
            match = re.search(r"time[=<]\s*(\d+\.?\d*)\s*ms", output)
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