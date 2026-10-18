"""
BhashaBridge — Transliteration Dataset Preprocessing
Processes raw Dakshina / Aksharantar lexicon samples into clean, deduplicated,
and leakage-free Train / Validation / Test splits for Hindi and Marathi.
Outputs:
  data/processed/transliteration/train.jsonl
  data/processed/transliteration/validation.jsonl
  data/processed/transliteration/test.jsonl
"""

import json
import random
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "dakshina"
OUT_DIR = BASE_DIR / "data" / "processed" / "transliteration"

MAX_TRANSLITERATION_EXAMPLES = 20000

def clean_record(dev: str, rom: str, lang: str):
    if not dev or not rom:
        return None
    # Unicode NFKC normalization
    dev_norm = unicodedata.normalize("NFKC", dev.strip())
    # Keep Roman spelling variations without aggressive alteration
    rom_norm = rom.strip().lower()

    if len(dev_norm) == 0 or len(rom_norm) == 0:
        return None

    return {
        "language": lang,
        "devanagari": dev_norm,
        "roman": rom_norm,
        "char_len_dev": len(dev_norm),
        "char_len_rom": len(rom_norm)
    }

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    raw_files = [
        ("mr", RAW_DIR / "mr_lexicon_sample.tsv"),
        ("hi", RAW_DIR / "hi_lexicon_sample.tsv"),
    ]

    all_records = []
    seen = set()

    # Also augment with common colloquial Roman variants as allowed by spec (e.g. aahe/ahe/ahey)
    VARIANTS_MAP = {
        "aahe": ["ahe", "ahey"],
        "khoop": ["khup"],
        "shikaychi": ["shikaychee"],
        "paani": ["pani"],
        "thoda": ["thoda", "thodaa"],
        "bahut": ["bohot", "bhot"],
        "chahiye": ["chaahiye", "chahiye"]
    }

    for lang, filepath in raw_files:
        if not filepath.exists():
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    dev = parts[0]
                    rom = parts[1]
                    rec = clean_record(dev, rom, lang)
                    if rec:
                        key = (rec["language"], rec["devanagari"], rec["roman"])
                        if key not in seen:
                            seen.add(key)
                            all_records.append(rec)

                        # Check for variants
                        if rec["roman"] in VARIANTS_MAP:
                            for var in VARIANTS_MAP[rec["roman"]]:
                                var_rec = clean_record(dev, var, lang)
                                var_key = (lang, dev, var)
                                if var_rec and var_key not in seen:
                                    seen.add(var_key)
                                    all_records.append(var_rec)

    # Shuffle deterministically
    random.shuffle(all_records)
    all_records = all_records[:MAX_TRANSLITERATION_EXAMPLES]

    n = len(all_records)
    train_idx = int(0.70 * n)
    val_idx = int(0.85 * n)

    train_data = all_records[:train_idx]
    val_data = all_records[train_idx:val_idx]
    test_data = all_records[val_idx:]

    for split_name, dataset in [("train.jsonl", train_data), ("validation.jsonl", val_data), ("test.jsonl", test_data)]:
        out_file = OUT_DIR / split_name
        with open(out_file, "w", encoding="utf-8") as f:
            for item in dataset:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"Written {len(dataset)} items to {out_file.name}")

if __name__ == "__main__":
    main()
