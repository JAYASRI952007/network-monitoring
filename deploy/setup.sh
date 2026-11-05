#!/usr/bin/env bash
#
# One-command deployment for the Network Monitoring stack.
#
#   sudo bash deploy/setup.sh
#
# Installs Docker if needed, works out a public hostname, creates the dashboard
# login, writes .env, builds the image and starts everything behind HTTPS.
#
# Non-interactive use:
#   sudo bash deploy/setup.sh --host monitor.example.com \
#        --user admin --password 'YourStrongPassword'
#
set -euo pipefail

GREEN='\033[32m'; RED='\033[31m'; YELLOW='\033[33m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { printf "${GREEN}==>${RESET} %s\n" "$*"; }
warn() { printf "${YELLOW}  !${RESET} %s\n" "$*"; }
die()  { printf "${RED}  x${RESET} %s\n" "$*" >&2; exit 1; }

usage() {
  cat <<'TXT'
Usage: sudo bash deploy/setup.sh [options]

Options:
  --host HOSTNAME     Public hostname (default: monitor.<public-ip>.sslip.io)
  --user USERNAME     Dashboard login user (default: admin)
  --password PASS     Dashboard password (otherwise you are prompted)
  --no-build          Reuse the existing image instead of rebuilding
  -h, --help          Show this help

Run with no options for the interactive path.
TXT
}

# ---------------------------------------------------------------------------
# Location: this script must run from the repository root.
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"
[ -f docker-compose.yml ] || die "docker-compose.yml not found in $PROJECT_DIR"

# ---------------------------------------------------------------------------
# Escalate before parsing arguments so "$@" is still intact.
# ---------------------------------------------------------------------------
if [ "$(id -u)" -ne 0 ] && ! docker info >/dev/null 2>&1; then
  command -v sudo >/dev/null 2>&1 || die "Run this script as root (Docker is not usable for this user)."
  warn "Docker needs root for this user - re-running with sudo..."
  exec sudo -E bash "${BASH_SOURCE[0]}" "$@"
fi

# ---------------------------------------------------------------------------
# Arguments and defaults.
# ---------------------------------------------------------------------------
SITE_ADDRESS="${SITE_ADDRESS:-}"
ADMIN_USER="${ADMIN_USER:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
DO_BUILD=1
NEED_RELOGIN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --host)
      [ $# -ge 2 ] || die "--host needs a value"
      SITE_ADDRESS="$2"; shift 2 ;;
    --user)
      [ $# -ge 2 ] || die "--user needs a value"
      ADMIN_USER="$2"; shift 2 ;;
    --password)
      [ $# -ge 2 ] || die "--password needs a value"
      ADMIN_PASSWORD="$2"; shift 2 ;;
    --no-build)
      DO_BUILD=0; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      die "Unknown option: $1 (try --help)" ;;
  esac
done

CAN_PROMPT=0
if [ -t 0 ] || [ -t 1 ]; then CAN_PROMPT=1; fi

ask() {
  # ask "<prompt>" "<default>" -> prints the answer
  local prompt="$1" default="${2:-}" value=""
  if [ -n "$default" ]; then
    printf '%s [%s]: ' "$prompt" "$default" >&2
  else
    printf '%s: ' "$prompt" >&2
  fi
  IFS= read -r value || true
  printf '%s' "${value:-$default}"
}

ask_secret() {
  # ask_secret "<prompt>" -> prints the password twice-confirmed
  local prompt="$1" first second
  while :; do
    printf '%s (min 8 chars): ' "$prompt" >&2
    IFS= read -rs first || true
    printf '\n' >&2
    if [ "${#first}" -lt 8 ]; then
      warn "Too short - try again."
      continue
    fi
    printf 'Repeat password: ' >&2
    IFS= read -rs second || true
    printf '\n' >&2
    if [ "$first" != "$second" ]; then
      warn "Passwords do not match - try again."
      continue
    fi
    printf '%s' "$first"
    return 0
  done
}

# ---------------------------------------------------------------------------
# 1. Docker
# ---------------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  ok "Installing Docker..."
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://get.docker.com | sh
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -y && apt-get install -y curl
    curl -fsSL https://get.docker.com | sh
  else
    die "No curl/wget available. Install Docker manually: https://docs.docker.com/engine/install/"
  fi
fi
command -v docker >/dev/null 2>&1 || die "Docker installation failed."

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  die "Docker Compose is not available. Install the docker-compose-plugin."
fi

docker info >/dev/null 2>&1 || {
  die "Cannot reach the Docker daemon. Log out and back in, or run with sudo."
}

# ---------------------------------------------------------------------------
# 2. Public hostname
# ---------------------------------------------------------------------------
detect_public_ip() {
  local url ip
  for url in https://api.ipify.org https://ifconfig.me/ip https://icanhazip.com; do
    ip="$(curl -4 -fsS --max-time 8 "$url" 2>/dev/null | tr -d '[:space:]')" || continue
    case "$ip" in
      ''|*[!0-9.]*) continue ;;
    esac
    printf '%s' "$ip"
    return 0
  done
  return 1
}

