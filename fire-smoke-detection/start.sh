#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# PYREGUARD — Quick-Start Script
# Run on the REMOTE SSH server:  bash start.sh
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

BOLD="\e[1m"; RED="\e[31m"; GRN="\e[32m"; YLW="\e[33m"; BLU="\e[34m"; RST="\e[0m"
log()  { echo -e "${GRN}[INFO]${RST}  $*"; }
warn() { echo -e "${YLW}[WARN]${RST}  $*"; }
err()  { echo -e "${RED}[ERROR]${RST} $*"; exit 1; }

# ── 1. Check Python ──────────────────────────────────────────────────────────
python3 --version &>/dev/null || err "Python 3 not found. Install with: sudo apt install python3"
log "Python: $(python3 --version)"

# ── 2. Check Node ────────────────────────────────────────────────────────────
node --version &>/dev/null || err "Node.js not found. Install: https://nodejs.org"
log "Node:   $(node --version)"

# ── 3. Backend setup ─────────────────────────────────────────────────────────
log "Setting up backend..."
cd backend

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  log "Virtual environment created"
fi

source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
log "Backend dependencies installed"

# Create models directory
mkdir -p models

# Check if custom weights exist
if [ ! -f "models/fire_smoke_yolov8.pt" ]; then
  warn "Custom model weights not found at backend/models/fire_smoke_yolov8.pt"
  warn "The system will use YOLOv8l pretrained weights + HSV colour heuristics."
  warn "For >95% accuracy, train with: python train.py --api-key YOUR_ROBOFLOW_KEY"
  warn "Dataset: https://universe.roboflow.com/reyzi916/fire-smoke-det/dataset/6"
fi

# Start Flask backend in background
log "Starting Flask backend on port 5050..."
nohup python app.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../backend.pid
log "Backend started (PID: $BACKEND_PID)"
deactivate
cd ..

# ── 4. Frontend setup ────────────────────────────────────────────────────────
log "Setting up frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
  npm install
  log "Node modules installed"
fi

# Start Vite dev server in background
log "Starting React frontend on port 3000..."
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid
log "Frontend started (PID: $FRONTEND_PID)"
cd ..

# ── 5. Summary ───────────────────────────────────────────────────────────────
sleep 2
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════════════${RST}"
echo -e "${BOLD}  🔥  PYREGUARD — Services Started${RST}"
echo -e "${BOLD}════════════════════════════════════════════════════════════${RST}"
echo -e "  Backend API : http://localhost:5050/api/health"
echo -e "  Frontend UI : http://localhost:3000"
echo ""
echo -e "${BOLD}  SSH Tunnel (run on your LOCAL laptop):${RST}"
echo -e "  ${BLU}ssh -L 3000:localhost:3000 -L 5050:localhost:5050 $(whoami)@$(hostname -I | awk '{print $1}')${RST}"
echo ""
echo -e "  Then open ${GRN}http://localhost:3000${RST} in your local browser."
echo -e "  Your LOCAL webcam will be used for detection."
echo ""
echo -e "  Logs:  tail -f logs/backend.log   (backend)"
echo -e "         tail -f logs/frontend.log  (frontend)"
echo ""
echo -e "  Stop:  bash stop.sh"
echo -e "${BOLD}════════════════════════════════════════════════════════════${RST}"
