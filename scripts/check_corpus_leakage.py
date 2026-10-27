"""Fail if normalized held-out sources are available to the runtime translator."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.translation.corpus import heldout_sources, sources


def audit():
    forbidden_hi, forbidden_mr = heldout_sources()
    files = [ROOT / "data/processed/learning/external_parallel_learning_index.json",
             ROOT / "data/processed/translation/hindi_marathi.jsonl"]
    counts = {}
    for path in files:
        data = path.read_text(encoding="utf-8")
        pairs = json.loads(data) if path.suffix == ".json" else [json.loads(x) for x in data.splitlines() if x.strip()]
        overlap = sum(sources(p)[0] in forbidden_hi or sources(p)[1] in forbidden_mr for p in pairs)
        counts[str(path.relative_to(ROOT))] = {"pairs": len(pairs), "overlapping_sources": overlap}
    from app.services.translation.translator import modular_translator
    counts["effective_runtime_lookup"] = {
        "pairs": len(modular_translator._runtime_pairs),
        "overlapping_sources": sum(sources(p)[0] in forbidden_hi or sources(p)[1] in forbidden_mr
                                   for p in modular_translator._runtime_pairs)}
    return counts


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, indent=2))
    sys.exit(1 if any(x["overlapping_sources"] for x in result.values()) else 0)
