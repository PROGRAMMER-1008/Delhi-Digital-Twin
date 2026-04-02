#!/bin/bash
set -e

echo "=========================================="
echo " Delhi Digital Twin — Startup Script"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found. Install from https://python.org"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js not found. Install from https://nodejs.org"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/4] Creating Python virtual environment..."
cd "$SCRIPT_DIR/backend"
python3 -m venv venv
source venv/bin/activate

echo "[2/4] Installing Python packages..."
pip install -r requirements.txt --quiet

echo "[3/4] Installing Node packages..."
cd "$SCRIPT_DIR/frontend"
npm install --silent

echo "[4/4] Starting servers..."
echo ""
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:3000"
echo "  API Docs → http://localhost:8000/docs"
echo ""
echo "  Press Ctrl+C to stop all servers."
echo ""

# Start backend in background
cd "$SCRIPT_DIR/backend"
source venv/bin/activate
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Open browser after a moment
sleep 4
if command -v open &> /dev/null; then
    open http://localhost:3000          # macOS
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:3000     # Linux
fi

# Wait and cleanup on Ctrl+C
trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
