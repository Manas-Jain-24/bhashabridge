"""Audit expanded corpus hashes, duplicates, and cross-split source overlap."""
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.translation.corpus import normalize_source


def read(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def audit(root=ROOT):
    base = root / "data/processed/expanded"
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["sha256"].items():
        # Manifests written on Windows can be audited on Linux too.
        path = root / name.replace("\\", "/")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Dataset checksum changed: " + name)
    rows = {split: read(base / f"transliteration/{split}.jsonl") for split in ("train", "validation", "test")}
    def native(rs): return {(r["language"], normalize_source(r["native"])) for r in rs}
    def roman(rs): return {(r["language"], normalize_source(a)) for r in rs for a in r.get("aliases", [r["roman"]])}
    heldout = rows["validation"] + rows["test"]
    native_overlap = len(native(rows["train"]) & native(heldout))
    roman_overlap = len(roman(rows["train"]) & roman(heldout))
    triples = [(r["language"], normalize_source(r["native"]), normalize_source(r["roman"])) for r in rows["train"]]
    duplicate_train = len(triples) - len(set(triples))
    lexical = read(base / "lexicon.jsonl")
    lexical_overlap = len(native(lexical) & native(heldout)) + len(roman(lexical) & roman(heldout))
    teaching = read(base / "translation/teaching.jsonl")
    test = read(base / "translation/test.jsonl")
    def sources(rs): return {(lang, normalize_source(text)) for r in rs for lang, text in r["sentences"].items()}
    translation_overlap = len(sources(teaching) & sources(test))
    directed = read(base / "translation/train.jsonl")
    directed_sources = {(r["source_language"], normalize_source(r["source_text"])) for r in directed}
    directed_sources.update((r["target_language"], normalize_source(r["target_text"])) for r in directed)
    directed_overlap = len(directed_sources & sources(test))
    report = {"transliteration_train_pairs": len(triples), "duplicate_train_pairs": duplicate_train,
              "train_heldout_native_overlap": native_overlap, "train_heldout_roman_overlap": roman_overlap,
              "game_lexicon_heldout_overlap": lexical_overlap, "translation_teaching_rows": len(teaching),
              "translation_test_rows": len(test), "translation_source_overlap": translation_overlap, "directional_training_pairs": len(directed),
              "directional_test_overlap": directed_overlap,
              "hashes_verified": len(manifest["sha256"])}
    if any((duplicate_train, native_overlap, roman_overlap, lexical_overlap, translation_overlap, directed_overlap)):
        raise ValueError("Expanded corpus audit failed: " + json.dumps(report))
    return report

if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
