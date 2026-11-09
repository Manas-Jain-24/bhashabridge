"""Unambiguous attested spellings from the training-only expanded lexicon."""
import json
import unicodedata
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def indexes():
    path = Path(__file__).resolve().parents[4] / "data/processed/expanded/lexicon.jsonl"
    roman = {}; native = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            for alias in row["aliases"]:
                roman.setdefault((row["language"], alias.lower()), set()).add(row["native"])
            native[(row["language"], row["native"])] = row["roman"]
    return {key: next(iter(values)) for key, values in roman.items() if len(values) == 1}, native

def lookup(word, language, direction):
    roman, native = indexes()
    key = unicodedata.normalize("NFC", word)
    return roman.get((language, key.lower())) if direction == "latin_to_devanagari" else native.get((language, key))
