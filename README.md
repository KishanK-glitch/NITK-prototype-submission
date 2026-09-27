
# 🎙️ Mirai Gijutsu: Voice-First AI Agent on WhatsApp

**Bridging the digital divide for rural India through voice, local languages, and AI.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Stateful_AI-orange.svg)](https://python.langchain.com/)
[![Twilio](https://img.shields.io/badge/Twilio-WhatsApp_API-red.svg)](https://www.twilio.com/)

## 🚨 The Problem: The Accessibility Gap
In rural India, accessing government welfare schemes (like PM-Kisan or PMJDY) is blocked by massive friction:
1. **Digital & Literacy Barriers:** Portals are complex and highly text-dependent.
2. **Language Constraints:** Most platforms default to English, while 70%+ of rural users prefer vernacular languages.
3. **Exploitative Middlemen:** Users are forced to pay brokers simply to navigate typing interfaces and document uploads.

## 💡 The Solution: WhatsApp-Native AI
**Mirai Gijutsu** is an end-to-end, voice-first AI assistant built directly into WhatsApp. 
* **Zero Learning Curve:** Users just hold the microphone button and speak.
* **Multilingual:** Native support for Kannada (ಕನ್ನಡ), Hindi (हिंदी), and English.
* **Live RAG Engine:** Fetches real-time eligibility rules directly from live government portals—**zero mock data**.
* **Automated OCR:** Users take a photo of their ID documents, and the system automatically extracts necessary details using Regex-optimized Tesseract OCR.

---

## ⚙️ Tech Stack & Architecture

### **Core Backend**
* **FastAPI:** High-performance async web framework for handling Twilio Webhooks.
* **Twilio Sandbox:** Provides the WhatsApp API gateway.
* **LangGraph:** Manages the conversational state machine, handles multi-turn context, and routes user intents (Eligibility Check -> Document Request -> Human Escalation).

### **AI & NLP Pipeline**
* **Groq API (Llama-3 20b):** Ultra-fast LLM inference for conversational reasoning. Token memory is dynamically truncated to prevent API rate limits.
* **Faster-Whisper:** Local, quantized Speech-to-Text (STT) inference to process WhatsApp `.ogg` audio files instantly.
* **Edge-TTS:** Asynchronous Text-to-Speech generation optimized to bypass Twilio's strict 15-second webhook timeouts.

### **Data & Extraction**
* **BeautifulSoup4:** Live web-scraping to feed real-time portal rules into the LLM context.
* **Tesseract OCR (pytesseract) + OpenCV:** Extracts IDs (like 12-digit Aadhaar/government IDs) and Land Records from uploaded images securely.

---

## 🚀 Installation & Setup Guide

### 1. Prerequisites
* Python 3.10+
* Tesseract OCR installed on your system (added to PATH)
* Ngrok (for local webhook tunneling)
* A Twilio Account (WhatsApp Sandbox enabled)
* A Groq API Key

### 2. Clone the Repository
```bash
git clone [https://github.com/KishanK-glitch/NITK-prototype-submission.git](https://github.com/KishanK-glitch/NITK-prototype-submission.git)
cd NITK-prototype-submission

```

### 3. Install Dependencies

Create a virtual environment and install the required Python packages:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt

```

### 4. Environment Variables

Create a `.env` file in the root directory and add your credentials:

```env
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
GROQ_API_KEY=your_groq_api_key

```

### 5. Run the Application

Start the FastAPI server:

```bash
python main.py

```

*(The server will run on `http://localhost:8000`)*

### 6. Expose the Webhook

In a new terminal window, use Ngrok to expose your local server to the internet:

```bash
ngrok http 8000

```

Copy the generated Forwarding URL (e.g., `https://your-url.ngrok-free.dev`) and paste it into your Twilio WhatsApp Sandbox configuration under **"When a message comes in"** as:
`https://your-url.ngrok-free.dev/webhook` (Set method to `POST`).

---

## 📱 How to Use (Demo Flow)

1. **Opt-in:** Send the Twilio Sandbox join code (e.g., `join word-word`) to the provided WhatsApp number.
2. **Start Speaking:** Send a voice note in English, Hindi, or Kannada asking about a scheme (e.g., *"How do I apply for PM Kisan?"*).
3. **Eligibility Check:** The AI scrapes the live portal, checks your eligibility, and replies with an audio message in your language.
4. **Document Upload:** The bot will request your ID. Upload a photo of the ID card.
5. **Verification:** The backend processes the image via OCR, masks the extracted ID for privacy, and clears you for the next step.

---

## 🔮 Future Scope

* Expansion to cover all 22 official regional languages of India.
* Integration with the actual government e-Pramaan / DigiLocker APIs for seamless, paperless application submissions.
* Multi-modal AI video generation for visual sign-language assistance.

---

*Built with ❤️ for rural empowerment by Team Mirai Gijutsu.*

```

```
