from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch    
import os
import re
import time
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Model: facebook/bart-large-cnn
#
# Token limits:
#   - Max INPUT  : 1024 tokens ≈ 700–750 words per chunk (we use 550 — safe)
#   - Max OUTPUT : 1024 tokens (model hard limit per single inference call)
#
# With larger output capacity, we can generate 300–400 word summaries efficiently
# through multi-chunk passes and consolidation while maintaining quality.
# ─────────────────────────────────────────────────────────────────────────────

print("Loading summarization model...")


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def select_device() -> torch.device:
    """
    Prefer Apple Silicon GPU (MPS) on Mac, then CUDA, then CPU.
    Set VIDBRIEF_DEVICE=cpu/mps/cuda to force a specific backend while testing.
    """
    requested = os.getenv("VIDBRIEF_DEVICE", "auto").strip().lower()
    available = {
        "cpu": True,
        "mps": torch.backends.mps.is_available(),
        "cuda": torch.cuda.is_available(),
    }

    if requested in {"cpu", "mps", "cuda"}:
        if available[requested]:
            return torch.device(requested)
        print(f"Requested device '{requested}' is not available in this process.")

    if available["mps"]:
        return torch.device("mps")
    if available["cuda"]:
        return torch.device("cuda")

    print("Apple GPU (MPS) is not available in this process; falling back to CPU.")
    if torch.backends.mps.is_built():
        print("MPS support is built into PyTorch, but this process cannot access it.")
    return torch.device("cpu")


DEVICE = select_device()
print(f"Using device: {DEVICE}")

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "bart-large-cnn"
MODEL_PATH = Path(os.getenv("VIDBRIEF_MODEL", str(DEFAULT_MODEL_PATH))).expanduser()
print(f"Using local model: {MODEL_PATH}")

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Local BART model not found at '{MODEL_PATH}'. "
        "Set VIDBRIEF_MODEL to the directory containing config.json, "
        "model.safetensors, and the tokenizer files."
    )

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_PATH,
    local_files_only=True,
).to(DEVICE)
model.eval()

MODEL_DEVICE = next(model.parameters()).device
print(f"Model parameters are on: {MODEL_DEVICE}")

TOKENIZER_MAX_LENGTH = 1024
SAFE_TOKEN_LIMIT = 992
DEFAULT_BATCH_SIZE = 2 if DEVICE.type in {"mps", "cuda"} else 1
BATCH_SIZE = max(1, int_env("VIDBRIEF_BATCH_SIZE", DEFAULT_BATCH_SIZE))
print(f"Model loaded successfully! (token limit: {TOKENIZER_MAX_LENGTH})")
print(f"Summarization batch size: {BATCH_SIZE}\n")

# ── facebook/bart-large-cnn constants ─────────────────────────────────────────
CHUNK_WORD_LIMIT  = int_env("VIDBRIEF_CHUNK_WORDS", 550)
CHUNK_MAX_OUT     = int_env("VIDBRIEF_CHUNK_MAX_OUT", 160)
CHUNK_MIN_OUT     = int_env("VIDBRIEF_CHUNK_MIN_OUT", 45)

FINAL_WORD_LIMIT  = 700   # max words fed into consolidation pass (safe for BART 1024 token encoder)
FINAL_MAX_OUT     = int_env("VIDBRIEF_FINAL_MAX_OUT", 260)
FINAL_MIN_OUT     = int_env("VIDBRIEF_FINAL_MIN_OUT", 120)

TARGET_MIN_WORDS  = 300   # target final summary minimum word count
TARGET_MAX_WORDS  = 400   # target final summary maximum word count
GENERATION_KWARGS = {
    "do_sample": False,
    "num_beams": int_env("VIDBRIEF_NUM_BEAMS", 2),
    "early_stopping": True,
}
# ─────────────────────────────────────────────────────────────────────────────


def word_count(text: str) -> int:
    return len(text.split())


