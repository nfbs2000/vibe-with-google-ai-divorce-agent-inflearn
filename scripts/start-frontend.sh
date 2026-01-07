#!/usr/bin/env bash
# Start Frontend server only
# Usage:
#   scripts/start-frontend.sh [--port P] [--backend-url URL]
#
# Examples:
#   scripts/start-frontend.sh --port 8005
#   scripts/start-frontend.sh --backend-url http://localhost:8004

set -euo pipefail

# -------- Config (defaults) --------
FRONTEND_PORT="8005"
BACKEND_URL="http://localhost:8004"

# -------- Paths --------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
PIDS_DIR="${ROOT_DIR}/.pids"
FRONTEND_DIR="${ROOT_DIR}/frontend"

mkdir -p "${LOG_DIR}" "${PIDS_DIR}"

# -------- Argument parsing --------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      FRONTEND_PORT="$2"; shift 2 ;;
    --backend-url)
      BACKEND_URL="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: scripts/start-frontend.sh [--port P] [--backend-url URL]"; exit 0 ;;
    *)
      echo "Unknown argument: $1"; exit 1 ;;
  esac
done

msg() {
  echo -e "\033[1;34m[FRONTEND]\033[0m $*"
}
warn() {
  echo -e "\033[1;33m[WARN]\033[0m $*"
}
err() {
  echo -e "\033[1;31m[ERROR]\033[0m $*" >&2
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

# -------- Frontend (Vite + React) --------
start_frontend() {
  kill_port_process "${FRONTEND_PORT}"
  msg "Starting Frontend (Vite) on port ${FRONTEND_PORT}"
  msg "Backend API URL: ${BACKEND_URL}"
  
  pushd "${FRONTEND_DIR}" > /dev/null
  
  if [[ ! -d "node_modules" ]]; then
    msg "Installing frontend dependencies..."
    npm install
  fi
  
  # Check if backend is running
  if command -v curl >/dev/null 2>&1; then
    if curl -s "${BACKEND_URL}/api/system/health" >/dev/null 2>&1; then
      msg "✓ Backend is running at ${BACKEND_URL}"
    else
      warn "⚠ Backend might not be running at ${BACKEND_URL}"
      warn "  Start backend with: scripts/start-backend.sh"
    fi
  fi
  
  msg "Frontend ready — http://localhost:${FRONTEND_PORT}/"
  
  # Save PID for later management
  echo $$ > "${PIDS_DIR}/frontend.pid"
  
  # Set environment variable for backend URL if needed
  export VITE_API_BASE_URL="${BACKEND_URL}"
  
  exec npm run dev -- --port "${FRONTEND_PORT}" --host 0.0.0.0
}

# -------- Main --------
start_frontend