# BhashaBridge — Dataset Repository & Documentation

This directory contains the lightweight, reproducible datasets for the BhashaBridge Hindi ↔ Marathi language learning application.

---

## 📁 Directory Structure

```text
data/
├── raw/
│   ├── dakshina/
│   │   ├── hi_lexicon_sample.tsv
│   │   └── mr_lexicon_sample.tsv
│   ├── bpcc/
│   │   └── hindi_marathi_parallel_sample.jsonl
│   └── provenance.json
│
├── processed/
│   ├── transliteration/
│   │   ├── train.jsonl            # 65 items (70%)
│   │   ├── validation.jsonl       # 14 items (15%)
│   │   └── test.jsonl             # 14 items (15%)
│   │
│   ├── translation/
│   │   ├── hindi_marathi.jsonl    # 317 pairs (train/dev)
│   │   └── test.jsonl             # 56 pairs (held-out evaluation)
│   │
│   └── learning/
│       └── bhashabridge_learning.json  # 360 curated educational items
│
├── dataset_stats.json             # Automated statistical analysis report
└── README.md
```

---

## 📜 Dataset Provenance & Licenses

| Dataset Name | Source / URL | Version | License | Extraction & Use |
|---|---|---|---|---|
| **Google Dakshina** | [google-research-datasets/dakshina](https://github.com/google-research-datasets/dakshina) | v1.0 | Apache 2.0 | Lightweight lexical sample for Roman ↔ Devanagari transliteration evaluation. |
| **AI4Bharat Aksharantar** | [ai4bharat/Aksharantar](https://huggingface.co/datasets/ai4bharat/Aksharantar) | v1.0 | CC-BY-4.0 | Skipped full 50GB multi-lingual corpus to preserve 8-day timeline; augmented with colloquial Roman variations (`aahe`/`ahe`/`ahey`). |
| **AI4Bharat BPCC** | [ai4bharat/BPCC](https://huggingface.co/datasets/ai4bharat/BPCC) | v1.0 | CC-BY-4.0 | Parallel Hindi–Marathi conversational sentence pairs. Full multi-gigabyte corpus skipped. |
| **BhashaBridge Custom Learning Corpus** | Internal / Hand-reviewed | v1.0 | CC-BY-SA 4.0 | 360 verified sentence pairs with vocabulary alignment, grammar notes, contextual nuances, and common learner traps. |

---

## 🛠️ Reproduction Scripts

All datasets can be rebuilt and verified in seconds using the scripts in `scripts/`:

```bash
# 1. Stage raw samples and provenance metadata
python scripts/download_datasets.py

# 2. Build the 360-example custom educational corpus across 17 topics
python scripts/build_learning_dataset.py

# 3. Clean and partition transliteration splits (train/val/test)
python scripts/prepare_transliteration.py

# 4. Clean and partition parallel translation corpora
python scripts/prepare_translation.py

# 5. Generate and update dataset statistics
python scripts/dataset_stats.py
```

---

## 📊 Summary Statistics (from `dataset_stats.json`)

### Transliteration Corpus
- **Total records**: 93
- **Languages**: Marathi (50), Hindi (43)
- **Splits**: Train (65), Validation (14), Test (14)
- **Devanagari Char Vocab Size**: 46
- **Roman Char Vocab Size**: 22
- **Average Roman Input Length**: 5.1 characters
- **Average Devanagari Output Length**: 4.2 characters
- **Duplicates / Missing**: 0

### Translation Corpus
- **Total parallel sentence pairs**: 373
- **Splits**: Train/Dev (317), Held-out Test (56)
- **Average Hindi Sentence Length**: 6.37 words
- **Average Marathi Sentence Length**: 4.85 words
- **Duplicates / Missing**: 0

### Custom Educational Learning Corpus
- **Total items**: 360
- **Topics covered**: 17 (Greetings, Introductions, College, Classroom, Friends, Family, Food, Shopping, Travel, Directions, Daily routine, Requests, Questions, Feelings, Common informal conversation, Politeness/formality, Common differences)
- **Difficulty breakdown**: Beginner (180), Intermediate (180)
- **Formality breakdown**: Formal (17), Neutral (329), Informal (14)
- **Field completeness**: 100% verified (no missing fields or unverified placeholders)
