from ping_engine import get_status

if __name__ == "__main__":
    ip = "8.8.8.8"
    result = get_status(ip)
    print(f"Ping result for {ip}: {result}")
