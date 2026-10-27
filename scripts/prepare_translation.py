"""
BhashaBridge — Translation Dataset Preprocessing
Processes raw BPCC and educational parallel pairs into clean Hindi <-> Marathi
translation corpora:
  data/processed/translation/hindi_marathi.jsonl (training & dev)
  data/processed/translation/test.jsonl (evaluation test set)
"""

import json
import random
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_FILE = BASE_DIR / "data" / "raw" / "bpcc" / "hindi_marathi_parallel_sample.jsonl"
OUT_DIR = BASE_DIR / "data" / "processed" / "translation"

MAX_TRANSLATION_EXAMPLES = 20000

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    records = []
    seen = set()

    if RAW_FILE.exists():
        with open(RAW_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                hi = unicodedata.normalize("NFKC", data["hindi"].strip())
                mr = unicodedata.normalize("NFKC", data["marathi"].strip())
                key = (hi, mr)
                if key not in seen:
                    seen.add(key)
                    records.append({
                        "hindi": hi,
                        "marathi": mr,
                        "domain": data.get("domain", "conversational"),
                        "hindi_char_len": len(hi),
                        "marathi_char_len": len(mr)
                    })

    # Also augment from the educational learning dataset sentences for conversational richness
    learn_file = BASE_DIR / "data" / "processed" / "learning" / "bhashabridge_learning.json"
    if learn_file.exists():
        with open(learn_file, "r", encoding="utf-8") as f:
            learn_data = json.load(f)
            for item in learn_data:
                hi = unicodedata.normalize("NFKC", item["hindi_devanagari"].strip())
                mr = unicodedata.normalize("NFKC", item["marathi_devanagari"].strip())
                key = (hi, mr)
                if key not in seen and len(records) < MAX_TRANSLATION_EXAMPLES:
                    seen.add(key)
                    records.append({
                        "hindi": hi,
                        "marathi": mr,
                        "domain": item.get("topic", "conversational"),
                        "hindi_char_len": len(hi),
                        "marathi_char_len": len(mr)
                    })

    random.shuffle(records)
    records = records[:MAX_TRANSLATION_EXAMPLES]

    # Split into general set (85%) and held-out test evaluation set (15%)
    split_idx = int(0.85 * len(records))
    test_set = records[split_idx:]
    import sys
    sys.path.insert(0, str(BASE_DIR / "backend"))
    from app.services.translation.corpus import exclude_heldout, sources
    forbidden = ({sources(p)[0] for p in test_set}, {sources(p)[1] for p in test_set})
    train_dev_set = exclude_heldout(records[:split_idx], forbidden)

    main_out = OUT_DIR / "hindi_marathi.jsonl"
    with open(main_out, "w", encoding="utf-8") as f:
        for r in train_dev_set:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    test_out = OUT_DIR / "test.jsonl"
    with open(test_out, "w", encoding="utf-8") as f:
        for r in test_set:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Prepared translation datasets:")
    print(f"  - {main_out.name}: {len(train_dev_set)} sentence pairs")
    print(f"  - {test_out.name}: {len(test_set)} sentence pairs")

if __name__ == "__main__":
    main()
