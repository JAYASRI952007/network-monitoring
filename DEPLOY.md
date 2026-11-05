# 🚀 Deploy in one route

This deploys the **full system** — the always-on ping monitor, the Streamlit
dashboard, SQLite storage and HTTPS — to one small Linux server, with one link.

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

There are exactly **two steps**: create a server, then run one command.

---

## Step 1 — Create the server

Any small VPS works:

| Provider | Plan | Cost |
|---|---|---|
| Oracle Cloud | Always Free (Ampere/AMD) | $0 |
| Hetzner | CX22 (2 vCPU / 4 GB) | ~€3.79/mo |
| DigitalOcean | Basic Droplet (1 vCPU / 1 GB) | $4–6/mo |

Choose **Ubuntu 22.04 or 24.04**, 1 vCPU / 1 GB RAM is enough.

In the provider's firewall / security list, allow inbound:

- **22** (SSH)
- **80** (HTTP)
- **443** (HTTPS, TCP **and** UDP)

Then connect:

```bash
ssh root@YOUR_SERVER_IP
```

---

## Step 2 — Run the setup script

```bash
git clone https://github.com/JAYASRI952007/network-monitoring.git
cd network-monitoring
sudo bash deploy/setup.sh
```

The script handles everything else:

1. installs Docker if it is missing
2. detects the server's public IP
3. asks for the dashboard username and password
4. generates the bcrypt hash and writes `.env`
5. builds the image and starts the containers
6. waits until the dashboard is healthy

It prints the link when it finishes:

```
https://monitor.<YOUR_SERVER_IP>.sslip.io
```

`sslip.io` resolves the IP embedded in the hostname, so **no domain purchase is
needed**, and Caddy obtains a free Let's Encrypt certificate automatically.

> The very first HTTPS request can take a few seconds while the certificate is
> issued. If the page fails to load, wait 30 seconds and reload.

If you own a domain, point its `A` record at the server and pass it instead:

```bash
sudo bash deploy/setup.sh --host monitor.example.com
```

Fully non-interactive (useful for cloud-init or a repeat deploy):

```bash
sudo bash deploy/setup.sh \
  --host monitor.example.com \
  --user admin \
  --password 'YourStrongPassword'
```

---

## Step 3 — Confirm it works

Open the link and log in.

Then check that monitoring is actually running:

```bash
docker compose logs -f app      # monitor + dashboard output
docker compose ps               # all services healthy
```

You should see alert lines appearing within ~10 seconds, and the dashboard's
device table should fill in.

---

## Day-to-day commands

```bash
cd network-monitoring

docker compose logs -f app          # live logs
docker compose restart app          # restart monitor + dashboard
docker compose restart caddy        # reload .env / password changes
docker compose down                 # stop everything (data is kept)
```

### Updating to the latest code

```bash
git pull
docker compose up -d --build
```

The database lives on a named volume, so it survives rebuilds.

### Backups

```bash
docker compose cp app:/data/monitor.db "./monitor-$(date +%F).db"
```

A nightly cron job is enough for a project this size.

---

## Changing which devices are monitored

Edit the `DEVICES` list in `config.py`, then restart:

```bash
nano config.py
docker compose restart app
```

The defaults are public DNS resolvers (`8.8.8.8`, `1.1.1.1`, …) that respond to
ICMP from any network, so a fresh deployment shows real UP statuses
immediately. To monitor your own machines, use their **public** IPs — private
LAN addresses (`10.x.x.x`, `192.168.x.x`) are not reachable from a VPS.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| Certificate error | DNS must resolve to the server; ports 80/443 must be open. Run `docker compose logs caddy`. |
| Login loop / 401 | Hash is wrong or unquoted in `.env`. Re-run `sudo bash deploy/setup.sh`, or `docker compose restart caddy`. |
| Dashboard shows 0 devices | Wait one full cycle (10 s+), then `docker compose logs app`. |
| Pings fail inside the container | `docker compose exec app ping -c 2 8.8.8.8` — the host or provider may block outbound ICMP. |
| Data disappears after redeploy | Confirm the `monitor-data` volume is mounted at `/data` and `DB_PATH=/data/monitor.db`. |
| Port already in use | Something else holds 80/443 — `sudo ss -lptn 'sport = :80'`, then stop it (often `apache2` or `nginx`). |
| Script says "Cannot reach the Docker daemon" | Log out and back in so the `docker` group applies, or run the script with `sudo`. |

---

## Manual setup (appendix)

Only needed if you want to do each step yourself instead of using the script.

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"     # then log out and back in

git clone https://github.com/JAYASRI952007/network-monitoring.git
cd network-monitoring

cp .env.example .env
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'YourStrongPassword'
nano .env                           # SITE_ADDRESS, ADMIN_USER, ADMIN_PASSWORD_HASH

docker compose up -d --build
```

`.env` format:

```dotenv
SITE_ADDRESS=monitor.203.0.113.10.sslip.io
ADMIN_USER=admin
ADMIN_PASSWORD_HASH='$2a$14$the_generated_hash_goes_here'
```

> **Keep the single quotes around the hash.** Compose treats single-quoted
> values literally, which preserves the `$` characters in the bcrypt hash.

---

## Security notes

- The dashboard has **no built-in authentication** — Caddy basic auth is what
  protects it. Use a strong password and never expose port 8501 directly.
- `.env` is git-ignored and created with `umask 077`; never commit it.
- Caddy redirects HTTP to HTTPS automatically.
- Keep the host patched (`sudo apt update && sudo apt upgrade`).