if [ -z "$SITE_ADDRESS" ]; then
  PUBLIC_IP="$(detect_public_ip || true)"
  if [ -n "$PUBLIC_IP" ]; then
    DEFAULT_HOST="monitor.${PUBLIC_IP}.sslip.io"
  else
    DEFAULT_HOST=""
  fi

  if [ "$CAN_PROMPT" -eq 1 ]; then
    SITE_ADDRESS="$(ask 'Public hostname for the dashboard' "$DEFAULT_HOST")"
  else
    SITE_ADDRESS="$DEFAULT_HOST"
  fi
fi

[ -n "$SITE_ADDRESS" ] || die "Could not detect a public hostname. Re-run with --host your.domain.com"

if [ -z "$ADMIN_USER" ]; then
  if [ "$CAN_PROMPT" -eq 1 ]; then
    ADMIN_USER="$(ask 'Dashboard username' 'admin')"
  else
    ADMIN_USER="admin"
  fi
fi
[ -n "$ADMIN_USER" ] || die "Dashboard username cannot be empty."

if [ -z "$ADMIN_PASSWORD" ]; then
  [ "$CAN_PROMPT" -eq 1 ] || die "No password supplied. Re-run with --password '...'"
  ADMIN_PASSWORD="$(ask_secret 'Dashboard password')"
fi
[ "${#ADMIN_PASSWORD}" -ge 8 ] || die "Password must be at least 8 characters."

# ---------------------------------------------------------------------------
# 3. Password hash + .env
# ---------------------------------------------------------------------------
ok "Generating the login hash..."
PASSWORD_HASH="$(docker run --rm caddy:2-alpine caddy hash-password --plaintext "$ADMIN_PASSWORD" 2>/dev/null | tr -d '\r\n')"

# shellcheck disable=SC2016  # '$2' is a literal bcrypt prefix, not a variable
case "$PASSWORD_HASH" in
  '$2'*) ;;
  *) die "Could not generate a password hash (is Docker able to pull images?)" ;;
esac

if [ -f .env ]; then
  warn "Replacing the existing .env"
fi

umask 077
cat > .env <<EOF
# Generated by deploy/setup.sh - do not commit this file.
SITE_ADDRESS=${SITE_ADDRESS}
ADMIN_USER=${ADMIN_USER}
ADMIN_PASSWORD_HASH='${PASSWORD_HASH}'
EOF
ok "Wrote .env for ${SITE_ADDRESS}"

# Hand the file to the invoking user so they can edit it without sudo later.
if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
  chown "${SUDO_USER}":"$(id -gn "${SUDO_USER}")" .env 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# 4. Build and start
# ---------------------------------------------------------------------------
if [ "$DO_BUILD" -eq 1 ]; then
  ok "Building and starting the containers (first run takes a few minutes)..."
  "${COMPOSE[@]}" up -d --build
else
  ok "Starting the containers..."
  "${COMPOSE[@]}" up -d
fi

# ---------------------------------------------------------------------------
# 5. Wait for the dashboard
# ---------------------------------------------------------------------------
ok "Waiting for the dashboard to report healthy..."
APP_ID="$("${COMPOSE[@]}" ps -q app 2>/dev/null | head -n 1 || true)"
HEALTHY=0
if [ -n "$APP_ID" ]; then
  for _ in $(seq 1 60); do
    STATE="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$APP_ID" 2>/dev/null || true)"
    if [ "$STATE" = "healthy" ] || [ "$STATE" = "running" ]; then
      HEALTHY=1
      break
    fi
    sleep 3
  done
fi

# Let the invoking user run docker/compose without sudo from now on.
if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
  if ! id -nG "${SUDO_USER}" | tr ' ' '\n' | grep -qx docker; then
    usermod -aG docker "${SUDO_USER}" 2>/dev/null || true
    NEED_RELOGIN=1
  fi
fi

printf '\n'
if [ "$HEALTHY" -eq 1 ]; then
  printf '%s\n\n' "${GREEN}${BOLD}  Deployment complete${RESET}"
else
  printf '%s\n\n' "${YELLOW}${BOLD}  Containers started, but the dashboard is not healthy yet${RESET}"
  warn "Check the logs with: ${COMPOSE[*]} logs -f app"
  printf '\n'
fi

cat <<TXT
  Link:      https://${SITE_ADDRESS}
  Username:  ${ADMIN_USER}
  Password:  (the one you just entered)

  The first HTTPS request can take a few seconds while the certificate
  is issued. If it fails, wait 30 seconds and reload.

  Next:
    ${COMPOSE[*]} logs -f app      # monitor + dashboard output
    ${COMPOSE[*]} ps               # container status
    ${COMPOSE[*]} restart caddy    # after changing .env

  Make sure inbound ports 80 and 443 are open in your provider firewall.
TXT

if [ "$NEED_RELOGIN" -eq 1 ]; then
  printf '\n'
  warn "You were added to the 'docker' group. Log out and back in so you can"
  warn "run docker commands without sudo."
fi
