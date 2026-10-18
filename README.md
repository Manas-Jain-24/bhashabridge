# BhashaBridge 🌉
> **NLP-Powered Hindi–Marathi Language-Learning Application with Roman–Devanagari Bridge**

BhashaBridge enables learners who can speak or understand Hindi/Marathi to master the other language **without being forced to first become proficient in Devanagari script**.

---

## 🌟 Key Features

1. **Principle 1 — Beyond Raw Translation**:
   `Input` ➔ `Script/Language Detection` ➔ `Transliteration` ➔ `Translation` ➔ `Word/Vocabulary Analysis` ➔ `Grammar/Context Explanation` ➔ `Adaptive Practice`.
2. **Principle 2 — Separate Language & Script Tracking**:
   Language proficiency (Vocabulary, Grammar, Speaking) and Script proficiency (Devanagari Recognition, Reading, Writing, Roman-to-Devanagari Bridge) are evaluated independently.
3. **Principle 3 — Pluggable NLP Interfaces**:
   Modular service contracts allow swapping mock/rule engines with **IndicTrans2** (translation), **IndicXlit** (transliteration), and **IndicLID** (language ID).
4. **Bridge Mode**:
   - **Beginner**: Roman script only (`Mala Marathi shikaychi aahe`)
   - **Intermediate**: Roman + Devanagari (`Mala Marathi शिकायची आहे`)
   - **Advanced**: Devanagari script (`मला मराठी शिकायची आहे`)
5. **Interactive Practice Engine**:
   Supports translation, reverse translation, romanisation, script conversion, vocabulary, and grammar error correction questions.

---

## 🚀 Running the Project

### 1. Backend (FastAPI + SQLite)
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### 2. Frontend (React + TypeScript + Vite + Tailwind CSS)
```bash
cd frontend
npm run dev
```
- Frontend Web App: `http://localhost:5173`

### 3. Run Backend Test Suite
```bash
cd backend
python -m pytest tests/
```
