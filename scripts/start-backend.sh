#!/usr/bin/env bash
# Start Backend server only
# Usage:
#   scripts/start-backend.sh [--port P] [--env-file PATH]
#
# Examples:
#   scripts/start-backend.sh --port 8004
#   scripts/start-backend.sh --env-file .env.local

set -euo pipefail

# -------- Config (defaults) --------
BACKEND_PORT="8004"
ENV_FILE=".env"

# -------- Paths --------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
PIDS_DIR="${ROOT_DIR}/.pids"
BACKEND_DIR="${ROOT_DIR}/adk-backend"

mkdir -p "${LOG_DIR}" "${PIDS_DIR}"

# -------- Argument parsing --------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      BACKEND_PORT="$2"; shift 2 ;;
    --env-file)
      ENV_FILE="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: scripts/start-backend.sh [--port P] [--env-file PATH]"; exit 0 ;;
    *)
      echo "Unknown argument: $1"; exit 1 ;;
  esac
done

msg() {
  echo -e "\033[1;32m[BACKEND]\033[0m $*"
}
warn() {
  echo -e "\033[1;33m[WARN]\033[0m $*"
}
err() {
  echo -e "\033[1;31m[ERROR]\033[0m $*" >&2
}

# -------- Env loading --------
load_env() {
  local env_path="${ROOT_DIR}/${ENV_FILE}"
  if [[ -f "${env_path}" ]]; then
    msg "Loading env from ${env_path}"
    set -o allexport
    # shellcheck disable=SC1090
    source "${env_path}"
    set +o allexport
  else
    warn "Env file not found: ${env_path}. Proceeding with current environment variables."
  fi
}

# -------- Port Management --------
kill_port_process() {
  local port=$1
  local pid
  pid=$(lsof -ti :"${port}" 2>/dev/null || true)

  if [[ -n "${pid}" ]]; then
    warn "Port ${port} is in use by PID ${pid}. Killing process..."
    kill -9 "${pid}" 2>/dev/null || true
    sleep 1
    msg "Process killed successfully"
  fi
}

# -------- Backend (Python + Uvicorn) --------
start_backend() {
  kill_port_process "${BACKEND_PORT}"
  msg "Starting Backend (Uvicorn) on port ${BACKEND_PORT}"
  pushd "${BACKEND_DIR}" > /dev/null
  
  if [[ ! -d "venv" ]]; then
    msg "Creating Python venv in adk-backend/venv"
    python3 -m venv venv
  fi
  
  # shellcheck disable=SC1091
  source venv/bin/activate
  
  msg "Installing/updating dependencies..."
  pip install --upgrade pip >/dev/null
  pip install -e ".[dev]" >/dev/null
  
  msg "Backend ready — http://localhost:${BACKEND_PORT}/health"
  msg "API Documentation — http://localhost:${BACKEND_PORT}/docs"
  
  # Save PID for later management
  echo $$ > "${PIDS_DIR}/backend.pid"
  
  exec python -m uvicorn adk_backend.app:app --host 0.0.0.0 --port "${BACKEND_PORT}" --reload
}

# -------- Main --------
load_env
start_backend