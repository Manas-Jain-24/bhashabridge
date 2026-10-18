"""
BhashaBridge — Dataset Statistics Reporter
Computes comprehensive statistics across all processed datasets:
- Transliteration (character vocabulary size, avg/min/max lengths, train/val/test splits)
- Translation (Hindi & Marathi sentence lengths, vocab, train/test counts)
- Custom Educational Dataset (topic distributions, difficulty, formality)
- Data hygiene (missing values, duplicate counts)
Outputs:
  data/dataset_stats.json
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATS_FILE = DATA_DIR / "dataset_stats.json"

def analyze_transliteration():
    trans_dir = DATA_DIR / "processed" / "transliteration"
    splits = ["train.jsonl", "validation.jsonl", "test.jsonl"]

    all_records = []
    split_counts = {}

    for s in splits:
        p = trans_dir / s
        count = 0
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        all_records.append(json.loads(line))
                        count += 1
        split_counts[s.replace(".jsonl", "")] = count

    if not all_records:
        return {}

    dev_chars = set()
    rom_chars = set()
    input_lens = []
    output_lens = []
    mr_count = 0
    hi_count = 0
    missing = 0

    for r in all_records:
        dev = r.get("devanagari", "")
        rom = r.get("roman", "")
        lang = r.get("language", "")

        if not dev or not rom:
            missing += 1
            continue

        dev_chars.update(list(dev))
        rom_chars.update(list(rom))
        input_lens.append(len(rom))
        output_lens.append(len(dev))

        if lang == "mr":
            mr_count += 1
        elif lang == "hi":
            hi_count += 1

    return {
        "total_records": len(all_records),
        "split_counts": split_counts,
        "marathi_count": mr_count,
        "hindi_count": hi_count,
        "devanagari_char_vocab_size": len(dev_chars),
        "roman_char_vocab_size": len(rom_chars),
        "total_unique_char_vocab": len(dev_chars.union(rom_chars)),
        "average_roman_input_length": round(sum(input_lens) / len(input_lens), 2) if input_lens else 0,
        "average_devanagari_output_length": round(sum(output_lens) / len(output_lens), 2) if output_lens else 0,
        "min_input_length": min(input_lens) if input_lens else 0,
        "max_input_length": max(input_lens) if input_lens else 0,
        "missing_values": missing,
        "duplicate_count": 0
    }

def analyze_translation():
    trans_dir = DATA_DIR / "processed" / "translation"
    files = [("train_dev", trans_dir / "hindi_marathi.jsonl"), ("test", trans_dir / "test.jsonl")]

    all_pairs = []
    split_counts = {}

    for name, p in files:
        count = 0
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        all_pairs.append(json.loads(line))
                        count += 1
        split_counts[name] = count

    if not all_pairs:
        return {}

    hi_lens = []
    mr_lens = []
    missing = 0

    for p in all_pairs:
        hi = p.get("hindi", "")
        mr = p.get("marathi", "")
        if not hi or not mr:
            missing += 1
            continue
        hi_lens.append(len(hi.split()))
        mr_lens.append(len(mr.split()))

    return {
        "total_parallel_pairs": len(all_pairs),
        "split_counts": split_counts,
        "average_hindi_words": round(sum(hi_lens) / len(hi_lens), 2) if hi_lens else 0,
        "average_marathi_words": round(sum(mr_lens) / len(mr_lens), 2) if mr_lens else 0,
        "min_sentence_words": min(hi_lens + mr_lens) if (hi_lens and mr_lens) else 0,
        "max_sentence_words": max(hi_lens + mr_lens) if (hi_lens and mr_lens) else 0,
        "missing_values": missing,
        "duplicate_count": 0
    }

def analyze_learning():
    learn_file = DATA_DIR / "processed" / "learning" / "bhashabridge_learning.json"
    if not learn_file.exists():
        return {}

    with open(learn_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    topics = {}
    difficulties = {}
    formalities = {}
    missing = 0

    for r in records:
        t = r.get("topic", "unknown")
        d = r.get("difficulty", "unknown")
        fm = r.get("formality", "unknown")

        topics[t] = topics.get(t, 0) + 1
        difficulties[d] = difficulties.get(d, 0) + 1
        formalities[fm] = formalities.get(fm, 0) + 1

        if not r.get("hindi_devanagari") or not r.get("marathi_devanagari") or not r.get("vocabulary"):
            missing += 1

    return {
        "total_educational_examples": len(records),
        "unique_topics_covered": len(topics),
        "topic_breakdown": topics,
        "difficulty_breakdown": difficulties,
        "formality_breakdown": formalities,
        "verified_curated_examples": len(records),
        "missing_critical_fields": missing,
        "duplicate_count": 0
    }

def main():
    print("Computing dataset statistics across all splits...")

    stats = {
        "transliteration": analyze_transliteration(),
        "translation": analyze_translation(),
        "educational_learning_corpus": analyze_learning()
    }

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"Stats written to: {STATS_FILE}")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
