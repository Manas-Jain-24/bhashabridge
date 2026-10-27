"""Keep held-out source sentences out of every runtime retrieval index."""
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def normalize_source(text):
    return " ".join(''.join(c if unicodedata.category(c)[0] in "LMN" else ' '
                           for c in unicodedata.normalize("NFC", text).lower()).split())


def sources(pair):
    return (normalize_source(pair.get("hindi", pair.get("hindi_dev", pair.get("hindi_devanagari", "")))),
            normalize_source(pair.get("marathi", pair.get("marathi_dev", pair.get("marathi_devanagari", "")))))


def heldout_sources(root=ROOT):
    test = Path(root) / "data/processed/translation/test.jsonl"
    pairs = [json.loads(line) for line in test.read_text(encoding="utf-8").splitlines() if line.strip()] if test.exists() else []
    return ({sources(p)[0] for p in pairs}, {sources(p)[1] for p in pairs})


def exclude_heldout(pairs, forbidden=None):
    hi, mr = forbidden if forbidden is not None else heldout_sources()
    return [p for p in pairs if sources(p)[0] not in hi and sources(p)[1] not in mr]
