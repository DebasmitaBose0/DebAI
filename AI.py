import streamlit as st
from fpdf import FPDF
import os
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import pdfplumber
import importlib
import importlib.util
import requests
from langdetect import detect, DetectorFactory

# make language detection deterministic
DetectorFactory.seed = 0

# ================== OPTIONAL MODEL CLIENTS ==================
def check_ollama():
    """Check if Ollama is running on localhost:11434"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        return response.status_code == 200
    except:
        return False

try:
    # Import dynamically to avoid static import resolution errors in editors/linters
    ollama = importlib.import_module("ollama")
    # Try to verify Ollama is actually running
    OLLAMA_AVAILABLE = check_ollama()
except Exception:
    ollama = None
    OLLAMA_AVAILABLE = False

# ------------------ CONFIG ------------------
MODEL = "gemma3:1b"

# ------------------ OCR READER ------------------
@st.cache_resource

def get_ocr_reader(langs=None):
    """Return an OCR reader instance.

    ``langs`` should be a list of language codes (e.g. ['en'] or ['bn','as','en']).
    Default is English only to prevent misclassification when images contain
    only Latin text.  The sidebar allows the user to override this selection.

    Falls back to pytesseract or a dummy reader if easyocr isn't available.
    """
    if langs is None:
        langs = ['en']

    # Try to import easyocr dynamically
    try:
        easyocr = importlib.import_module("easyocr")
    except Exception:
        easyocr = None

    if easyocr:
        import sys, contextlib
        with contextlib.redirect_stdout(sys.stdout if False else open(os.devnull, 'w')):
            with contextlib.redirect_stderr(sys.stderr if False else open(os.devnull, 'w')):
                try:
                    return easyocr.Reader(langs, gpu=False, verbose=False)
                except Exception:
                    easyocr = None

    # Fallback: try to use pytesseract if available
    try:
        pytesseract = importlib.import_module("pytesseract")

        class PTReader:
            def __init__(self, langs):
                self.langs = langs

            def readtext(self, img_array, detail=1):
                from PIL import Image
                img = Image.fromarray(img_array.astype("uint8"))
                try:
                    # Use pytesseract to extract text; return in easyocr-like format
                    txt = pytesseract.image_to_string(img, lang='eng')
                except Exception:
                    txt = pytesseract.image_to_string(img)
                lines = [l.strip() for l in txt.splitlines() if l.strip()]
                return [[None, l, 0.5] for l in lines]

        return PTReader(['en'])

    except Exception:
        # Final fallback: dummy reader that returns no detections
        class DummyReader:
            def __init__(self, langs):
                self.langs = langs

            def readtext(self, img_array, detail=1):
                return []

        return DummyReader(['en'])

# ------------------ IMAGE PREPROCESSING ------------------
def preprocess_image(image):
    """
    Advanced preprocessing for 100% accurate OCR
    """
    try:
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image.astype("uint8"))

        # Convert to grayscale
        image = image.convert("L")

        # Strong contrast enhancement
        image = ImageEnhance.Contrast(image).enhance(2.0)

        # Sharpen for text clarity
        image = image.filter(ImageFilter.SHARPEN)
        image = image.filter(ImageFilter.SHARPEN)

        # Brightness adjustment
        image = ImageEnhance.Brightness(image).enhance(1.1)

        return image

    except Exception as e:
        return image

# ------------------ OCR FUNCTION ------------------
def perform_ocr(image):
    """
    High-accuracy multilingual OCR with optional automatic language detection.

    The first pass always uses English; the result is passed through a
    language detector.  If a non-English language is detected the image is
    re-read using that language model.  The detected language is stored in
    `st.session_state.detected_lang` for UI reporting/override.
    """
    try:
        processed = preprocess_image(image)
        img_array = np.array(processed)

        # first pass: always start with English to avoid mis-classification
        reader = get_ocr_reader(['en'])
        results = reader.readtext(img_array, detail=1)

        extracted = []
        if results:
            for detection in results:
                text = detection[1].strip()
                conf = detection[2]
                if text and conf > 0.05:
                    extracted.append(text)

        text = "\n".join(extracted) if extracted else ""

        # language detection on preliminary text
        try:
            lang = detect(text) if text.strip() else 'en'
        except Exception:
            lang = 'en'
        st.session_state.detected_lang = lang

        # if detected language differs, rerun OCR with that model
        if lang != 'en':
            reader = get_ocr_reader([lang])
            results = reader.readtext(img_array, detail=1)
            extracted = []
            if results:
                for detection in results:
                    t = detection[1].strip()
                    c = detection[2]
                    if t and c > 0.05:
                        extracted.append(t)
            text = "\n".join(extracted) if extracted else text

        # fallback message if nothing found
        if not text:
            return "No readable text found in image"
        return text

        if extracted:
            # if OCR returned many single characters (vertical output),
            # join into a single string instead of line breaks
            if all(len(x) == 1 for x in extracted) and len(extracted) > 1:
                return "".join(extracted)
            return "\n".join(extracted)

        return "No readable text found in image"

    except Exception as e:
        return f"OCR Error: {str(e)}"

# ------------------ PDF EXPORT ------------------
def create_pdf(messages):
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 14)
            self.cell(0, 10, "DebAI Session Report", ln=True, align="C")
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", align="C")

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)

    for msg in messages:
        if msg["role"] == "system":
            continue

        role = msg["role"].upper()
        content = msg["content"].encode("latin-1", "replace").decode("latin-1")

        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"{role}:", ln=True)

        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 8, content)
        pdf.ln(3)

    return pdf.output(dest="S").encode("latin-1")

# pre-warm OCR reader outside of upload flow to prevent cache message
# being displayed next to images during user interaction
with st.spinner("Loading OCR engine..."):
    _ = get_ocr_reader(st.session_state.get('ocr_langs'))

# ------------------ PAGE CONFIG ------------------
# simple SVG favicon — no external files required.
st.set_page_config(
    page_title="DebAI",
    page_icon="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' fill='%2300d4aa'/><text x='50%' y='50%' font-size='36' font-family='Inter' fill='%23ffffff' text-anchor='middle' alignment-baseline='middle'>D</text></svg>",
    layout="wide"
)

# ------------------ SESSION STATE ------------------
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "system",
        "content": (
            "You are DebAI, a multilingual AI assistant. "
            "You MUST respond in the same language as the user: "
            "If user writes in English → respond in English. "
            "If user writes in Hindi → respond in Hindi (Devanagari script). "
            "If user writes in Bengali → respond in Bengali (Bangla script). "
            "Do not translate or mix languages. Respond ONLY in the detected language. "
            "Use only native script; do NOT include romanized or phonetic transliteration of Bengali or Hindi. "
            "If you are replying in Bengali, append a plain English translation on a new line beneath your Bengali answer, without using parentheses, brackets, or any transliteration."
        )
    }]

if "is_generating" not in st.session_state:
    st.session_state.is_generating = False

if "last_ocr" not in st.session_state:
    st.session_state.last_ocr = ""

# ------------------ CUSTOM THEME CSS ------------------
theme_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

* {
    font-family: 'Inter', sans-serif;
}

/* Professional color palette */
:root {
    --primary: #00d4aa;
    --primary-dark: #00b894;
    --secondary: #0984e3;
    --accent: #fdcb6e;
    --background: #0a0a0a;
    --surface: #1a1a1a;
    --surface-hover: #2a2a2a;
    --text-primary: #ffffff;
    --text-secondary: #b0b0b0;
    --text-muted: #808080;
    --border: #333333;
    --border-light: #404040;
    --success: #00b894;
    --warning: #fdcb6e;
    --error: #e17055;
}

/* Background with subtle pattern */
body, .stApp {
    background: 
        radial-gradient(circle at 20% 80%, rgba(0, 212, 170, 0.1) 0%, transparent 50%),
        radial-gradient(circle at 80% 20%, rgba(9, 132, 227, 0.1) 0%, transparent 50%),
        linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0f0f0f 100%);
    background-attachment: fixed;
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
}

/* Main container */
.stApp {
    background-color: rgba(10, 10, 10, 0.95);
    backdrop-filter: blur(20px);
}

/* Professional chat messages */
.stChatMessage {
    background: var(--surface) !important;
    backdrop-filter: blur(20px) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    box-shadow: 
        0 4px 20px rgba(0, 0, 0, 0.3),
        0 0 0 1px rgba(255, 255, 255, 0.05) !important;
    margin: 8px 0 !important;
    padding: 16px 20px !important;
    position: relative !important;
    animation: messageSlideIn 0.4s ease-out;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.stChatMessage:hover {
    transform: translateY(-2px) !important;
    box-shadow: 
        0 8px 30px rgba(0, 0, 0, 0.4),
        0 0 0 1px rgba(255, 255, 255, 0.1),
        0 0 20px rgba(0, 212, 170, 0.1) !important;
    border-color: var(--border-light) !important;
}

@keyframes messageSlideIn {
    from {
        opacity: 0;
        transform: translateY(20px) scale(0.95);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

/* User message styling - right aligned */
.stChatMessage[data-testid="stChatMessage-user"] {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
    border: 1px solid rgba(0, 212, 170, 0.3) !important;
    margin-left: 20% !important;
    margin-right: 0 !important;
    border-radius: 16px 4px 16px 16px !important;
    position: relative !important;
}

.stChatMessage[data-testid="stChatMessage-user"]::before {
    content: "👤";
    position: absolute;
    top: -8px;
    right: 16px;
    background: var(--primary);
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    border: 2px solid var(--background);
}

/* Assistant message styling - left aligned */
.stChatMessage[data-testid="stChatMessage-assistant"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    margin-right: 20% !important;
    margin-left: 0 !important;
    border-radius: 4px 16px 16px 16px !important;
    position: relative !important;
}

.stChatMessage[data-testid="stChatMessage-assistant"]::before {
    content: "🤖";
    position: absolute;
    top: -8px;
    left: 16px;
    background: var(--secondary);
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    border: 2px solid var(--background);
}

/* Message content styling */
.stChatMessage p {
    margin: 0 !important;
    line-height: 1.6 !important;
    font-size: 15px !important;
    color: var(--text-primary) !important;
}

.stChatMessage[data-testid="stChatMessage-user"] p {
    color: white !important;
}

/* Professional buttons */
.stButton > button {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 28px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    letter-spacing: 0.5px !important;
    backdrop-filter: blur(10px) !important;
    box-shadow: 0 4px 16px rgba(0, 212, 170, 0.3) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    text-transform: uppercase !important;
    position: relative !important;
    overflow: hidden !important;
}

.stButton > button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s;
}

.stButton > button:hover::before {
    left: 100%;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(0, 212, 170, 0.4) !important;
}

.stDownloadButton > button {
    background: linear-gradient(135deg, var(--secondary) 0%, #0b6bcb 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 28px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
}

/* Professional input fields */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--surface) !important;
    color: var(--text-primary) !important;
    border: 2px solid var(--border) !important;
    border-radius: 12px !important;
    backdrop-filter: blur(10px) !important;
    padding: 16px 20px !important;
    font-size: 15px !important;
    line-height: 1.5 !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 
        0 0 0 3px rgba(0, 212, 170, 0.1),
        0 4px 16px rgba(0, 0, 0, 0.3) !important;
    outline: none !important;
}

/* Chat input specific styling */
.stChatInput {
    background: var(--surface) !important;
    border: 2px solid var(--border) !important;
    border-radius: 24px !important;
    padding: 4px !important;
}

.stChatInput > div > div > input {
    background: transparent !important;
    border: none !important;
    border-radius: 20px !important;
    padding: 12px 20px !important;
    font-size: 16px !important;
}

.stChatInput > div > div > input:focus {
    box-shadow: none !important;
}

/* Professional expander */
.stExpander {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(20px) !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    overflow: hidden !important;
}

.stExpander:hover {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3) !important;
    border-color: var(--border-light) !important;
}

.stExpander > div > div > button {
    color: var(--primary) !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    padding: 16px 20px !important;
    background: transparent !important;
    border: none !important;
    width: 100% !important;
    text-align: left !important;
    transition: all 0.3s ease !important;
}

.stExpander > div > div > button:hover {
    background: rgba(0, 212, 170, 0.05) !important;
}

/* Professional sidebar */
section[data-testid='stSidebar'] {
    background: var(--surface) !important;
    backdrop-filter: blur(20px) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: 2px 0 16px rgba(0, 0, 0, 0.2) !important;
}

section[data-testid='stSidebar'] > div {
    background: transparent !important;
}

/* Professional headings */
h1, h2, h3 {
    color: var(--primary) !important;
    font-weight: 700 !important;
    text-shadow: 0 0 20px rgba(0, 212, 170, 0.3) !important;
    margin-bottom: 16px !important;
}

h1 {
    font-size: 2.5rem !important;
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

/* Professional text */
p, span, label {
    color: var(--text-primary) !important;
    line-height: 1.6 !important;
}

/* Professional checkbox */
.stCheckbox > label {
    color: var(--text-primary) !important;
    font-weight: 500 !important;
}

.stCheckbox > div > div > input[type="checkbox"] {
    accent-color: var(--primary) !important;
    width: 18px !important;
    height: 18px !important;
}

/* Professional tabs */
.stTabs > div > div[role="tablist"] {
    background: var(--surface) !important;
    border-bottom: 2px solid var(--border) !important;
    border-radius: 12px 12px 0 0 !important;
    padding: 8px !important;
    gap: 4px !important;
}

.stTabs > div > div[role="tablist"] > button {
    color: var(--text-secondary) !important;
    border: none !important;
    background: transparent !important;
    border-radius: 8px !important;
    padding: 12px 20px !important;
    font-weight: 500 !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative !important;
}

.stTabs > div > div[role="tablist"] > button[aria-selected="true"] {
    background: rgba(0, 212, 170, 0.1) !important;
    color: var(--primary) !important;
    font-weight: 600 !important;
}

.stTabs > div > div[role="tablist"] > button[aria-selected="true"]::after {
    content: '';
    position: absolute;
    bottom: -2px;
    left: 50%;
    transform: translateX(-50%);
    width: 20px;
    height: 2px;
    background: var(--primary);
    border-radius: 1px;
}

.stTabs > div > div[role="tablist"] > button:hover {
    background: rgba(0, 212, 170, 0.05) !important;
    color: var(--text-primary) !important;
}

/* Professional status messages */
.stSuccess {
    background: rgba(0, 184, 148, 0.1) !important;
    border: 1px solid var(--success) !important;
    border-radius: 12px !important;
    color: var(--success) !important;
    padding: 12px 16px !important;
}

.stWarning {
    background: rgba(252, 203, 110, 0.1) !important;
    border: 1px solid var(--warning) !important;
    border-radius: 12px !important;
    color: var(--warning) !important;
    padding: 12px 16px !important;
}

/* Professional file uploader */
[data-testid='stFileUploader'] {
    background: var(--surface) !important;
    border: 2px dashed var(--border-light) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(10px) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    padding: 32px !important;
    text-align: center !important;
}

[data-testid='stFileUploader']:hover {
    border-color: var(--primary) !important;
    background: rgba(0, 212, 170, 0.02) !important;
    box-shadow: 0 0 20px rgba(0, 212, 170, 0.1) !important;
}

[data-testid='stFileUploader'] > button {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
    color: white !important;
    margin-top: 16px !important;
}

/* Professional scrollbar */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: var(--surface);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb {
    background: var(--border-light);
    border-radius: 4px;
    transition: background 0.3s ease;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--primary);
}

/* Professional spinner */
.stSpinner > div {
    border-color: rgba(0, 212, 170, 0.3) !important;
    border-top-color: var(--primary) !important;
    width: 24px !important;
    height: 24px !important;
}

/* Typing indicator */
@keyframes typing {
    0%, 60%, 100% {
        transform: translateY(0);
    }
    30% {
        transform: translateY(-10px);
    }
}

.typing-indicator {
    display: inline-flex;
    gap: 4px;
    align-items: center;
}

.typing-indicator span {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--primary);
    animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
    animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
    animation-delay: 0.4s;
}

/* Code blocks */
code {
    background: rgba(0, 0, 0, 0.3) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    padding: 2px 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 14px !important;
}

pre code {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 16px !important;
    display: block !important;
    overflow-x: auto !important;
}

/* Professional metrics/cards */
.stMetric {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 20px !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2) !important;
}

.stMetric > div > div > div {
    color: var(--primary) !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
}

.stMetric > div > div > div:nth-child(2) {
    color: var(--text-secondary) !important;
    font-size: 0.9rem !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}

/* Responsive design */
@media (max-width: 768px) {
    .stChatMessage[data-testid="stChatMessage-user"],
    .stChatMessage[data-testid="stChatMessage-assistant"] {
        margin-left: 8px !important;
        margin-right: 8px !important;
    }
    
    h1 {
        font-size: 2rem !important;
    }
}

</style>
"""

