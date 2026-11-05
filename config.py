import os

DEVICES = [
    {"name": "Google DNS",      "ip": "8.8.8.8"},
    {"name": "Cloudflare DNS",  "ip": "1.1.1.1"},
    {"name": "OpenDNS",         "ip": "208.67.222.222"},
    {"name": "Google DNS 2",    "ip": "8.8.4.4"},
    {"name": "Quad9 DNS",       "ip": "9.9.9.9"},
    {"name": "Cloudflare DNS 2", "ip": "1.0.0.1"},
    {"name": "GitHub",          "ip": "140.82.112.3"},
    {"name": "AWS DNS",         "ip": "205.251.192.0"},
    {"name": "Quad9 DNS 2",     "ip": "149.112.112.112"},
    {"name": "Verisign DNS",    "ip": "64.6.64.6"},
]

PING_INTERVAL = 10       # seconds between monitoring cycles
PING_TIMEOUT = 2         # seconds before a ping is considered failed
FAILURE_THRESHOLD = 2    # consecutive failures before marking DOWN
DB_PATH = os.getenv("DB_PATH", "monitor.db")  # SQLite file location
PACKET_SAMPLE = 4        # pings per cycle used to calculate packet loss %