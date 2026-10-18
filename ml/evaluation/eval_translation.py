"""
BhashaBridge — Machine Translation Evaluation Suite (M3)
Evaluates Hindi <-> Marathi translation models against held-out test corpora
(data/processed/translation/test.jsonl) using BLEU, chrF++, and Exact Match metrics.
Outputs report to: ml/evaluation/translation_eval_report.json
"""

import os
import sys
import json
import math
from collections import Counter
from pathlib import Path

# Add backend directory to sys.path so app services can be imported directly
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.services.translation.service import translation_service

TEST_FILE = BASE_DIR / "data" / "processed" / "translation" / "test.jsonl"
OUTPUT_REPORT = BASE_DIR / "ml" / "evaluation" / "translation_eval_report.json"

def calculate_ngram_counts(tokens, n):
    if len(tokens) < n:
        return Counter()
    return Counter([tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)])

def compute_bleu(candidate_tokens, reference_tokens, max_n=4):
    """
    Computes standard sentence-level BLEU with add-1 smoothing and brevity penalty.
    """
    c_len = len(candidate_tokens)
    r_len = len(reference_tokens)
    if c_len == 0:
        return 0.0

    bp = 1.0 if c_len > r_len else math.exp(1.0 - (r_len / max(1, c_len)))

    precisions = []
    for n in range(1, max_n + 1):
        cand_ngrams = calculate_ngram_counts(candidate_tokens, n)
        ref_ngrams = calculate_ngram_counts(reference_tokens, n)

        clipped_count = sum(min(count, ref_ngrams.get(ngram, 0)) for ngram, count in cand_ngrams.items())
        total_count = max(1, sum(cand_ngrams.values()))
        precisions.append((clipped_count + 1) / (total_count + 1))

    geom_mean = math.exp(sum(math.log(p) for p in precisions) / max_n)
    return round(bp * geom_mean * 100, 2)

def compute_chrf(candidate: str, reference: str, char_order: int = 6, beta: float = 2.0):
    """
    Computes character n-gram F-score (chrF), the gold standard for Indic morphology.
    """
    cand_chars = list(candidate.replace(" ", ""))
    ref_chars = list(reference.replace(" ", ""))

    if not cand_chars or not ref_chars:
        return 0.0

    precisions = []
    recalls = []

    for n in range(1, char_order + 1):
        cand_ngrams = calculate_ngram_counts(cand_chars, n)
        ref_ngrams = calculate_ngram_counts(ref_chars, n)

        overlap = sum(min(count, ref_ngrams.get(ngram, 0)) for ngram, count in cand_ngrams.items())
        cand_total = sum(cand_ngrams.values())
        ref_total = sum(ref_ngrams.values())

        p = (overlap / cand_total) if cand_total > 0 else 0.0
        r = (overlap / ref_total) if ref_total > 0 else 0.0
        precisions.append(p)
        recalls.append(r)

    avg_p = sum(precisions) / char_order
    avg_r = sum(recalls) / char_order

    if avg_p + avg_r == 0:
        return 0.0

    beta_sq = beta ** 2
    f_score = ((1 + beta_sq) * avg_p * avg_r) / (beta_sq * avg_p + avg_r)
    return round(f_score * 100, 2)