st.markdown(theme_css, unsafe_allow_html=True)

# ------------------ SIDEBAR ------------------
with st.sidebar:
    st.markdown("### ⚙️ DebAI Control Panel")
    st.markdown(f"**Model:** `{MODEL}`")
    st.markdown("**Features:** 🌍 Multilingual OCR + Chat")
    st.markdown("---")

    # allow user to choose OCR languages (default english)
    ocr_lang = st.selectbox("OCR language", ["en", "bn", "as", "en+bn+as"], index=0)
    # translate choice into easyocr style list
    if ocr_lang == "en+bn+as":
        st.session_state.ocr_langs = ['bn','as','en']
    else:
        st.session_state.ocr_langs = [ocr_lang]

    # chat language preference: auto means detect per message
    chat_pref = st.selectbox("Chat language", ["auto", "en", "bn", "hi"], index=0)
    st.session_state.chat_pref = chat_pref

    auto_send = st.checkbox("Auto-send OCR to model", value=True)
    st.session_state.auto_send = auto_send

    if st.session_state.messages:
        pdf_data = create_pdf(st.session_state.messages)
        st.download_button(
            "📄 Download Chat PDF",
            pdf_data,
            "debai_report.pdf",
            "application/pdf"
        )

# ------------------ HEADER ------------------
st.markdown("## 🤖 DebAI — Intelligent Multilingual OCR & Chat Assistant")
st.markdown("Extract text from images & PDFs in 80+ languages and chat intelligently.")

