"""
BhashaBridge — External Open-Source Corpus Ingestion & Indexer
Ingests public Hindi <-> Marathi parallel corpora from Hugging Face:
  1. Lots-of-LoRAs/task1082_pib_translation_marathi_hindi (1,496 pairs)
  2. supergoose/flan_combined_task1081_pib_translation_hindi_marathi (4,476 pairs)
  3. Waghya/colloquial_datasets_hindi_marathi_tamil_telugu (117 pairs)

Cleans, deduplicates, tags contrastive grammar patterns, and indexes them
for both the Translation and Explanation engines.
"""

import os
import re
import json
import random
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "external_corpora"
PROCESSED_TRANS_DIR = BASE_DIR / "data" / "processed" / "translation"
PROCESSED_LEARN_DIR = BASE_DIR / "data" / "processed" / "learning"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_TRANS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_LEARN_DIR.mkdir(parents=True, exist_ok=True)

# Grammar pattern detection heuristics
GRAMMAR_PATTERNS = {
    "dative_subject": {
        "marathi": [r"\bमला\b", r"\bतुला\b", r"\bत्याला\b", r"\bतिला\b", r"\bआम्हाला\b", r"\bतुम्हाला\b"],
        "hindi": [r"\bमुझे\b", r"\bतुझे\b", r"\bउसे\b", r"\bहमें\b", r"\bआपको\b", r"\bतुम्हें\b"],
        "concept": "Dative Subject (मला / मुझे) Experiencer Case"
    },
    "continuous_aspect": {
        "marathi": [r"\bजात आहे\b", r"\bकरत आहे\b", r"\bखात आहे\b", r"\bपाहत आहे\b", r"\bबोलत आहे\b", r"\bयेत आहे\b"],
        "hindi": [r"\bजा रहा\b", r"\bकर रहा\b", r"\bखा रहा\b", r"\bदेख रहा\b", r"\bबोल रहा\b", r"\bआ रहा\b"],
        "concept": "Continuous Aspect (त आहे vs रहा है)"
    },
    "obligation_verb": {
        "marathi": [r"[^\s]+चं आहे", r"[^\s]+ची आहे", r"[^\s]+चे आहेत", r"\bपाहिजे\b"],
        "hindi": [r"\bजाना है\b", r"\bकरना है\b", r"\bसीखनी है\b", r"\bचाहिए\b"],
        "concept": "Obligation / Infinitive Auxiliary"
    },
    "question_tag_ka": {
        "marathi": [r"\bका\?", r"\bका\s*।?$"],
        "hindi": [r"^क्या\b", r"\bक्या\?"],
        "concept": "Yes/No Question Marker (का vs Initial क्या)"
    },
    "neuter_gender": {
        "marathi": [r"\bमाझं\b", r"\bतुझं\b", r"\bत्याचं\b", r"\bकाय\b", r"\bहे\b", r"\bते\b"],
        "hindi": [r"\bमेरा\b", r"\bमेरी\b", r"\bतुम्हारा\b", r"\bक्या\b", r"\bयह\b", r"\bवह\b"],
        "concept": "Neuter Gender Alignment (Marathi 3-Gender System)"
    }
}

