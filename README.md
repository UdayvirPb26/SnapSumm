# Snap-Summ - YouTube Video Summarizer

Snap-Summ is an AI-powered Flask web app that summarizes YouTube videos from transcripts, saves user summary history, supports translation into Indian languages, and stores app data in PostgreSQL.

## Features

- YouTube transcript extraction from supported videos
- AI summary generation with a local BART model
- Key point extraction for quick review
- User registration and login
- Guest mode for trying the app without saving history
- Save summaries to user history
- View, rename, and delete saved summaries
- Admin dashboard for managing users
- Summary translation support for Hindi, Punjabi, Bengali, Tamil, and Telugu
- PostgreSQL database support through `DATABASE_URL`
- SQLite fallback for local development when `DATABASE_URL` is not set
- pgAdmin-compatible database management
- Apple Silicon GPU support through PyTorch MPS when available

## Project Structure

```text
vidbrief/
├── app.py                         # Flask server and routes
├── models.py                      # SQLAlchemy database models
├── summarizer.py                  # Transcript and AI summarization logic
├── migrate_sqlite_to_postgres.py  # One-time SQLite to PostgreSQL migration script
├── requirements.txt               # Python dependencies
├── START_HERE_WINDOWS.bat         # Windows launch helper
├── START_HERE_MAC_LINUX.sh        # macOS/Linux launch helper
├── templates/                     # Jinja2 HTML templates
├── static/                        # CSS/JS/static assets
└── models/                        # Local BART model files, ignored by Git
```

## Database

Snap-Summ now supports PostgreSQL.

The app reads the database connection from `DATABASE_URL`:

```bash
export DATABASE_URL="postgresql://snapsumm_user:YOUR_PASSWORD@localhost:5432/snapsumm_db"
```

If `DATABASE_URL` is not set, the app falls back to local SQLite:

```text
vidbrief.db
```

Local database files are ignored by Git:

```text
*.db
*.db.backup
```

## PostgreSQL Setup On macOS

Install PostgreSQL 18:

```bash
brew install postgresql@18
brew services start postgresql@18
```

Add PostgreSQL commands to your shell:

```bash
echo 'export PATH="$(brew --prefix postgresql@18)/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Create the app user and database:

```bash
createuser snapsumm_user --pwprompt
createdb -O snapsumm_user snapsumm_db
```

Grant permissions:

```bash
psql -d snapsumm_db
```

```sql
GRANT ALL PRIVILEGES ON DATABASE snapsumm_db TO snapsumm_user;
GRANT ALL ON SCHEMA public TO snapsumm_user;
\q
```

Set the database URL:

```bash
export DATABASE_URL="postgresql://snapsumm_user:YOUR_PASSWORD@localhost:5432/snapsumm_db"
```

To avoid typing it every time on your own laptop, you can save it:

```bash
echo 'export DATABASE_URL="postgresql://snapsumm_user:YOUR_PASSWORD@localhost:5432/snapsumm_db"' >> ~/.zshrc
source ~/.zshrc
```

## pgAdmin GUI

Install pgAdmin:

```bash
brew install --cask pgadmin4
open -a pgAdmin\ 4
```

Register a new server with:

```text
Name: SnapSumm Local PostgreSQL
Host name/address: localhost
Port: 5432
Maintenance database: snapsumm_db
Username: snapsumm_user
Password: your PostgreSQL password
```

To view data:

```text
Servers
-> SnapSumm Local PostgreSQL
-> Databases
-> snapsumm_db
-> Schemas
-> public
-> Tables
```

Open `summary` or `user` with:

```text
Right-click table -> View/Edit Data -> All Rows
```

To reload table data after saving a new summary, click the **Play** button in the table toolbar to re-run the query.

## Run The App

Activate the virtual environment:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run with PostgreSQL:

```bash
export DATABASE_URL="postgresql://snapsumm_user:YOUR_PASSWORD@localhost:5432/snapsumm_db"
python3 app.py
```

If `DATABASE_URL` is already saved in `~/.zshrc`, run:

```bash
python3 app.py
```

Open:

```text
http://127.0.0.1:5001
```

## SQLite To PostgreSQL Migration

Use this only when moving existing local SQLite data into PostgreSQL.

Make sure `DATABASE_URL` points to PostgreSQL:

```bash
export DATABASE_URL="postgresql://snapsumm_user:YOUR_PASSWORD@localhost:5432/snapsumm_db"
```

Run:

```bash
python3 migrate_sqlite_to_postgres.py
```

The script copies users and summaries from `vidbrief.db` into PostgreSQL.

Keep `vidbrief.db` and `vidbrief.db.backup` locally for a while after migration, but do not commit them.

## First Run Notes

- The first model load can take time.
- The app uses the local model at `models/bart-large-cnn` by default.
- Model files are ignored by Git because they are large.
- On Apple Silicon Macs, PyTorch can use MPS acceleration when available.

Check Apple Silicon GPU support:

```bash
python3 -c "import torch; print(torch.backends.mps.is_built(), torch.backends.mps.is_available())"
```

Force CPU if needed:

```bash
VIDBRIEF_DEVICE=cpu python3 app.py
```

Tune summarization speed:

```bash
VIDBRIEF_BATCH_SIZE=3 VIDBRIEF_NUM_BEAMS=1 python3 app.py
```

Tune for higher quality:

```bash
VIDBRIEF_BATCH_SIZE=1 VIDBRIEF_NUM_BEAMS=4 python3 app.py
```

Use a different local model path:

```bash
VIDBRIEF_MODEL=/absolute/path/to/local/model python3 app.py
```

## Common Errors And Fixes

| Error | Fix |
|---|---|
| `ModuleNotFoundError` | Activate `venv`, then run `pip install -r requirements.txt` |
| `psql: command not found` | Add PostgreSQL 18 to PATH with `export PATH="$(brew --prefix postgresql@18)/bin:$PATH"` |
| App saves data but pgAdmin does not update | In pgAdmin, click the table toolbar **Play** button to re-run the query |
| App data appears in SQLite instead of PostgreSQL | Check `echo $DATABASE_URL`; it must point to PostgreSQL |
| `No transcript found` | Use a YouTube video with available captions/transcript |
| Port already in use | Stop the old Flask process or change the port in `app.py` |

## Git Safety

Do not commit local databases or secret files:

```text
vidbrief.db
vidbrief.db.backup
.env
```

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Flask |
| Database ORM | Flask-SQLAlchemy |
| Database | PostgreSQL, with SQLite fallback |
| Authentication | Flask-Login |
| AI Summarization | BART / Hugging Face Transformers |
| Transcript Extraction | youtube-transcript-api |
| Translation | deep-translator |
| Deep Learning Backend | PyTorch |
| Frontend | HTML, CSS, JavaScript |
| Templates | Jinja2 |
| Database GUI | pgAdmin 4 |
