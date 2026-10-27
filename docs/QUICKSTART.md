# BhashaBridge Quickstart Guide

## Project Layout

```
C:\Users\HP\Desktop\NLP\
├── BhashaBridge/        # Complete application source code & models
├── docs/                # FUTURE_PLAN.txt, ARCHITECTURE, WHAT_WE_BUILT
└── backups/             # Golden checkpoints & legacy failover scripts
```

## Running the Application

### Option A: Using the 1-Click Launchers
Inside `C:\Users\HP\Desktop\NLP\BhashaBridge`:
- Double-click **`run_backend.bat`** to start FastAPI on `http://localhost:8000`.
- Double-click **`run_frontend.bat`** to start Vite on `http://localhost:5173`.
- Open your browser to `http://localhost:5173`.

### Option B: Running Tests
```bash
cd C:\Users\HP\Desktop\NLP\BhashaBridge
pytest backend/tests
```
All 17 end-to-end integration tests will verify:
- Script detection & transliteration
- Bilingual alignment & 100% token coverage
- Translation fallback & IndicTrans2 adapters
- Gamification endpoints & user progress tracking
