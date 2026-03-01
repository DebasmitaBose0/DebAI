# 🤖 DebAI — Intelligent OCR & Chat Assistant

![DebAI Banner](https://img.shields.io/badge/DebAI-Intelligent_Assistant-blue?style=for-the-badge&logo=robot)
![Python](https://img.shields.io/badge/Python-3.10+-yellow?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**DebAI** is a cutting-edge, dual-theme AI assistant built with **Streamlit**. It combines powerful **OCR (Optical Character Recognition)** capabilities with a sophisticated chat interface, wrapped in a stunning **"Ultimate Glassmorphism"** UI.

Whether you need to extract text from scanned documents, analyze PDFs, or have a conversation with a local (Ollama) or cloud-based (Gemini) LLM, DebAI handles it with style and precision.

---

## ✨ Key Features

### 🧠 **Dual-Core AI Engine**
*   **Local Power**: Seamless integration with **Ollama** for running privacy-focused local models (e.g., Gemma, Llama 3).
*   **Cloud Fallback**: Automatic fallback to **Google Gemini** when local models are unavailable.
*   **Multilingual Support**: Languages can be detected properly in **Hindi**, **English**, and **Bengali**. 
*   **Smart Response Logic**: If a user writes text in English but desires a response in another language (Hindi or Bengali), the model identifies the intended language and responds accordingly.
*   **Future Roadmap**: More necessary changes are in progress, including broader implementation of Indian languages.

### 📄 **Advanced OCR Suite**
*   **Image OCR**: Extract text from images (`.png`, `.jpg`, `.jpeg`) using **Tesseract**.
*   **PDF Analysis**: Read and extract text from multi-page PDF documents.
*   **Auto-Context**: Extracted text is automatically fed into the chat context for immediate analysis.

### 🎨 **Ultimate Glassmorphism UI**
*   **Dual Theme**: Switch between a **Cinematic Dark Mode** and a **Clean, Airy Light Mode**.
*   **Visuals**: Features frosted glass cards, animated backgrounds (`orbFloat`), and smooth transitions.
*   **Responsive**: Perfectly optimized layout for various screen sizes.

### 🛠 **Productivity Tools**
*   **PDF Export**: Download your entire chat session as a formatted PDF report.
*   **Hotkeys**: Quick actions like "Send Last OCR" (Alt+S) for rapid workflows.

---

## 🛠️ Tech Stack

*   **Frontend**: [Streamlit](https://streamlit.io/)
*   **OCR Engine**: [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) & [PyTesseract](https://pypi.org/project/pytesseract/)
*   **PDF Processing**: [pdfplumber](https://github.com/jsvine/pdfplumber)
*   **AI Models**: [Ollama](https://ollama.com/) (Local) & [Google Gemini](https://ai.google.dev/) (Cloud)
*   **Report Generation**: [FPDF](https://pyfpdf.readthedocs.io/)

---

## 🚀 Getting Started

### 1. Prerequisites

Ensure you have the following installed:
*   **Python 3.8+**
*   **[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)**:
    *   *Windows*: Download and install the binary. Note the installation path (default: `C:\Program Files\Tesseract-OCR\tesseract.exe`).
*   **[Ollama](https://ollama.com/)** (Optional, for local models):
    *   Install Ollama and pull a model: `ollama pull gemma:2b` (or your preferred model).

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/DebasmitaBose0/Code-Genie-AI-Team-A-.git
cd Code-Genie-AI-Team-A-
pip install -r requirements.txt
```

### 3. Configuration

DebAI works out-of-the-box with Ollama. To use Google Gemini as a fallback, set your API key:

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="your_api_key_here"
```

*(Optional)* You can also configure the Tesseract path in `AI.py` if it differs from the default.

### 4. Run the App

Launch the application using Streamlit:

```bash
streamlit run AI.py
```

The app will open in your default browser at `http://localhost:8501`.

---

## 📖 Usage Guide

1.  **Upload Documents**: Use the sidebar or top tabs to upload Images or PDFs.
2.  **Extract Text**: The app will automatically extract text. You can choose to send it to the AI immediately or edit/review it.
3.  **Chat**: Type your queries in the chat bar. The AI has context of your uploaded documents.
4.  **Switch Themes**: Toggle between Light and Dark mode using the button in the top-right corner.
5.  **Export**: Click "Download Report (PDF)" in the sidebar to save your conversation.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1.  Fork the project
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