def clean_text(text: str) -> str:
    """Normalizes text and strips stray punctuation/tags."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text.strip())
    t = re.sub(r'[\r\n\t]+', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip()

def detect_grammar_tags(hindi_text: str, marathi_text: str) -> List[str]:
    """Identifies linguistic contrastive patterns present in the pair."""
    tags = []
    for tag_name, rules in GRAMMAR_PATTERNS.items():
        mr_match = any(re.search(pat, marathi_text) for pat in rules["marathi"])
        hi_match = any(re.search(pat, hindi_text) for pat in rules["hindi"])
        if mr_match or hi_match:
            tags.append(tag_name)
    return tags

def extract_lora_dataset(ds) -> List[Dict[str, Any]]:
    """Extracts pairs from Lots-of-LoRAs/task1082_pib_translation_marathi_hindi."""
    pairs = []
    pattern = re.compile(r'Now complete the following example -\s*\nInput:\s*(.+?)\nOutput:', re.DOTALL)
    
    for row in ds:
        inp = row.get("input", "")
        out = row.get("output", "")
        if isinstance(out, list) and len(out) > 0:
            out = out[0]
            
        m = pattern.search(inp)
        if m:
            mr_text = clean_text(m.group(1))
            hi_text = clean_text(out)
            
            # Simple length and Devanagari validation
            if len(mr_text) >= 5 and len(hi_text) >= 5:
                pairs.append({
                    "hindi": hi_text,
                    "marathi": mr_text,
                    "source": "PIB_LoRA_task1082",
                    "domain": "governance_and_public_life"
                })
    return pairs

def extract_supergoose_dataset(ds) -> List[Dict[str, Any]]:
    """Extracts pairs from supergoose/flan_combined_task1081_pib_translation_hindi_marathi."""
    pairs = []
    for row in ds:
        inp = row.get("inputs", "")
        out = row.get("targets", "")
        
        matches = re.findall(r'Input:\s*(.+?)(?=\nOutput:|\nExample Output:|\Z)', inp, re.DOTALL)
        if matches:
            hi_text = clean_text(matches[-1])
            mr_text = clean_text(out)
            
            if len(hi_text) >= 5 and len(mr_text) >= 5:
                pairs.append({
                    "hindi": hi_text,
                    "marathi": mr_text,
                    "source": "PIB_Flan_task1081",
                    "domain": "governance_and_public_life"
                })
    return pairs

def extract_waghya_dataset(ds) -> List[Dict[str, Any]]:
    """Extracts pairs from Waghya/colloquial_datasets_hindi_marathi_tamil_telugu."""
    pairs = []
    for row in ds:
        hi_text = clean_text(row.get("Hindi", ""))
        mr_text = clean_text(row.get("Marathi", ""))
        eng_text = clean_text(row.get("English", ""))
        
        if len(hi_text) >= 3 and len(mr_text) >= 3:
            pairs.append({
                "hindi": hi_text,
                "marathi": mr_text,
                "english": eng_text,
                "source": "Waghya_Colloquial",
                "domain": "colloquial_conversation"
            })
    return pairs

def main():
    print("=" * 60)
    print("BhashaBridge: Open-Source Parallel Corpus Ingestion & Indexer")
    print("=" * 60)
    
    from datasets import load_dataset
    
    all_pairs = []
    seen = set()
    
    # 1. Ingest Lots-of-LoRAs
    try:
        print("[*] Ingesting Lots-of-LoRAs/task1082_pib_translation_marathi_hindi...")
        ds_lora = load_dataset("Lots-of-LoRAs/task1082_pib_translation_marathi_hindi", split="train")
        lora_pairs = extract_lora_dataset(ds_lora)
        print(f"    -> Extracted {len(lora_pairs)} valid pairs.")
        all_pairs.extend(lora_pairs)
    except Exception as e:
        print(f"    [!] Error loading LoRA dataset: {e}")

    # 2. Ingest Supergoose Flan
    try:
        print("[*] Ingesting supergoose/flan_combined_task1081_pib_translation_hindi_marathi...")
        ds_flan = load_dataset("supergoose/flan_combined_task1081_pib_translation_hindi_marathi", split="train")
        flan_pairs = extract_supergoose_dataset(ds_flan)
        print(f"    -> Extracted {len(flan_pairs)} valid pairs.")
        all_pairs.extend(flan_pairs)
    except Exception as e:
        print(f"    [!] Error loading Flan dataset: {e}")

    # 3. Ingest Waghya Colloquial
    try:
        print("[*] Ingesting Waghya/colloquial_datasets_hindi_marathi_tamil_telugu...")
        ds_waghya = load_dataset("Waghya/colloquial_datasets_hindi_marathi_tamil_telugu", split="train")
        waghya_pairs = extract_waghya_dataset(ds_waghya)
        print(f"    -> Extracted {len(waghya_pairs)} valid colloquial pairs.")
        all_pairs.extend(waghya_pairs)
    except Exception as e:
        print(f"    [!] Error loading Waghya dataset: {e}")

    # 4. Deduplicate and Tag
    print("[*] Deduplicating and tagging contrastive grammar patterns...")
    clean_pairs = []
    grammar_counts = {k: 0 for k in GRAMMAR_PATTERNS}
    
    for p in all_pairs:
        hi = p["hindi"]
        mr = p["marathi"]
        key = (hi, mr)
        if key not in seen and len(hi.split()) <= 45 and len(mr.split()) <= 45:
            seen.add(key)
            tags = detect_grammar_tags(hi, mr)
            for t in tags:
                grammar_counts[t] += 1
                
            entry = {
                "id": len(clean_pairs) + 1,
                "hindi": hi,
                "marathi": mr,
                "english": p.get("english", ""),
                "domain": p.get("domain", "general"),
                "source": p.get("source", "external"),
                "grammar_tags": tags,
                "hindi_word_count": len(hi.split()),
                "marathi_word_count": len(mr.split())
            }
            clean_pairs.append(entry)

    print(f"[*] Total unique, verified parallel sentence pairs: {len(clean_pairs)}")
    print(f"[*] Grammar Pattern Breakdown:")
    for tag, cnt in grammar_counts.items():
        print(f"    - {tag}: {cnt} sentence pairs")

    # 5. Save Raw External Parallel JSONL
    raw_output_file = RAW_DIR / "hindi_marathi_parallel_hf.jsonl"
    with open(raw_output_file, "w", encoding="utf-8") as f:
        for p in clean_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"[*] Saved raw ingested dataset to {raw_output_file}")

    # 6. Save Learning Index for Explanation Engine
    learning_index_file = PROCESSED_LEARN_DIR / "external_parallel_learning_index.json"
    with open(learning_index_file, "w", encoding="utf-8") as f:
        json.dump(clean_pairs, f, ensure_ascii=False, indent=2)
    print(f"[*] Saved explanation learning index to {learning_index_file}")

    # 7. Update Translation splits (Train/Dev and Test)
    # Shuffle deterministically
    random.seed(42)
    shuffled = clean_pairs.copy()
    random.shuffle(shuffled)
    
    # Keep 15% for held-out evaluation
    test_size = min(500, int(0.15 * len(shuffled)))
    train_dev = shuffled[:-test_size]
    test_set = shuffled[-test_size:]
    
    train_file = PROCESSED_TRANS_DIR / "hindi_marathi.jsonl"
    with open(train_file, "w", encoding="utf-8") as f:
        for r in train_dev:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    test_file = PROCESSED_TRANS_DIR / "test.jsonl"
    with open(test_file, "w", encoding="utf-8") as f:
        for r in test_set:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    print(f"[*] Updated translation corpus:")
    print(f"    - Train/Dev: {len(train_dev)} pairs in {train_file.name}")
    print(f"    - Test: {len(test_set)} pairs in {test_file.name}")

    # 8. Update Dataset Stats
    stats_file = BASE_DIR / "data" / "dataset_stats.json"
    stats = {}
    if stats_file.exists():
        with open(stats_file, "r", encoding="utf-8") as sf:
            stats = json.load(sf)
            
    stats["translation"]["total_parallel_pairs"] = len(clean_pairs)
    stats["translation"]["split_counts"] = {
        "train_dev": len(train_dev),
        "test": len(test_set)
    }
    stats["translation"]["external_sources"] = ["Lots-of-LoRAs", "supergoose-flan", "Waghya-colloquial"]
    stats["translation"]["grammar_pattern_coverage"] = grammar_counts
    
    with open(stats_file, "w", encoding="utf-8") as sf:
        json.dump(stats, sf, ensure_ascii=False, indent=2)
    print(f"[*] Updated dataset stats at {stats_file}")
    print("=" * 60)
    print("Ingestion & Indexing Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
