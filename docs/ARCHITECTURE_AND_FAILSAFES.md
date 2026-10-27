# BhashaBridge Architecture & Failsafe Guarantees

## 1. System Architecture Overview

BhashaBridge is an end-to-end pedagogical cross-lingual system designed to make learning closely-related Indian languages transparent, intuitive, and fun.

```
[User Input] (Text / Roman / Script)
     │
     ▼
┌────────────────────────────────────────────────────────┐
│ 1. Detection Layer (detector.py)                       │
│    - Normalization & Unicode canonicalization          │
│    - Script classification (Devanagari vs. Latin)      │
│    - Strong linguistic cues detection (Marathi/Hindi)  │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 2. Transliteration Layer (service.py)                  │
│    - Primary: PyTorch Seq2Seq Model (seq2seq_translit) │
│    - Secondary: IndicXlit phonetic transliterator      │
│    - Failsafe: Rule-based character/ligature mapper    │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 3. Translation Layer (service.py & translator.py)      │
│    - Primary: IndicTrans2 Distilled 320M Transformer   │
│    - Secondary: Cached Parallel Corpus Index           │
│    - Failsafe: Contrastive Pattern Rule-Based Engine   │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 4. Explanation & Alignment Layer (engine.py)           │
│    - 100% Token Coverage Bilingual Aligner             │
│    - Universal Dependencies (UD) Morphological Tagger  │
│    - 3-Gender System Contrast Highlighter              │
│    - Curated 360+ Verified Learning Scenarios KB       │
│    - Failsafe: Autonomous Preserved Legacy Engine      │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 5. Gamification Hub & Learning State (engine.py)       │
│    - Daily Blitz & Sentence Scramble Challenges        │
│    - Contextual Scenarios (Cafes, Markets, Directions) │
│    - Persistent XP, Streaks, and Skill Trees           │
└────────────────────────────────────────────────────────┘
```

---

## 2. Complete Failsafe Matrix

| Component | Primary Mechanism | Secondary Mechanism | Failsafe / Fallback |
| :--- | :--- | :--- | :--- |
| **Transliteration** | Fine-tuned PyTorch Seq2Seq (`seq2seq_translit.pt`) | IndicXlit phonetic engine | Preserved golden checkpoint (`seq2seq_translit_backup.pt`) + Hardcoded rule dictionary |
| **Translation** | AI4Bharat IndicTrans2 320M Model | Curated Parallel Corpus (360+ pairs) | Rule-assisted Pattern Matcher |
| **Explanation** | `HybridExplanationEngine` with 3-Gender & UD tags | Normalized Phonetic Devanagari Matcher (`_norm_dev`) | `LegacyExplanationEngine` (`engine_legacy.py`) |
| **Token Alignment** | Bilingual Subphrase Lexicon Alignment | Soundex/Cognate Phonetic Normalizer | Dynamic Token-by-Token Content Fallback (100% Coverage) |
| **Pronunciation** | Browser SpeechSynthesis API (Web Speech) | Fallback phonetic audio synthesis | Visual Devanagari + Romanized IPA-style transcriptions |

---

## 3. Preserved Checkpoint Registry

To guarantee zero data loss or breaking changes, the following checkpoints are mirrored in `C:\Users\HP\Desktop\NLP\backups`:

1. `backups/seq2seq_translit_backup.pt`:
   - Pre-training baseline PyTorch weights for bidirectional Latin-Devanagari character-level transliteration.
2. `backups/seq2seq_translit.pt`:
   - Fine-tuned weights trained on expanded conversational vocabulary.
3. `backups/engine_legacy.py`:
   - The original, self-contained rule-based explanation engine.
4. `backups/bhashabridge_backend.db`:
   - SQLite snapshot containing seeded gamification scenarios, user profiles, and test attempts.

---

## 4. Key Linguistic Nuances Preserved

1. **The 3-Gender Distinction**:
   - Marathi preserves the Sanskrit Neuter (*नपुंसकलिंग*) gender (e.g. *पाणी*, *पुस्तक*, *घर*), whereas Hindi collapsed into a 2-gender system (*पानी* is masculine in Hindi).
2. **Dative Experiencer Subjects**:
   - In both languages, necessity and desire require dative subjects (*मुझे* in Hindi, *मला* in Marathi) instead of nominative (*मैं* / *मी*).
3. **Gender-Inflected Modals**:
   - Hindi *चाहिए* is invariant. Marathi *हवे आहे* inflects to match the gender and number of the object:
     - Neuter: *मला पाणी हवे आहे.*
     - Masculine: *मला चहा हवा आहे.*
     - Feminine: *मला कॉफी हवी आहे.*
     - Plural: *मला पुस्तके हवी आहेत / पाहिजेत.*
