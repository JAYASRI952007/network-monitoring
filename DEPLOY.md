# 🚀 Deploy to a VPS with Docker

This guide deploys the **full system** — the always-on ping monitor, the
Streamlit dashboard, SQLite storage and HTTPS — to a single small Linux server.

```
Internet
   │  HTTPS + basic auth
   ▼
Caddy :443
   │
   ▼
app container (Supervisor)
   ├── monitor.py        → writes /data/monitor.db
   └── streamlit :8501   → reads /data/monitor.db
```

Both processes restart automatically if they crash or the server reboots.

---

## 1. Create the server

Any small VPS works. Suggested options:

| Provider | Plan | Cost |
|---|---|---|
| Oracle Cloud | Always Free (Ampere/AMD) | $0 |
| Hetzner | CX22 (2 vCPU / 4 GB) | ~€3.79/mo |
| DigitalOcean | Basic Droplet (1 vCPU / 1 GB) | $4–6/mo |

Use **Ubuntu 22.04 or 24.04**. 1 vCPU / 1 GB RAM is enough.

Open inbound ports **22 (SSH), 80 (HTTP), 443 (HTTPS, TCP + UDP)** in both the
provider firewall/security list and the OS firewall.

---

## 2. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
```

Log out and back in (or run `newgrp docker`) so the group change applies.

---

## 3. Get the code

> **Before deploying:** the default `config.py` contains LAN addresses
> (`10.186.62.x`) and a test host (`10.0.0.199`). From a VPS those will always
> be DOWN. Replace or remove them first — see section 8.

```bash
git clone https://github.com/JAYASRI952007/network-monitoring.git
cd network-monitoring
```

The repository is **private**, so the server needs credentials:

- easiest: temporarily make the repo public, or
- authenticate Git on the server with a GitHub token / deploy key, or
- copy the folder from your computer with `scp -r`.

---

## 4. Configure the deployment

```bash
cp .env.example .env
```

Generate a password hash for the dashboard login:

```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'ChooseAStrongPassword'
```

Edit `.env`:

```dotenv
# Replace the IP with your server's public IPv4 address.
# sslip.io resolves this automatically, so no DNS purchase is needed.
SITE_ADDRESS=monitor.203.0.113.10.sslip.io

ADMIN_USER=admin
ADMIN_PASSWORD_HASH='$2a$14$the_generated_hash_goes_here'
```

> **Keep the single quotes around the hash.** Compose treats single-quoted
> values literally, which preserves the `$` characters in the bcrypt hash.

If you own a domain, point its `A` record at the server IP and use that
hostname instead. Caddy will obtain a free Let's Encrypt certificate either way.

---

## 5. Start it

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f app
```

The first build takes a few minutes. Wait until the logs show monitoring
activity, then open:

```
https://monitor.<YOUR_SERVER_IP>.sslip.io
```

Log in with the `ADMIN_USER` and password you configured.

> The very first HTTPS request may take a few seconds while Caddy requests
> the certificate. `docker compose logs -f caddy` shows its progress.

---

## 6. Updating

```bash
git pull
docker compose up -d --build
```

Your SQLite data is on a named volume, so it survives rebuilds.

---

## 7. Backups

```bash
docker compose cp app:/data/monitor.db "./monitor-$(date +%F).db"
```

A nightly cron job is enough for a project of this size.

---

## 8. Before you deploy — device list

`config.py` still contains **local LAN addresses** (`10.186.62.x`) and a test
host (`10.0.0.199`). When the monitor runs on a VPS, those addresses are not
reachable, so they will show as DOWN.

Edit `config.py` before deploying and replace them with real public targets
(or remove them). Public DNS resolvers such as `8.8.8.8` and `1.1.1.1` work
from anywhere.

---

## 9. Troubleshooting

| Symptom | Check |
|---|---|
| Certificate error | DNS must resolve to the server; ports 80/443 must be open. Run `docker compose logs caddy`. |
| Login loop / 401 | Hash is wrong or missing quotes. Regenerate it and run `docker compose restart caddy`. |
| Dashboard shows 0 devices | Wait one full cycle (10 s+), then `docker compose logs app`. |
| Pings fail inside the container | `docker compose exec app ping -c 2 8.8.8.8` — the host or provider may block outbound ICMP. |
| Data disappears after redeploy | Confirm the `monitor-data` volume is mounted at `/data` and `DB_PATH=/data/monitor.db`. |
| Streamlit not loading | `docker compose logs app`; verify Caddy is proxying `app:8501`. |

---

## Security notes

- The dashboard has **no built-in authentication** — Caddy basic auth is what
  protects it. Use a strong password and never expose port 8501 directly.
- `.env` is git-ignored; never commit it.
- Caddy redirects HTTP to HTTPS automatically.
- Keep the host patched (`sudo apt update && sudo apt upgrade`).
