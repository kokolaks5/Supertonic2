"""
EPUB to MP3 converter using Supertonic TTS
Streamlit app with chapter division, language/voice/style selection
"""

import os
import re
import tempfile
import unicodedata
from pathlib import Path

import streamlit as st
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import numpy as np
import soundfile as sf
import subprocess
import asyncio
import edge_tts

# ─────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="EPUB → MP3 · Supertonic",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    min-height: 100vh;
}

section[data-testid="stSidebar"] {
    background: rgba(15, 12, 41, 0.95) !important;
    border-right: 1px solid rgba(255,255,255,0.08);
}

.main-header {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.6rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
}

.sub-header {
    color: rgba(255,255,255,0.55);
    font-size: 1rem;
    margin-bottom: 2rem;
}

.card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
}

.chapter-item {
    background: rgba(102,126,234,0.08);
    border: 1px solid rgba(102,126,234,0.2);
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: all 0.2s ease;
}
.chapter-item:hover {
    background: rgba(102,126,234,0.18);
    border-color: rgba(102,126,234,0.5);
}
.chapter-item.active {
    background: rgba(102,126,234,0.25);
    border-color: #667eea;
}

.badge {
    display: inline-block;
    background: linear-gradient(90deg, #667eea, #764ba2);
    color: white;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 20px;
    margin-left: 8px;
}

.fragment-box {
    background: rgba(0,0,0,0.25);
    border-left: 3px solid #667eea;
    border-radius: 0 8px 8px 0;
    padding: 1.4rem 1.6rem;
    margin-bottom: 0.8rem;
    font-size: 1rem;
    line-height: 1.7;
    color: rgba(255,255,255,0.82);
    font-family: 'Inter', sans-serif;
    white-space: pre-wrap;
    word-break: break-word;
    min-height: 4rem;
}

.stat-box {
    display: inline-block;
    background: rgba(102,126,234,0.15);
    border: 1px solid rgba(102,126,234,0.3);
    border-radius: 8px;
    padding: 0.4rem 0.9rem;
    margin-right: 0.5rem;
    font-size: 0.82rem;
    color: rgba(255,255,255,0.8);
}

.progress-msg {
    color: #a78bfa;
    font-size: 0.9rem;
    margin: 0.3rem 0;
}

stButton > button {
    background: linear-gradient(90deg, #667eea, #764ba2) !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────
MAX_CHARS = 100_000

LANGUAGES = {
    "English": "en", "Korean": "ko", "Japanese": "ja", "Arabic": "ar",
    "Bulgarian": "bg", "Czech": "cs", "Danish": "da", "German": "de",
    "Greek": "el", "Spanish": "es", "Estonian": "et", "Finnish": "fi",
    "French": "fr", "Hindi": "hi", "Croatian": "hr", "Hungarian": "hu",
    "Indonesian": "id", "Italian": "it", "Lithuanian": "lt", "Latvian": "lv",
    "Dutch": "nl", "Polish": "pl", "Portuguese": "pt", "Romanian": "ro",
    "Russian": "ru", "Slovak": "sk", "Slovenian": "sl", "Swedish": "sv",
    "Turkish": "tr", "Ukrainian": "uk", "Vietnamese": "vi",
    "Unknown / Fallback": "na",
}

VOICE_NAMES = ["M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"]

VOICE_DESCRIPTIONS = {
    "M1": "Male · Deep & Calm", "M2": "Male · Warm & Clear",
    "M3": "Male · Energetic", "M4": "Male · Expressive",
    "M5": "Male · Authoritative", "F1": "Female · Soft & Natural",
    "F2": "Female · Clear & Bright", "F3": "Female · Warm",
    "F4": "Female · Lively", "F5": "Female · Professional",
}

MODELS = ["supertonic-3", "supertonic-2", "supertonic"]

# ─────────────────────────────────────────────────────
# Text normalisation helpers
# ─────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Remove/replace characters that interfere with TTS."""
    # Normalise unicode
    text = unicodedata.normalize("NFKC", text)

    # ── All quote variants → nothing / apostrophe ──────────────
    # Double quotes (curly, low-9, guillemets)
    text = text.replace("\u201c", "")   # “ left double
    text = text.replace("\u201d", "")   # ” right double
    text = text.replace("\u201e", "")   # „ low-9 double (German open)
    text = text.replace("\u201f", "")   # ‟ high-rev-9 double
    text = text.replace("\u00ab", "")   # « left guillemet
    text = text.replace("\u00bb", "")   # » right guillemet
    text = text.replace("\u2039", "")   # ‹ single left guillemet
    text = text.replace("\u203a", "")   # › single right guillemet
    # Single quotes (curly, low-9)
    text = text.replace("\u2018", "")   # ‘ left single
    text = text.replace("\u2019", "'")  # ’ right single / apostrophe
    text = text.replace("\u201a", "")   # ‚ low-9 single
    text = text.replace("\u201b", "")   # ‛ high-rev-9 single
    # Plain ASCII double quote
    text = text.replace('"', "")
    # Backtick-style
    text = text.replace("’", "'")

    # ── Dashes ──────────────────────────────────────────────────
    text = re.sub(r"[\u2013\u2014\u2015\u2212]", ", ", text)  # en, em, hor. bar, minus
    text = re.sub(r"\s+-\s+", ", ", text)    # hyphen used as dash

    # ── Ellipsis / misc ─────────────────────────────────────────
    text = text.replace("…", "...")
    text = text.replace("\u00ad", "")   # soft hyphen
    text = text.replace("\u200b", "")   # zero-width space
    text = text.replace("\u200c", "")   # ZWNJ
    text = text.replace("\u200d", "")   # ZWJ
    text = text.replace("\ufeff", "")   # BOM

    # ── Control characters ───────────────────────────────────────
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # ── Collapse whitespace ──────────────────────────────────────
    text = re.sub(r"  +", " ", text)
    return text.strip()


# ─────────────────────────────────────────────────────
# EPUB parsing
# ─────────────────────────────────────────────────────

def extract_epub_chapters(epub_path: str) -> list[dict]:
    """Return list of {title, text} dicts."""
    book = epub.read_epub(epub_path)
    chapters = []

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        # Detect chapter title
        title_tag = soup.find(["h1", "h2", "h3"])
        if title_tag:
            title = title_tag.get_text(strip=True)
        else:
            # Fallback: use filename without path and extension (.xhtml, .html, etc.)
            title = Path(item.get_name()).stem
        raw_text = soup.get_text(separator=" ", strip=True)
        if len(raw_text.strip()) < 80:
            continue  # skip very short items (ToC, cover, etc.)
        chapters.append({"title": title, "raw_text": raw_text})

    return chapters


def split_into_fragments(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Split text into ≤max_chars fragments, cutting at sentence boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    fragments = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_chars:
            current = (current + " " + sent).strip()
        else:
            if current:
                fragments.append(current)
            # If a single sentence exceeds limit, hard-split
            while len(sent) > max_chars:
                fragments.append(sent[:max_chars])
                sent = sent[max_chars:]
            current = sent
    if current:
        fragments.append(current)
    return fragments


# ─────────────────────────────────────────────────────
# TTS helpers (lazy-load)
# ─────────────────────────────────────────────────────

def run_async(coro):
    import asyncio
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()


@st.cache_data(show_spinner="Loading Edge TTS voices…")
def get_edge_voices():
    async def _get():
        return await edge_tts.list_voices()
    try:
        voices = run_async(_get())
        voices = sorted(voices, key=lambda x: (x.get("Locale", ""), x.get("ShortName", "")))
        return voices
    except Exception as e:
        st.error(f"Error fetching Edge TTS voices: {e}")
        return []


def mp3_bytes_to_wav_array(mp3_bytes: bytes) -> tuple[np.ndarray, int]:
    """Convert MP3 bytes to float32 numpy array and sample rate using ffmpeg."""
    process = subprocess.Popen(
        ["ffmpeg", "-y", "-i", "pipe:0", "-f", "wav", "pipe:1"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout_data, stderr_data = process.communicate(input=mp3_bytes)
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg error during decode: {stderr_data.decode()}")
    
    import io
    wav_io = io.BytesIO(stdout_data)
    data, sample_rate = sf.read(wav_io)
    return data, sample_rate


def synthesize_edge_tts_fragment_sync(text: str, voice: str, rate: str, volume: str, pitch: str) -> tuple[np.ndarray, int]:
    async def _synth():
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            await communicate.save(tmp_path)
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
                
    mp3_bytes = run_async(_synth())
    return mp3_bytes_to_wav_array(mp3_bytes)


@st.cache_resource(show_spinner="Loading Supertonic model…")
def get_tts(model_name: str):
    from supertonic import TTS
    return TTS(model=model_name, auto_download=True)


def synthesize_fragment(tts, text: str, voice_name: str, lang: str) -> np.ndarray:
    style = tts.get_voice_style(voice_name)
    # Safety net: if Supertonic rejects chars, strip them and retry once
    for attempt in range(2):
        try:
            wav, duration = tts.synthesize(text, voice_style=style, lang=lang)
            break
        except ValueError as e:
            if attempt == 0 and "unsupported character" in str(e).lower():
                import re as _re
                # Extract the bad chars from the error message list
                bad = _re.findall(r"'([^']+)'", str(e))
                for ch in bad:
                    text = text.replace(ch, "")
                text = text.strip() or "."
            else:
                raise
    # Trim to actual duration
    samples = int(tts.sample_rate * float(duration[0]))
    if wav.ndim == 2:
        wav = wav.squeeze(0)
    return wav[:samples]


def wav_to_mp3_bytes(wav_data: np.ndarray, sample_rate: int, bitrate: str = "128k") -> bytes:
    """Convert numpy wav array → MP3 bytes via ffmpeg using temp files."""
    # Supertonic may return shape [1, T] – flatten to 1-D
    if wav_data.ndim == 2:
        wav_data = wav_data.squeeze(0)
    # Ensure float32 in [-1, 1]
    wav_data = np.clip(wav_data.astype(np.float32), -1.0, 1.0)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_tmp:
        wav_path = wav_tmp.name
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_tmp:
        mp3_path = mp3_tmp.name
    try:
        sf.write(wav_path, wav_data, sample_rate, subtype="PCM_16")
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path,
             "-codec:a", "libmp3lame", "-b:a", bitrate, mp3_path],
            capture_output=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg error: {result.stderr.decode()}")
        with open(mp3_path, "rb") as f:
            return f.read()
    finally:
        for p in (wav_path, mp3_path):
            try:
                os.unlink(p)
            except OSError:
                pass

def make_filename(chapter_idx: int, title: str) -> str:
    """Build a safe MP3 filename like 001_Chapter_Title.mp3"""
    # Keep letters, digits, spaces, hyphens (works for unicode too)
    safe = re.sub(r"[^\w\s\-]", "", title, flags=re.UNICODE)
    safe = safe.strip().replace(" ", "_")
    # Collapse multiple underscores
    safe = re.sub(r"_+", "_", safe)
    # Fallback if title was all special chars
    if not safe:
        safe = f"chapter_{chapter_idx + 1}"
    return f"{chapter_idx + 1:03d}_{safe[:60]}.mp3"

# ─────────────────────────────────────────────────────
for k, v in [
    ("chapters", []),
    ("selected_chapter", 0),
    ("epub_name", ""),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────
# Sidebar – settings
# ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")

    engine_choice = st.selectbox(
        "TTS Engine", ["Supertonic TTS", "Microsoft Edge TTS"],
        help="Supertonic TTS runs locally. Microsoft Edge TTS runs in the cloud (no API key required)."
    )

    lang_label = st.selectbox("Language", list(LANGUAGES.keys()), index=0)
    lang_code = LANGUAGES[lang_label]

    if engine_choice == "Supertonic TTS":
        model_choice = st.selectbox(
            "Model", MODELS,
            help="supertonic-3 = 31 languages | supertonic-2 = 5 languages | supertonic = English only"
        )

        voice_choice = st.selectbox(
            "Voice",
            VOICE_NAMES,
            format_func=lambda v: f"{v} — {VOICE_DESCRIPTIONS[v]}"
        )
    else:
        # Microsoft Edge TTS Settings
        edge_voices = get_edge_voices()
        if lang_code != "na":
            filtered_voices = [v for v in edge_voices if v.get("Locale", "").startswith(lang_code)]
        else:
            filtered_voices = edge_voices

        if not filtered_voices:
            filtered_voices = edge_voices

        voice_options = [v["ShortName"] for v in filtered_voices]
        voice_labels = {v["ShortName"]: f"{v['ShortName']} ({v.get('Gender', 'Unknown')})" for v in filtered_voices}

        voice_choice = st.selectbox(
            "Voice",
            options=voice_options,
            format_func=lambda x: voice_labels.get(x, x),
            index=0 if voice_options else None
        )

        rate_pct = st.slider("Speech Rate / Speed", min_value=-50, max_value=100, value=0, step=5, format="%d%%")
        rate_str = f"{rate_pct:+d}%"

        volume_pct = st.slider("Speech Volume", min_value=-50, max_value=50, value=0, step=5, format="%d%%")
        volume_str = f"{volume_pct:+d}%"

        pitch_hz = st.slider("Speech Pitch", min_value=-50, max_value=50, value=0, step=5, format="%d Hz")
        pitch_str = f"{pitch_hz:+d}Hz"

    bitrate = st.select_slider(
        "MP3 Bitrate", options=["64k", "96k", "128k", "192k", "256k", "320k"],
        value="128k"
    )

    st.markdown("---")
    st.markdown("### 📂 EPUB File")
    uploaded = st.file_uploader("Upload EPUB", type=["epub"])

    st.markdown("---")
    st.markdown("### ▶️ Continue from Chapter")
    start_chapter = st.number_input(
        "Start from chapter #", min_value=1, value=1, step=1,
        help="1 = start from the beginning"
    )

    st.markdown("---")
    st.caption("Powered by [Supertonic](https://github.com/supertone-inc/supertonic) & [Edge-TTS](https://github.com/rany2/edge-tts)")

# ─────────────────────────────────────────────────────
# Main area
# ─────────────────────────────────────────────────────
st.markdown('<div class="main-header">🎧 EPUB → MP3</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Convert any EPUB audiobook with Supertonic TTS · 128k · chapter-aware</div>', unsafe_allow_html=True)

if uploaded:
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp:
        tmp.write(uploaded.read())
        epub_path = tmp.name

    if st.session_state.epub_name != uploaded.name:
        with st.spinner("Parsing EPUB…"):
            raw_chapters = extract_epub_chapters(epub_path)
        st.session_state.chapters = raw_chapters
        st.session_state.epub_name = uploaded.name
        st.session_state.selected_chapter = 0

    chapters = st.session_state.chapters

    if not chapters:
        st.error("No readable chapters found in this EPUB.")
    else:
        col_left, col_right = st.columns([1, 2], gap="large")

        # ── Left: chapter list ──────────────────────────────
        with col_left:
            st.markdown(f'<div class="card"><b>📖 {uploaded.name}</b><br>'
                        f'<span class="stat-box">{len(chapters)} chapters</span></div>',
                        unsafe_allow_html=True)

            st.markdown("**Chapters** *(click to preview)*")
            for i, ch in enumerate(chapters):
                word_count = len(ch["raw_text"].split())
                active_cls = "active" if i == st.session_state.selected_chapter else ""
                label = f"{'✅' if i + 1 < start_chapter else '▶' if i + 1 == start_chapter else '○'} {i+1}. {ch['title'][:45]}"
                if st.button(label, key=f"ch_{i}", use_container_width=True):
                    st.session_state.selected_chapter = i

        # ── Right: preview + convert ────────────────────────
        with col_right:
            idx = st.session_state.selected_chapter
            ch = chapters[idx]
            clean = clean_text(ch["raw_text"])
            fragments = split_into_fragments(clean)

            st.markdown(f"### Chapter {idx+1}: {ch['title']}")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Characters (clean)", f"{len(clean):,}")
            col_b.metric("Fragments", len(fragments))
            col_c.metric("Words", f"{len(clean.split()):,}")

            with st.expander(f"📄 Preview fragments ({len(fragments)})", expanded=True):
                for fi, frag in enumerate(fragments):
                    st.markdown(
                        f'<div class="fragment-box">'
                        f'<b style="color:#a78bfa">Fragment {fi+1} · {len(frag):,} chars</b><br><br>'
                        f'{frag[:1600]}{"…" if len(frag) > 1600 else ""}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        st.divider()

        # ── Conversion controls ─────────────────────────────
        st.markdown("## 🎙️ Convert to MP3")

        conv_col1, conv_col2 = st.columns(2)
        with conv_col1:
            convert_single = st.button(
                f"🎧 Convert Chapter {idx+1} only",
                use_container_width=True,
                type="primary",
            )
        with conv_col2:
            convert_all = st.button(
                f"🚀 Convert ALL chapters (from #{start_chapter})",
                use_container_width=True,
            )

        # ── Single chapter conversion ───────────────────────
        if convert_single:
            if engine_choice == "Supertonic TTS":
                tts = get_tts(model_choice)
            st.markdown(f"**Converting chapter {idx+1}: {ch['title']}**")
            progress = st.progress(0.0)
            status = st.empty()
            all_wav = []
            sample_rate = 24000  # Default fallback

            for fi, frag in enumerate(fragments):
                status.markdown(f'<div class="progress-msg">Fragment {fi+1}/{len(fragments)}…</div>',
                                unsafe_allow_html=True)
                if engine_choice == "Supertonic TTS":
                    wav = synthesize_fragment(tts, frag, voice_choice, lang_code)
                    sample_rate = tts.sample_rate
                else:
                    wav, sample_rate = synthesize_edge_tts_fragment_sync(
                        frag, voice_choice, rate_str, volume_str, pitch_str
                    )
                all_wav.append(wav)
                progress.progress((fi + 1) / len(fragments))

            combined = np.concatenate(all_wav)
            mp3_bytes = wav_to_mp3_bytes(combined, sample_rate, bitrate)
            file_name = make_filename(idx, ch["title"])
            st.success(f"✅ Done! Chapter {idx+1} converted.")
            st.download_button(
                f"⬇️ Download {file_name}",
                data=mp3_bytes,
                file_name=file_name,
                mime="audio/mpeg",
                use_container_width=True,
            )

        # ── All chapters conversion ─────────────────────────
        if convert_all:
            if engine_choice == "Supertonic TTS":
                tts = get_tts(model_choice)
            chapters_to_convert = chapters[start_chapter - 1:]
            overall = st.progress(0.0)
            chapter_status = st.empty()
            downloads = []

            for ci, ch_item in enumerate(chapters_to_convert):
                real_idx = ci + start_chapter - 1
                chapter_status.markdown(
                    f'<div class="progress-msg">Chapter {real_idx+1}/{len(chapters)}: {ch_item["title"]}</div>',
                    unsafe_allow_html=True
                )
                clean_ch = clean_text(ch_item["raw_text"])
                frags = split_into_fragments(clean_ch)
                frag_progress = st.progress(0.0)
                all_wav = []
                sample_rate = 24000  # Fallback

                for fi, frag in enumerate(frags):
                    if engine_choice == "Supertonic TTS":
                        wav = synthesize_fragment(tts, frag, voice_choice, lang_code)
                        sample_rate = tts.sample_rate
                    else:
                        wav, sample_rate = synthesize_edge_tts_fragment_sync(
                            frag, voice_choice, rate_str, volume_str, pitch_str
                        )
                    all_wav.append(wav)
                    frag_progress.progress((fi + 1) / len(frags))

                combined = np.concatenate(all_wav)
                mp3_bytes = wav_to_mp3_bytes(combined, sample_rate, bitrate)
                file_name = make_filename(real_idx, ch_item["title"])
                downloads.append((file_name, mp3_bytes))
                overall.progress((ci + 1) / len(chapters_to_convert))

            st.success(f"✅ All {len(downloads)} chapters converted!")
            st.markdown("### ⬇️ Downloads")
            for file_name, mp3_bytes in downloads:
                st.download_button(
                    label=file_name,
                    data=mp3_bytes,
                    file_name=file_name,
                    mime="audio/mpeg",
                    key=f"dl_{file_name}",
                    use_container_width=True,
                )

else:
    # Landing state
    st.markdown("""
    <div class="card" style="text-align:center; padding: 3rem;">
        <div style="font-size:4rem; margin-bottom:1rem;">📚</div>
        <div style="font-size:1.3rem; font-weight:600; color:rgba(255,255,255,0.9);">
            Upload an EPUB file to get started
        </div>
        <div style="color:rgba(255,255,255,0.4); margin-top:0.5rem;">
            Select your language, voice, and bitrate in the sidebar, then upload your book.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Features")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""<div class="card">
        <b>📖 Smart Chapter Splitting</b><br><br>
        Splits at sentence boundaries, never mid-word.
        Handles chapters larger than 100,000 characters automatically.
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class="card">
        <b>🌍 31 Languages</b><br><br>
        Full multilingual support via Supertonic-3.
        Select any language and voice style (M1–M5, F1–F5).
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""<div class="card">
        <b>🔢 Text Normalisation</b><br><br>
        Removes problematic punctuation, and cleans smart quotes and dashes.
        </div>""", unsafe_allow_html=True)