def word_overlap(a: str, b: str) -> float:
    wa = set(re.findall(r'\b\w{4,}\b', a.lower()))
    wb = set(re.findall(r'\b\w{4,}\b', b.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def split_sentences(text: str) -> list[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if len(sentences) > 1:
        return sentences

    words = text.split()
    return [" ".join(words[i:i + 35]) for i in range(0, len(words), 35)]


def trim_to_target_words(text: str) -> str:
    words = text.split()
    if len(words) <= TARGET_MAX_WORDS:
        return text.strip()

    trimmed = " ".join(words[:TARGET_MAX_WORDS]).strip()
    last_stop = max(trimmed.rfind("."), trimmed.rfind("!"), trimmed.rfind("?"))
    if last_stop > len(trimmed) // 2:
        sentence_trimmed = trimmed[:last_stop + 1].strip()
        if word_count(sentence_trimmed) >= TARGET_MIN_WORDS:
            return sentence_trimmed

    return trimmed.rstrip(",;:") + "."


def enforce_target_word_count(summary: str, source_texts: list[str]) -> str:
    """
    BART controls token length, not exact word length. If generation undershoots,
    add non-duplicate detail sentences from earlier chunk/section summaries.
    """
    summary = trim_to_target_words(summary)
    if word_count(summary) >= TARGET_MIN_WORDS:
        return summary

    existing = split_sentences(summary)
    additions = []
    for source in source_texts:
        for sentence in split_sentences(source):
            sentence_words = word_count(sentence)
            if not 8 <= sentence_words <= 45:
                continue
            if any(word_overlap(sentence, seen) >= 0.50 for seen in existing + additions):
                continue
            if sentence[-1] not in ".!?":
                sentence += "."
            additions.append(sentence)

            candidate = trim_to_target_words(" ".join([summary] + additions))
            if word_count(candidate) >= TARGET_MIN_WORDS:
                print(f"  → Word-count guard adjusted summary to {word_count(candidate)} words")
                return candidate

    final = trim_to_target_words(" ".join([summary] + additions))
    print(f"  → Word-count guard finished at {word_count(final)} words")
    return final


def truncate_to_token_limit(text: str, token_limit: int) -> str:
    encoded = tokenizer.encode(text, add_special_tokens=False)
    if len(encoded) <= token_limit:
        return text
    return tokenizer.decode(
        encoded[:token_limit],
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True,
    )


def generate_summaries(texts: list[str], **generate_kwargs) -> list[dict[str, str]]:
    """Run BART directly through model.generate(), without a HF pipeline."""
    summaries = []
    generation_options = {**GENERATION_KWARGS, **generate_kwargs}

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        inputs = tokenizer(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
            # Text is already capped at 992 non-special tokens above. Keep room
            # for BART's special tokens within its 1024-position encoder limit.
            max_length=TOKENIZER_MAX_LENGTH,
        )
        inputs = {name: tensor.to(MODEL_DEVICE) for name, tensor in inputs.items()}

        with torch.inference_mode():
            output_ids = model.generate(**inputs, **generation_options)

        decoded = tokenizer.batch_decode(
            output_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        summaries.extend({"summary_text": summary.strip()} for summary in decoded)

    return summaries


def safe_summarize(text: str, **generate_kwargs):
    return safe_summarize_batch([text], **generate_kwargs)


def safe_summarize_batch(texts: list[str], **generate_kwargs):
    if not texts:
        return []
    safe_texts = [truncate_to_token_limit(text, SAFE_TOKEN_LIMIT) for text in texts]
    return generate_summaries(safe_texts, **generate_kwargs)


def extract_video_id(url: str) -> str | None:
    """Extract the 11-character YouTube video ID from any URL format."""
    patterns = [
        r"(?:v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_transcript(video_id: str) -> str:
    """
    Fetch transcript using youtube-transcript-api v1.x syntax.
    Includes retry logic for YouTube rate-limiting / blocking.
    """
    max_retries = 3
    wait_seconds = 5

    for attempt in range(max_retries):
        try:
            ytt_api = YouTubeTranscriptApi()
            fetched = ytt_api.fetch(video_id, languages=["en"])
            return " ".join([snippet.text for snippet in fetched])

        except TranscriptsDisabled:
            raise Exception("Transcripts are disabled for this video.")

        except NoTranscriptFound:
            raise Exception("No English transcript found for this video.")

        except Exception as e:
            error_msg = str(e).lower()
            if "no element found" in error_msg or "xml" in error_msg or "blocked" in error_msg:
                if attempt < max_retries - 1:
                    print(f"  → YouTube blocked, retrying in {wait_seconds}s "
                          f"(attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_seconds)
                    continue
                raise Exception(
                    "YouTube kept blocking the request after 3 attempts. "
                    "Try a different video or switch to a different network."
                )
            raise Exception(f"Transcript error: {str(e)}")


def chunk_text(text: str) -> list:
    """Split a transcript using the configured chunk word limit."""
    words = text.split()
    chunks, chunk = [], []

    print(f"  → Transcript word count : {len(words)}")
    print(f"  → Chunk size            : {CHUNK_WORD_LIMIT} words")

    for word in words:
        chunk.append(word)
        if len(chunk) >= CHUNK_WORD_LIMIT:
            chunks.append(" ".join(chunk))
            chunk = []
    if chunk:
        chunks.append(" ".join(chunk))

    print(f"  → Total chunks          : {len(chunks)}")
    return chunks


def expand_summary_to_target(base_summary: str, transcript: str) -> str:
    """
    If the base summary is under TARGET_MIN_WORDS, run additional
    inference passes on different sections of the transcript and
    stitch the outputs together until we reach the 300–400 word target.

    Strategy:
      - Divide the transcript into 3 broad sections (beginning / middle / end)
      - Summarize each section independently
      - Combine: base_summary + section summaries
      - Trim to TARGET_MAX_WORDS
    """
    words = transcript.split()
    total = len(words)

    # Split transcript into 3 broad sections
    third = total // 3
    sections = [
        " ".join(words[:third]),
        " ".join(words[third:2 * third]),
        " ".join(words[2 * third:]),
    ]

    section_labels = ["beginning", "middle", "end"]
    combined_parts = [base_summary]

    print(f"  → Base summary is {len(base_summary.split())} words — "
          f"expanding to {TARGET_MIN_WORDS}–{TARGET_MAX_WORDS} words...")

    section_inputs = []
    active_labels = []
    for label, section in zip(section_labels, sections):
        if section.strip():
            section_inputs.append(" ".join(section.split()[:CHUNK_WORD_LIMIT]))
            active_labels.append(label)

    try:
        results = safe_summarize_batch(
            section_inputs,
            max_length=CHUNK_MAX_OUT,
            min_length=CHUNK_MIN_OUT,
        )
        for label, result in zip(active_labels, results):
            section_summary = result["summary_text"].strip()
            combined_parts.append(section_summary)
            print(f"  → Section ({label}) summarized: {len(section_summary.split())} words")
    except Exception as e:
        print(f"  → Section expansion skipped: {e}")

    full_text = trim_to_target_words(" ".join(combined_parts))

    print(f"  → Final summary word count: {word_count(full_text)} words")
    return full_text


def summarize_text(text: str) -> str:
    """
    Three-stage summarization pipeline targeting 300–400 word output:

    Stage 1 — Chunk pass:
        Transcript → fixed-size word chunks → each summarized by local BART

    Stage 2 — Consolidation pass:
        Chunk summaries joined → re-summarized into one paragraph

    Stage 3 — Expansion pass (if needed):
        If consolidated summary < 300 words, section-level passes
        are added and stitched together to reach the 300–400 word target
    """
    chunks = chunk_text(text)
    # ── Stage 1: chunk summaries ──────────────────────────────────────────────
    print(f"  → Summarizing {len(chunks)} chunks in batches of {BATCH_SIZE}...")
    try:
        results = safe_summarize_batch(
            chunks,
            max_length=CHUNK_MAX_OUT,
            min_length=CHUNK_MIN_OUT,
        )
        summaries = [result["summary_text"] for result in results]
    except Exception as e:
        print("Chunk batch error:", e)
        raise

    # ── Stage 2: consolidation pass ───────────────────────────────────────────
    if len(summaries) > 1:
        print(f"  → Consolidating {len(summaries)} chunk summaries...")
        combined_words = " ".join(summaries).split()
        if len(combined_words) > FINAL_WORD_LIMIT:
            print(f"  → Trimming to {FINAL_WORD_LIMIT} words for consolidation...")
        combined = " ".join(combined_words[:FINAL_WORD_LIMIT])

        try:
            final = safe_summarize(
                combined,
                max_length=FINAL_MAX_OUT,
                min_length=FINAL_MIN_OUT,
            )
            base_summary = final[0]["summary_text"]
        except Exception as e:
            print("Consolidation error:", e)
            if "index out of range" in str(e).lower():
                retry_words = 400
                print(f"  → Retrying consolidation with {retry_words} words instead of {len(combined_words)}...")
                combined = " ".join(combined_words[:retry_words])
                final = safe_summarize(
                    combined,
                    max_length=FINAL_MAX_OUT,
                    min_length=FINAL_MIN_OUT,
                )
                base_summary = final[0]["summary_text"]
            else:
                raise
    else:
        base_summary = summaries[0]

    # ── Stage 3: expand to 300–400 words if needed ───────────────────────────
    if len(base_summary.split()) < TARGET_MIN_WORDS:
        base_summary = expand_summary_to_target(base_summary, text)

    base_summary = enforce_target_word_count(base_summary, summaries + chunks)
    print(f"  → Returned summary word count: {word_count(base_summary)} words")
    return base_summary


def extract_key_points(summary: str, transcript: str) -> list:
    """
    Extract UNIQUE, MEANINGFUL key points — NOT just sentences from the summary.

    Strategy:
      1. Split summary into sentences as a base
      2. Score each sentence by information density:
         - Penalise sentences that are too similar to each other (dedup)
         - Prefer sentences containing numbers, named entities, or action verbs
         - Prefer sentences that are 10–35 words (not too short, not too long)
      3. Return the top 5 most distinct, informative sentences
      4. Fallback: if summary has < 3 sentences, mine extra facts from transcript
    """
    # ── Step 1: split summary into candidate sentences ────────────────────────
    raw = re.split(r"(?<=[.!?])\s+", summary.strip())
    candidates = [s.strip() for s in raw if 15 < len(s.strip().split()) < 50]

    # ── Step 2: score each candidate ─────────────────────────────────────────
    def score(sentence: str) -> float:
        words = sentence.split()
        word_count = len(words)
        s = sentence.lower()

        score = 0.0

        # Prefer sentences in the 12–30 word sweet spot
        if 12 <= word_count <= 30:
            score += 2.0
        elif word_count > 30:
            score += 0.5

        # Reward numbers and statistics
        if re.search(r'\b\d+[\.,]?\d*\b', sentence):
            score += 2.5

        # Reward action verbs (informative sentences)
        action_verbs = [
            "explains", "shows", "demonstrates", "introduces", "describes",
            "reveals", "discusses", "highlights", "presents", "explores",
            "argues", "proves", "suggests", "concludes", "defines",
            "compares", "analyzes", "covers", "examines", "focuses"
        ]
        if any(v in s for v in action_verbs):
            score += 1.5

        # Reward sentences with named concepts (capitalised mid-sentence words)
        caps = re.findall(r'(?<!\. )[A-Z][a-z]{2,}', sentence[5:])
        score += min(len(caps) * 0.5, 2.0)

        # Penalise very generic openers
        generic = ["this", "it is", "there are", "in this", "the video", "the speaker"]
        if any(s.startswith(g) for g in generic):
            score -= 1.0

        return score

    scored = sorted(candidates, key=score, reverse=True)

    # ── Step 3: deduplicate — remove near-duplicate sentences ─────────────────
    def word_overlap(a: str, b: str) -> float:
        wa = set(re.findall(r'\b\w{4,}\b', a.lower()))
        wb = set(re.findall(r'\b\w{4,}\b', b.lower()))
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    unique = []
    for s in scored:
        if all(word_overlap(s, u) < 0.45 for u in unique):
            unique.append(s)
        if len(unique) == 5:
            break

    # ── Step 4: fallback — mine transcript for extra facts if needed ──────────
    if len(unique) < 3:
        print("  → Not enough key points from summary — mining transcript...")
        # Find sentences in transcript with numbers or specific facts
        transcript_sents = re.split(r"(?<=[.!?])\s+", transcript)
        fact_sents = [
            s.strip() for s in transcript_sents
            if re.search(r'\b\d+\b', s) and 10 < len(s.split()) < 40
        ]
        for fs in fact_sents[:5]:
            if all(word_overlap(fs, u) < 0.45 for u in unique):
                unique.append(fs)
            if len(unique) == 5:
                break

    # Final safety: ensure minimum 3 points even if low quality
    if len(unique) < 3 and candidates:
        for c in candidates:
            if c not in unique:
                unique.append(c)
            if len(unique) == 3:
                break

    print(f"  → Key points extracted: {len(unique)}")
    return unique


def get_summary(url: str) -> dict:
    """
    Main pipeline:
    URL → video ID → transcript → summarize (300–400 words) → key points → dict
    """
    print(f"\n📥 Processing URL: {url}")

    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "Invalid YouTube URL. Please check the link and try again."}

    print(f"  → Video ID: {video_id}")

    try:
        print("  → Fetching transcript...")
        transcript = fetch_transcript(video_id)
        print(f"  → Transcript fetched: {len(transcript.split())} words")
    except Exception as e:
        return {"error": str(e)}

    try:
        summary = summarize_text(transcript)
        # Pass transcript to key points so it can mine facts if needed
        key_points = extract_key_points(summary, transcript)
        print("  → Done!\n")
    except Exception as e:
        return {"error": f"Summarization failed: {str(e)}"}

    return {
        "video_id": video_id,
        "transcript_length": len(transcript.split()),
        "summary": summary,
        "key_points": key_points,
    }
