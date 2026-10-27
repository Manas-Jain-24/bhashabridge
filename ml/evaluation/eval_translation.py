"""Reproducible corpus evaluation with an explicit engine and leakage checks."""
import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))


def evaluate(engine="modular"):
    # Default evaluation is offline. Neural evaluation is explicitly requested.
    if engine == "modular":
        os.environ["USE_MOCK_MODELS"] = "true"
    from sacrebleu.metrics import BLEU, CHRF
    from check_corpus_leakage import audit
    from app.services.translation.translator import modular_translator
    from app.services.translation.corpus import normalize_source
    leakage = audit()
    if any(x["overlapping_sources"] for x in leakage.values()):
        raise RuntimeError("Corpus leakage detected. Rebuild the runtime/training indexes first.")
    if engine == "indictrans2":
        from app.services.translation.indictrans2 import indictrans2_adapter
        translator = indictrans2_adapter
    else:
        translator = modular_translator
    test_file = ROOT / "data/processed/translation/test.jsonl"
    pairs = [json.loads(x) for x in test_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    if not pairs:
        raise ValueError("The evaluation corpus is empty.")
    summary, samples = {}, {}
    engines = Counter()
    signatures = {}
    for source, target in [("hindi", "marathi"), ("marathi", "hindi")]:
        predictions, references, rows = [], [], []
        for pair in pairs:
            result = translator.translate(pair[source], source_language=source, target_language=target, script="devanagari")
            prediction = result["translation_native"]
            predictions.append(prediction)
            references.append(pair[target])
            engines[result.get("engine", result.get("model_source", "unknown"))] += 1
            rows.append({"source": pair[source], "reference": pair[target], "prediction": prediction})
        bleu = BLEU(tokenize="intl")
        chrf = CHRF(word_order=2)
        key = f"{source}_to_{target}"
        summary[key] = {
            "corpus_bleu": round(bleu.corpus_score(predictions, [references]).score, 2),
            "corpus_chrf_plus_plus": round(chrf.corpus_score(predictions, [references]).score, 2),
            "exact_match_rate_pct": round(100 * sum(normalize_source(a) == normalize_source(b)
                                                    for a, b in zip(predictions, references)) / len(pairs), 2)}
        signatures[key] = {"bleu": str(bleu.get_signature()), "chrf_plus_plus": str(chrf.get_signature())}
        samples[key] = rows[:10]
    report = {
        "evaluation_name": "BhashaBridge leakage-checked translation evaluation",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_engine": engine,
        "engine_breakdown": dict(engines),
        "test_dataset": str(test_file.relative_to(ROOT)),
        "test_sha256": hashlib.sha256(test_file.read_bytes()).hexdigest(),
        "total_test_samples": len(pairs),
        "leakage_audit": leakage,
        "metric_signatures": signatures,
        "metrics_summary": summary,
        "limitations": ["External parallel references contain suspected misalignments and require human review.",
                        "This frozen benchmark is diagnostic; it does not establish conversational teaching quality.",
                        "Earlier reports with runtime lookup overlap are invalid for unseen-sentence quality."],
        "sample_evaluations": samples,
    }
    output = ROOT / "ml/evaluation/translation_eval_report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Report: {output}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=["modular", "indictrans2"], default="modular")
    evaluate(parser.parse_args().engine)
