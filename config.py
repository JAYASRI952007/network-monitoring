DEVICES = [
    {"name": "Google DNS",      "ip": "8.8.8.8"},
    {"name": "Cloudflare DNS",  "ip": "1.1.1.1"},
    {"name": "OpenDNS",         "ip": "208.67.222.222"},
    {"name": "Local Gateway",   "ip": "10.186.62.107"},
    {"name": "Quad9 DNS",       "ip": "9.9.9.9"},
    {"name": "This PC",        "ip": "10.186.62.157"},
    {"name": "GitHub",          "ip": "140.82.112.3"},
    {"name": "AWS DNS",         "ip": "205.251.192.0"},
    {"name": "Level3 DNS",      "ip": "4.2.2.2"},
    {"name": "Nonexistent Host",    "ip": "10.0.0.199"},
]

PING_INTERVAL = 10       # seconds between monitoring cycles
PING_TIMEOUT = 2         # seconds before a ping is considered failed
FAILURE_THRESHOLD = 2    # consecutive failures before marking DOWN
DB_PATH = "monitor.db"   # SQLite file location
PACKET_SAMPLE = 4        # pings per cycle used to calculate packet loss %