#!/bin/bash

echo ""
echo "============================================"
echo "  VidBrief - YouTube Video Summarizer"
echo "============================================"
echo ""

# Step 1: Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "Install it from https://python.org"
    exit 1
fi
echo "[OK] Python found: $(python3 --version)"

# Step 2: Create virtual environment
if [ ! -d "venv" ]; then
    echo "[SETUP] Creating virtual environment..."
    python3 -m venv venv
    echo "[OK] Virtual environment created."
else
    echo "[OK] Virtual environment already exists."
fi

# Step 3: Activate venv
echo "[SETUP] Activating virtual environment..."
source venv/bin/activate

# Step 4: Install dependencies
echo "[SETUP] Installing dependencies (first run may take a few minutes)..."
pip install -r requirements.txt --quiet
echo "[OK] All dependencies installed."

# Step 5: Configure PyTorch device behavior
export PYTORCH_ENABLE_MPS_FALLBACK=1
export VIDBRIEF_DEVICE="${VIDBRIEF_DEVICE:-auto}"

echo "[SETUP] Checking Apple GPU / MPS availability..."
python - <<'PY'
import torch
print(f"[OK] PyTorch: {torch.__version__}")
print(f"[OK] MPS built: {torch.backends.mps.is_built()} | available: {torch.backends.mps.is_available()}")
PY

# Step 6: Run
echo ""
echo "============================================"
echo "  Starting VidBrief..."
echo "  Open your browser at: http://127.0.0.1:5001"
echo "  Press CTRL+C to stop the server"
echo "============================================"
echo ""
python app.py