# ------------------ OCR SECTION ------------------
with st.expander("📂 Upload Documents", expanded=True):
    tab1, tab2 = st.tabs(["🖼 Image OCR", "📄 PDF OCR"])

    # -------- IMAGE OCR --------
    with tab1:
        img = st.file_uploader("Upload image", type=["png", "jpg", "jpeg"])
        if img:
            image = Image.open(img)
            st.image(image, width='stretch')

            text = perform_ocr(image)
            if text and text != "No readable text found in image":
                detected = st.session_state.get('detected_lang', 'en')
                st.success(f"OCR completed (detected language: {detected})")
                # display in textarea for readability
                st.text_area("Extracted text", text, height=200)
            else:
                st.warning("No readable text found in image")

            st.session_state.messages.append({"role": "user", "content": text})
            st.session_state.last_ocr = text

            if st.session_state.auto_send:
                st.session_state.is_generating = True

    # -------- PDF OCR --------
    with tab2:
        pdf = st.file_uploader("Upload PDF", type=["pdf"])
        if pdf:
            combined_text = ""
            # reset language detection for multi-page PDF
            st.session_state.detected_lang = 'en'

            with pdfplumber.open(pdf) as pdf_file:
                for page in pdf_file.pages:
                    text = page.extract_text()

                    if text:
                        combined_text += text + "\n"
                    else:
                        try:
                            img = page.to_image(resolution=400)
                            pil_img = img.original.convert("RGB")
                            ocr_text = perform_ocr(pil_img)
                            combined_text += ocr_text + "\n"
                        except:
                            pass

            st.success("PDF processed")
            if combined_text and combined_text.strip():
                detected = st.session_state.get('detected_lang', 'en')
                st.success(f"PDF processed (detected language: {detected})")
                st.text_area("Extracted text", combined_text, height=200)
            else:
                st.warning("No readable text found in PDF")

            st.session_state.messages.append({"role": "user", "content": combined_text})
            st.session_state.last_ocr = combined_text

            if st.session_state.auto_send:
                st.session_state.is_generating = True

