# Snap-Summ — YouTube Video Summarizer

An AI-powered Flask web app that summarizes any YouTube video using BART (facebook/bart-large-cnn).

---

## Project Structure

```
vidbrief/
├── app.py                    ← Flask server (run this to start)
├── summarizer.py             ← All AI logic (BART + transcript)
├── requirements.txt          ← Python dependencies
├── START_HERE_WINDOWS.bat    ← One-click launch (Windows)
├── START_HERE_MAC_LINUX.sh   ← One-click launch (Mac/Linux)
├── templates/
│   └── index.html            ← Frontend UI
├── static/                   ← (optional CSS/JS files)
└── .vscode/
    ├── launch.json           ← F5 run config for VS Code
    └── settings.json         ← Auto-selects venv interpreter
```

---

## How to Run (Step by Step)

### Option A — One-Click Script (Easiest)

**Windows:**
1. Open the `vidbrief` folder
2. Double-click `START_HERE_WINDOWS.bat`
3. Wait for setup (first time: ~5 minutes to download PyTorch)
3. Open your browser → http://127.0.0.1:5001

**Mac / Linux:**
1. Open Terminal in the `vidbrief` folder
2. Run: `chmod +x START_HERE_MAC_LINUX.sh && ./START_HERE_MAC_LINUX.sh`
3. Open your browser → http://127.0.0.1:5001

---

### Option B — Run inside VS Code (F5 or Green Play Button)

Follow these steps exactly — do them once and the project will always just work.

**Step 1 — Open the folder in VS Code**
- Open VS Code
- Go to File → Open Folder → select the `vidbrief` folder
- Make sure you open the FOLDER (not a single file)

**Step 2 — Open the integrated terminal**
- Press `Ctrl + `` (backtick) or go to Terminal → New Terminal
- You should see a terminal at the bottom of VS Code

**Step 3 — Create a virtual environment**
```bash
# Windows
python -m venv venv

# Mac / Linux
python3 -m venv venv
```

**Step 4 — Activate the virtual environment**
```bash
# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```
✅ You should now see `(venv)` at the start of your terminal prompt.

**Step 5 — Install dependencies**
```bash
pip install -r requirements.txt
```
⏳ This downloads PyTorch + BART model dependencies (~800MB). Do this only once.

**Step 6 — Select the venv Python interpreter in VS Code**
- Press `Ctrl+Shift+P`
- Type: `Python: Select Interpreter`
- Choose the one that shows `venv` in the path (e.g., `./venv/Scripts/python.exe`)

**Step 7 — Run the app**
- Press **F5** (or click the green ▶ play button at the top right)
- Or in the terminal run: `python app.py`

**Step 8 — Open the app**
- Open your browser
- Go to: **http://127.0.0.1:5001**
- Paste any YouTube URL and click Summarize!

---

## First Run Notes

- The first time you run the app, BART model weights (~1.6GB) are downloaded automatically from HuggingFace and cached on your computer. This only happens once.
- Subsequent runs load the model from cache and are much faster.
- Model loading takes ~20–30 seconds on startup — wait for the terminal to print "✅ Model loaded successfully!" before opening the browser.
- On Apple Silicon Macs, the app uses PyTorch MPS (`mps`) automatically when it is available. The terminal should show `Using device: mps` and `Model parameters are on: mps:0`.

### Mac GPU Check

Run this inside the project venv:

```bash
source venv/bin/activate
python -c "import torch; print(torch.backends.mps.is_built(), torch.backends.mps.is_available())"
```

Expected result on Apple Silicon is `True True`. If the second value is `False`, make sure you are using the `venv` Python and not an Intel/Rosetta Python. You can force CPU for testing with:

```bash
VIDBRIEF_DEVICE=cpu python app.py
```

For faster Apple GPU summarization, the app batches chunk summaries and uses `num_beams=2` by default. You can tune speed from the terminal:

```bash
# More speed, slightly lower quality
VIDBRIEF_BATCH_SIZE=3 VIDBRIEF_NUM_BEAMS=1 python app.py

# Better quality, slower
VIDBRIEF_BATCH_SIZE=1 VIDBRIEF_NUM_BEAMS=4 python app.py
```

For a much faster but smaller model, run:

```bash
VIDBRIEF_MODEL=sshleifer/distilbart-cnn-12-6 python app.py
```

---

## Common Errors and Fixes

| Error | Fix |
|---|---|
| `python is not recognized` | Install Python 3.9+ and check "Add to PATH" during install |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` with venv activated |
| `No transcript found` | Use a video with English captions (try a TED Talk) |
| `Port 5000 in use` | In `app.py`, change `app.run(debug=True)` to `app.run(debug=True, port=5001)` |
| `(venv) not showing` | Run the activate command again (Step 4 above) |

---

## Tech Stack

| Component | Technology |
|---|---|
| Web Framework | Flask 3.0 |
| AI Summarization | facebook/bart-large-cnn (HuggingFace) |
| Transcript Extraction | youtube-transcript-api |
| Deep Learning Backend | PyTorch |
| Frontend | HTML / CSS / Vanilla JS |
| Templating | Jinja2 |
