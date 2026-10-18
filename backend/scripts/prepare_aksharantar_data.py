"""
Prepare clean, high-coverage transliteration datasets from AI4Bharat Aksharantar & conversational datasets.
Extracts Marathi and Hindi word pairs into data/processed/transliteration/train.jsonl & validation.jsonl.
"""

import os
import re
import json
import random
from pathlib import Path

def clean_word(word: str) -> str:
    return word.strip().strip("।,!?;:\"'()[]{}")

def prepare_data(max_train_samples: int = 200000, max_val_samples: int = 10000):
    root_dir = Path(__file__).resolve().parent.parent.parent
    raw_dir = root_dir / "data" / "raw" / "aksharantar"
    proc_dir = root_dir / "data" / "processed" / "transliteration"
    learning_path = root_dir / "data" / "processed" / "learning" / "bhashabridge_learning.json"
    parallel_path = root_dir / "data" / "processed" / "translation" / "hindi_marathi.jsonl"
    proc_dir.mkdir(parents=True, exist_ok=True)

    train_out = proc_dir / "train.jsonl"
    val_out = proc_dir / "validation.jsonl"

    train_pairs = []
    val_pairs = []
    seen = set()

    # 1. First, extract conversational word pairs from learning and parallel datasets
    if learning_path.exists():
        print(f"[*] Extracting conversational words from {learning_path}...")
        try:
            with open(learning_path, "r", encoding="utf-8") as f:
                learn_data = json.load(f)
            conv_count = 0
            for item in learn_data:
                # Marathi
                mr_rom_tokens = [clean_word(w).lower() for w in re.findall(r"[a-zA-Z]+", item.get("marathi_roman", ""))]
                mr_dev_tokens = [clean_word(w) for w in re.findall(r"[\u0900-\u097F]+", item.get("marathi_devanagari", ""))]
                if len(mr_rom_tokens) == len(mr_dev_tokens):
                    for r, d in zip(mr_rom_tokens, mr_dev_tokens):
                        if r and d and len(r) <= 25 and len(d) <= 25:
                            # Replicate 5 times for strong conversational prior
                            for _ in range(5):
                                train_pairs.append({"roman": r, "devanagari": d, "language": "mr"})
                            conv_count += 1
                # Hindi
                hi_rom_tokens = [clean_word(w).lower() for w in re.findall(r"[a-zA-Z]+", item.get("hindi_roman", ""))]
                hi_dev_tokens = [clean_word(w) for w in re.findall(r"[\u0900-\u097F]+", item.get("hindi_devanagari", ""))]
                if len(hi_rom_tokens) == len(hi_dev_tokens):
                    for r, d in zip(hi_rom_tokens, hi_dev_tokens):
                        if r and d and len(r) <= 25 and len(d) <= 25:
                            for _ in range(5):
                                train_pairs.append({"roman": r, "devanagari": d, "language": "hi"})
                            conv_count += 1
            print(f"[*] Added {conv_count} conversational word instances.")
        except Exception as e:
            print(f"[!] Warning reading learning dataset: {e}")

    # Core colloquial pairs, names, and conversational typing variations
    seed_pairs = [
        # Conversational Marathi
        {"roman": "porghi", "devanagari": "पोर्गी", "language": "mr"},
        {"roman": "porghi", "devanagari": "पोरगी", "language": "mr"},
        {"roman": "porgi", "devanagari": "पोरगी", "language": "mr"},
        {"roman": "porgi", "devanagari": "पोर्गी", "language": "mr"},
        {"roman": "mala", "devanagari": "मला", "language": "mr"},
        {"roman": "majha", "devanagari": "माझा", "language": "mr"},
        {"roman": "maza", "devanagari": "माझा", "language": "mr"},
        {"roman": "mazha", "devanagari": "माझा", "language": "mr"},
        {"roman": "tula", "devanagari": "तुला", "language": "mr"},
        {"roman": "aahe", "devanagari": "आहे", "language": "mr"},
        {"roman": "ahe", "devanagari": "आहे", "language": "mr"},
        {"roman": "aahes", "devanagari": "आहेस", "language": "mr"},
        {"roman": "ahes", "devanagari": "आहेस", "language": "mr"},
        {"roman": "var", "devanagari": "वर", "language": "mr"},
        {"roman": "war", "devanagari": "वर", "language": "mr"},
        {"roman": "prem", "devanagari": "प्रेम", "language": "mr"},
        {"roman": "ek", "devanagari": "एक", "language": "mr"},
        {"roman": "jaycha", "devanagari": "जायचं", "language": "mr"},
        {"roman": "jayecha", "devanagari": "जायचं", "language": "mr"},
        {"roman": "kasa", "devanagari": "कसा", "language": "mr"},
        {"roman": "kashi", "devanagari": "कशी", "language": "mr"},
        {"roman": "kase", "devanagari": "कसे", "language": "mr"},
        {"roman": "kuthe", "devanagari": "कुठे", "language": "mr"},
        {"roman": "kute", "devanagari": "कुठे", "language": "mr"},
        {"roman": "kadhi", "devanagari": "कधी", "language": "mr"},
        {"roman": "kadi", "devanagari": "कधी", "language": "mr"},
        {"roman": "jevlas", "devanagari": "जेवलास", "language": "mr"},
        {"roman": "jevlis", "devanagari": "जेवलीस", "language": "mr"},
        {"roman": "shikaycha", "devanagari": "शिकायचं", "language": "mr"},
        {"roman": "sikaycha", "devanagari": "शिकायचं", "language": "mr"},
        {"roman": "zala", "devanagari": "झाला", "language": "mr"},
        {"roman": "jhala", "devanagari": "झाला", "language": "mr"},
        {"roman": "zhala", "devanagari": "झाला", "language": "mr"},
        {"roman": "shala", "devanagari": "शाळा", "language": "mr"},
        {"roman": "school", "devanagari": "शाळा", "language": "mr"},
        {"roman": "school", "devanagari": "स्कूल", "language": "hi"},
        {"roman": "college", "devanagari": "कॉलेज", "language": "mr"},
        {"roman": "college", "devanagari": "कॉलेज", "language": "hi"},
        {"roman": "clg", "devanagari": "कॉलेज", "language": "mr"},
        {"roman": "clg", "devanagari": "कॉलेज", "language": "hi"},
        {"roman": "bday", "devanagari": "बर्थडे", "language": "mr"},
        {"roman": "bday", "devanagari": "बर्थडे", "language": "hi"},
        
        # Conversational Hindi
        {"roman": "mujhe", "devanagari": "मुझे", "language": "hi"},
        {"roman": "mera", "devanagari": "मेरा", "language": "hi"},
        {"roman": "hai", "devanagari": "है", "language": "hi"},
        {"roman": "hoon", "devanagari": "हूँ", "language": "hi"},
        {"roman": "pyar", "devanagari": "प्यार", "language": "hi"},
        {"roman": "ladki", "devanagari": "लड़की", "language": "hi"},
        {"roman": "par", "devanagari": "पर", "language": "hi"},
        {"roman": "jana", "devanagari": "जाना", "language": "hi"},
        {"roman": "jaana", "devanagari": "जाना", "language": "hi"},
        {"roman": "meko", "devanagari": "मुझे", "language": "hi"},
        {"roman": "mereko", "devanagari": "मुझे", "language": "hi"},
        {"roman": "teko", "devanagari": "तुझे", "language": "hi"},
        {"roman": "tereko", "devanagari": "तुझे", "language": "hi"},
        {"roman": "apanko", "devanagari": "हमें", "language": "hi"},
        {"roman": "nahi", "devanagari": "नहीं", "language": "hi"},
        {"roman": "nhi", "devanagari": "नहीं", "language": "hi"},
        {"roman": "kal", "devanagari": "कल", "language": "hi"},
        {"roman": "aaj", "devanagari": "आज", "language": "hi"},
        {"roman": "abhi", "devanagari": "अभी", "language": "hi"},

        # High-Frequency Indian Names (Ensuring proper transliteration for both Marathi & Hindi)
        {"roman": "manas", "devanagari": "मानस", "language": "mr"},
        {"roman": "manas", "devanagari": "मानस", "language": "hi"},
        {"roman": "rohan", "devanagari": "रोहन", "language": "mr"},
        {"roman": "rohan", "devanagari": "रोहन", "language": "hi"},
        {"roman": "amit", "devanagari": "अमित", "language": "mr"},
        {"roman": "amit", "devanagari": "अमित", "language": "hi"},
        {"roman": "rahul", "devanagari": "राहुल", "language": "mr"},
        {"roman": "rahul", "devanagari": "राहुल", "language": "hi"},
        {"roman": "sneha", "devanagari": "स्नेहा", "language": "mr"},
        {"roman": "sneha", "devanagari": "स्नेहा", "language": "hi"},
        {"roman": "aniket", "devanagari": "अनिकेत", "language": "mr"},
        {"roman": "aniket", "devanagari": "अनिकेत", "language": "hi"},
        {"roman": "pooja", "devanagari": "पूजा", "language": "mr"},
        {"roman": "pooja", "devanagari": "पूजा", "language": "hi"},
        {"roman": "puja", "devanagari": "पूजा", "language": "mr"},
        {"roman": "puja", "devanagari": "पूजा", "language": "hi"},
        {"roman": "sachin", "devanagari": "सचिन", "language": "mr"},
        {"roman": "sachin", "devanagari": "सचिन", "language": "hi"},
        {"roman": "priya", "devanagari": "प्रिया", "language": "mr"},
        {"roman": "priya", "devanagari": "प्रिया", "language": "hi"},
        {"roman": "aarav", "devanagari": "आरव", "language": "mr"},
        {"roman": "aarav", "devanagari": "आरव", "language": "hi"},
        {"roman": "arav", "devanagari": "आरव", "language": "mr"},
        {"roman": "arav", "devanagari": "आरव", "language": "hi"},
        {"roman": "gaurav", "devanagari": "गौरव", "language": "mr"},
        {"roman": "gaurav", "devanagari": "गौरव", "language": "hi"},
        {"roman": "deepak", "devanagari": "दीपक", "language": "mr"},
        {"roman": "deepak", "devanagari": "दीपक", "language": "hi"},
        {"roman": "dipak", "devanagari": "दीपक", "language": "mr"},
        {"roman": "dipak", "devanagari": "दीपक", "language": "hi"},
        {"roman": "tanmay", "devanagari": "तन्मय", "language": "mr"},
        {"roman": "tanmay", "devanagari": "तन्मय", "language": "hi"},
        {"roman": "shubham", "devanagari": "शुभम", "language": "mr"},
        {"roman": "shubham", "devanagari": "शुभम", "language": "hi"},
        {"roman": "subham", "devanagari": "शुभम", "language": "mr"},
        {"roman": "subham", "devanagari": "शुभम", "language": "hi"},
        {"roman": "rohit", "devanagari": "रोहित", "language": "mr"},
        {"roman": "rohit", "devanagari": "रोहित", "language": "hi"},
        {"roman": "virat", "devanagari": "विराट", "language": "mr"},
        {"roman": "virat", "devanagari": "विराट", "language": "hi"},
        {"roman": "anushka", "devanagari": "अनुष्का", "language": "mr"},
        {"roman": "anushka", "devanagari": "अनुष्का", "language": "hi"},
        {"roman": "neha", "devanagari": "नेहा", "language": "mr"},
        {"roman": "neha", "devanagari": "नेहा", "language": "hi"},
        {"roman": "kavita", "devanagari": "कविता", "language": "mr"},
        {"roman": "kavita", "devanagari": "कविता", "language": "hi"},
        {"roman": "prashant", "devanagari": "प्रशांत", "language": "mr"},
        {"roman": "prashant", "devanagari": "प्रशांत", "language": "hi"},
        {"roman": "sameer", "devanagari": "समीर", "language": "mr"},
        {"roman": "sameer", "devanagari": "समीर", "language": "hi"},
        {"roman": "samir", "devanagari": "समीर", "language": "mr"},
        {"roman": "samir", "devanagari": "समीर", "language": "hi"},
        {"roman": "sandeep", "devanagari": "संदीप", "language": "mr"},
        {"roman": "sandeep", "devanagari": "संदीप", "language": "hi"},
        {"roman": "pradeep", "devanagari": "प्रदीप", "language": "mr"},
        {"roman": "pradeep", "devanagari": "प्रदीप", "language": "hi"},
        {"roman": "santosh", "devanagari": "संतोष", "language": "mr"},
        {"roman": "santosh", "devanagari": "संतोष", "language": "hi"},
        {"roman": "amol", "devanagari": "अमोल", "language": "mr"},
        {"roman": "amol", "devanagari": "अमोल", "language": "hi"},
        {"roman": "praveen", "devanagari": "प्रवीण", "language": "mr"},
        {"roman": "praveen", "devanagari": "प्रवीण", "language": "hi"},
        {"roman": "pravin", "devanagari": "प्रवीण", "language": "mr"},
        {"roman": "pravin", "devanagari": "प्रवीण", "language": "hi"},
        {"roman": "manish", "devanagari": "मनीष", "language": "mr"},
        {"roman": "manish", "devanagari": "मनीष", "language": "hi"},
        {"roman": "ajay", "devanagari": "अजय", "language": "mr"},
        {"roman": "ajay", "devanagari": "अजय", "language": "hi"},
        {"roman": "vijay", "devanagari": "विजय", "language": "mr"},
        {"roman": "vijay", "devanagari": "विजय", "language": "hi"},
        {"roman": "ganesh", "devanagari": "गणेश", "language": "mr"},
        {"roman": "ganesh", "devanagari": "गणेश", "language": "hi"},
        {"roman": "suresh", "devanagari": "सुरेश", "language": "mr"},
        {"roman": "suresh", "devanagari": "सुरेश", "language": "hi"},
        {"roman": "ramesh", "devanagari": "रमेश", "language": "mr"},
        {"roman": "ramesh", "devanagari": "रमेश", "language": "hi"},
        {"roman": "mahesh", "devanagari": "महेश", "language": "mr"},
        {"roman": "mahesh", "devanagari": "महेश", "language": "hi"},
        {"roman": "raj", "devanagari": "राज", "language": "mr"},
        {"roman": "raj", "devanagari": "राज", "language": "hi"},
        {"roman": "sunil", "devanagari": "सुनील", "language": "mr"},
        {"roman": "sunil", "devanagari": "सुनील", "language": "hi"},
        {"roman": "anil", "devanagari": "अनिल", "language": "mr"},
        {"roman": "anil", "devanagari": "अनिल", "language": "hi"},
        {"roman": "nitin", "devanagari": "नितीन", "language": "mr"},
        {"roman": "nitin", "devanagari": "नितिन", "language": "hi"},
        {"roman": "vikas", "devanagari": "विकास", "language": "mr"},
        {"roman": "vikas", "devanagari": "विकास", "language": "hi"},
        {"roman": "anand", "devanagari": "आनंद", "language": "mr"},
        {"roman": "anand", "devanagari": "आनंद", "language": "hi"},
        {"roman": "prakash", "devanagari": "प्रकाश", "language": "mr"},
        {"roman": "prakash", "devanagari": "प्रकाश", "language": "hi"},
        {"roman": "mumbai", "devanagari": "मुंबई", "language": "mr"},
        {"roman": "mumbai", "devanagari": "मुंबई", "language": "hi"},
        {"roman": "pune", "devanagari": "पुणे", "language": "mr"},
        {"roman": "pune", "devanagari": "पुणे", "language": "hi"},
        {"roman": "delhi", "devanagari": "दिल्ली", "language": "mr"},
        {"roman": "delhi", "devanagari": "दिल्ली", "language": "hi"},
        {"roman": "nagpur", "devanagari": "नागपूर", "language": "mr"},
        {"roman": "nagpur", "devanagari": "नागपुर", "language": "hi"},
        {"roman": "nashik", "devanagari": "नाशिक", "language": "mr"},
        {"roman": "nashik", "devanagari": "नासिक", "language": "hi"},
        {"roman": "swiggy", "devanagari": "स्वीगी", "language": "mr"},
        {"roman": "swiggy", "devanagari": "स्विगी", "language": "hi"},
        {"roman": "zomato", "devanagari": "झोमॅटो", "language": "mr"},
        {"roman": "zomato", "devanagari": "जोमैटो", "language": "hi"},
    ]
    for sp in seed_pairs:
        for _ in range(15):
            train_pairs.append(sp)

    # 2. Process Marathi Aksharantar data
    mar_train_path = raw_dir / "mar_train.json"
    mar_val_path = raw_dir / "mar_valid.json"

    if mar_train_path.exists():
        print(f"[*] Reading Marathi training data from {mar_train_path}...")
        with open(mar_train_path, "r", encoding="utf-8") as f:
            count = 0
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    eng = obj.get("english word", "").strip().lower()
                    native = obj.get("native word", "").strip()
                    if eng and native and len(eng) <= 25 and len(native) <= 25:
                        if all(c.isascii() and (c.isalpha() or c in " -'") for c in eng):
                            key = (eng, native, "mr")
                            if key not in seen:
                                seen.add(key)
                                train_pairs.append({"roman": eng, "devanagari": native, "language": "mr"})
                                count += 1
                                if count >= max_train_samples // 2:
                                    break
                except Exception:
                    continue
        print(f"[*] Loaded {count} Marathi training pairs.")

    if mar_val_path.exists():
        with open(mar_val_path, "r", encoding="utf-8") as f:
            count = 0
            for line in f:
                try:
                    obj = json.loads(line)
                    eng = obj.get("english word", "").strip().lower()
                    native = obj.get("native word", "").strip()
                    if eng and native and len(eng) <= 25:
                        val_pairs.append({"roman": eng, "devanagari": native, "language": "mr"})
                        count += 1
                        if count >= max_val_samples // 2:
                            break
                except Exception:
                    continue
        print(f"[*] Loaded {count} Marathi validation pairs.")

    # 3. Process Hindi Aksharantar data
    hin_train_path = raw_dir / "hin_train.json"
    hin_val_path = raw_dir / "hin_valid.json"

    if hin_train_path.exists():
        print(f"[*] Reading Hindi training data from {hin_train_path}...")
        with open(hin_train_path, "r", encoding="utf-8") as f:
            count = 0
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    eng = obj.get("english word", "").strip().lower()
                    native = obj.get("native word", "").strip()
                    if eng and native and len(eng) <= 25 and len(native) <= 25:
                        if all(c.isascii() and (c.isalpha() or c in " -'") for c in eng):
                            key = (eng, native, "hi")
                            if key not in seen:
                                seen.add(key)
                                train_pairs.append({"roman": eng, "devanagari": native, "language": "hi"})
                                count += 1
                                if count >= max_train_samples // 2:
                                    break
                except Exception:
                    continue
        print(f"[*] Loaded {count} Hindi training pairs.")

    if hin_val_path.exists():
        with open(hin_val_path, "r", encoding="utf-8") as f:
            count = 0
            for line in f:
                try:
                    obj = json.loads(line)
                    eng = obj.get("english word", "").strip().lower()
                    native = obj.get("native word", "").strip()
                    if eng and native and len(eng) <= 25:
                        val_pairs.append({"roman": eng, "devanagari": native, "language": "hi"})
                        count += 1
                        if count >= max_val_samples // 2:
                            break
                except Exception:
                    continue
        print(f"[*] Loaded {count} Hindi validation pairs.")

    random.seed(42)
    random.shuffle(train_pairs)
    random.shuffle(val_pairs)

    print(f"[*] Writing {len(train_pairs)} training records to {train_out}...")
    with open(train_out, "w", encoding="utf-8") as f:
        for p in train_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"[*] Writing {len(val_pairs)} validation records to {val_out}...")
    with open(val_out, "w", encoding="utf-8") as f:
        for p in val_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print("[*] Aksharantar & conversational preprocessing completed successfully!")

if __name__ == "__main__":
    prepare_data()