def evaluate():
    if not TEST_FILE.exists():
        print(f"Error: Test file not found at {TEST_FILE}")
        return

    test_pairs = []
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                test_pairs.append(json.loads(line))

    print(f"Evaluating {len(test_pairs)} test pairs in both directions...")

    # Direction 1: Hindi -> Marathi
    hi_to_mr_results = []
    mr_to_hi_results = []

    for item in test_pairs:
        hi_src = item["hindi"]
        mr_ref = item["marathi"]

        # 1. Translate Hindi -> Marathi
        tr_out = translation_service.translate(hi_src, source_language="hindi", target_language="marathi", script="devanagari")
        mr_pred = tr_out.get("translation_native", tr_out.get("translation", ""))

        clean_pred = mr_pred.strip().replace("।", "").replace(".", "")
        clean_ref = mr_ref.strip().replace("।", "").replace(".", "")

        bleu_score = compute_bleu(clean_pred.split(), clean_ref.split())
        chrf_score = compute_chrf(clean_pred, clean_ref)
        is_exact = clean_pred == clean_ref

        hi_to_mr_results.append({
            "source": hi_src,
            "reference": mr_ref,
            "prediction": mr_pred,
            "bleu": bleu_score,
            "chrf": chrf_score,
            "exact_match": is_exact
        })

        # 2. Reverse Translate Marathi -> Hindi
        tr_rev = translation_service.translate(mr_ref, source_language="marathi", target_language="hindi", script="devanagari")
        hi_pred = tr_rev.get("translation_native", tr_rev.get("translation", ""))

        clean_rev_pred = hi_pred.strip().replace("।", "").replace(".", "")
        clean_rev_ref = hi_src.strip().replace("।", "").replace(".", "")

        bleu_rev = compute_bleu(clean_rev_pred.split(), clean_rev_ref.split())
        chrf_rev = compute_chrf(clean_rev_pred, clean_rev_ref)
        is_rev_exact = clean_rev_pred == clean_rev_ref

        mr_to_hi_results.append({
            "source": mr_ref,
            "reference": hi_src,
            "prediction": hi_pred,
            "bleu": bleu_rev,
            "chrf": chrf_rev,
            "exact_match": is_rev_exact
        })

    # Summary statistics
    avg_bleu_hi_mr = round(sum(r["bleu"] for r in hi_to_mr_results) / len(hi_to_mr_results), 2)
    avg_chrf_hi_mr = round(sum(r["chrf"] for r in hi_to_mr_results) / len(hi_to_mr_results), 2)
    exact_rate_hi_mr = round(sum(1 for r in hi_to_mr_results if r["exact_match"]) / len(hi_to_mr_results) * 100, 2)

    avg_bleu_mr_hi = round(sum(r["bleu"] for r in mr_to_hi_results) / len(mr_to_hi_results), 2)
    avg_chrf_mr_hi = round(sum(r["chrf"] for r in mr_to_hi_results) / len(mr_to_hi_results), 2)
    exact_rate_mr_hi = round(sum(1 for r in mr_to_hi_results if r["exact_match"]) / len(mr_to_hi_results) * 100, 2)

    overall_report = {
        "evaluation_name": "IndicTrans2 Translation Evaluation Suite",
        "test_dataset": str(TEST_FILE.relative_to(BASE_DIR)),
        "total_test_samples": len(test_pairs),
        "metrics_summary": {
            "hindi_to_marathi": {
                "avg_bleu": avg_bleu_hi_mr,
                "avg_chrf": avg_chrf_hi_mr,
                "exact_match_rate_pct": exact_rate_hi_mr
            },
            "marathi_to_hindi": {
                "avg_bleu": avg_bleu_mr_hi,
                "avg_chrf": avg_chrf_mr_hi,
                "exact_match_rate_pct": exact_rate_mr_hi
            },
            "aggregate": {
                "mean_bleu": round((avg_bleu_hi_mr + avg_bleu_mr_hi) / 2, 2),
                "mean_chrf": round((avg_chrf_hi_mr + avg_chrf_mr_hi) / 2, 2)
            }
        },
        "sample_evaluations": {
            "hindi_to_marathi_samples": hi_to_mr_results[:5],
            "marathi_to_hindi_samples": mr_to_hi_results[:5]
        }
    }

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(overall_report, f, ensure_ascii=False, indent=2)

    print("\n=== Translation Evaluation Results ===")
    print(f"Hindi -> Marathi: chrF++ = {avg_chrf_hi_mr} | BLEU = {avg_bleu_hi_mr} | Exact = {exact_rate_hi_mr}%")
    print(f"Marathi -> Hindi: chrF++ = {avg_chrf_mr_hi} | BLEU = {avg_bleu_mr_hi} | Exact = {exact_rate_mr_hi}%")
    print(f"Full report exported to: {OUTPUT_REPORT}")

if __name__ == "__main__":
    evaluate()