# ------------------ CHAT HISTORY ------------------
for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ------------------ CHAT INPUT ------------------
prompt = st.chat_input("Type your message…")
if prompt:
    # always run detection first (auto-detect the user's language)
    try:
        detected = detect(prompt)
    except Exception:
        detected = "en"
    # normalization + simple romanization heuristics
    if detected == "en":
        # check for common romanized Bengali words
        bengali_tokens = ["ami","tomar","khobor","bhalo","kemon","achi","achho","apni","dhonnobad","ki","kintu","tumi"]
        hindi_tokens = ["hai","kaise","kya","hain","aap","kamaal","dhanyavaad"]
        lower = prompt.lower()
        if any(tok in lower for tok in bengali_tokens):
            detected = "bn"
        elif any(tok in lower for tok in hindi_tokens):
            detected = "hi"
    # normalize to supported list
    if detected not in ("en","bn","hi"):
        detected = "en"
    # allow manual override if user picked a non-auto preference
    if st.session_state.chat_pref != "auto":
        override = st.session_state.chat_pref
        if override in ("en","bn","hi"):
            detected = override
    st.session_state.chat_lang = detected

    # update system prompt to include current chat language
    base = (
        "You are DebAI, a multilingual AI assistant. "
        "You MUST respond in the same language as the user: "
        "If user writes in English → respond in English. "
        "If user writes in Hindi → respond in Hindi (Devanagari script). "
        "If user writes in Bengali → respond in Bengali (Bangla script). "
        "Do not translate or mix languages. Respond ONLY in the detected language."
    )
    lang_name = {"en":"English","bn":"Bengali","hi":"Hindi"}.get(detected, "English")
    st.session_state.messages[0]["content"] = base + f" Current chat language: {lang_name}."

    # Display user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.is_generating = True
    st.rerun()

# ------------------ RESPONSE GENERATION ------------------
def generate_response():
    user_msg = st.session_state.messages[-1]["content"]

    if not OLLAMA_AVAILABLE:
        yield "⚠️ **Chat unavailable**: Ollama is not running.\n\nTo enable chat:\n1. Install Ollama from [ollama.ai](https://ollama.ai)\n2. Run `ollama serve` in a separate terminal\n3. Refresh this page\n\n**OCR text extraction is working!** You can still upload images/PDFs to extract text."
        return

    try:
        stream = ollama.chat(
            model=MODEL,
            messages=st.session_state.messages,
            stream=True
        )
        response = ""
        for chunk in stream:
            text = chunk.get("message", {}).get("content", "")
            response += text
            yield response
        return
    except Exception as e:
        yield f"❌ Ollama error: {str(e)}\n\nMake sure Ollama is running: `ollama serve`"
        return

# ------------------ STREAM RESPONSE ------------------
if st.session_state.is_generating:
    with st.chat_message("assistant"):
        placeholder = st.empty()
        final = ""

        for part in generate_response():
            final = part
            placeholder.markdown(part)

    st.session_state.messages.append(
        {"role": "assistant", "content": final}
    )
    st.session_state.is_generating = False
