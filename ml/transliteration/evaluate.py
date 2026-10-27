"""
BhashaBridge — ML Transliteration Evaluation Script (M7)
Computes CER (Character Error Rate), WER (Word Error Rate), and Exact Match on the test split.
Generates structured eval report json artifact.
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple
import torch

from dataset import CharVocab, TransliterationDataset, PAD_IDX, SOS_IDX, EOS_IDX
from model import Encoder, Decoder, Seq2Seq

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def evaluate_transliteration(
    checkpoint_path: str = None,
    vocab_path: str = None,
    test_file_path: str = None
) -> Dict:
    base_dir = Path(__file__).resolve().parent
    root_dir = base_dir.parent.parent

    if checkpoint_path is None:
        checkpoint_path = base_dir / "weights" / "seq2seq_translit.pt"
    if vocab_path is None:
        vocab_path = base_dir / "vocab.json"
    if test_file_path is None:
        test_file_path = root_dir / "data" / "processed" / "transliteration" / "test.jsonl"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load Vocabs
    with open(vocab_path, "r", encoding="utf-8") as f:
        vocab_data = json.load(f)
    src_vocab = CharVocab.from_dict(vocab_data["src_vocab"])
    tgt_vocab = CharVocab.from_dict(vocab_data["tgt_vocab"])

    # Load Model Checkpoint
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    hp = checkpoint.get("hyperparams", {})
    emb_dim = hp.get("emb_dim", 64)
    enc_hid_dim = hp.get("enc_hid_dim", 96)
    dec_hid_dim = hp.get("dec_hid_dim", 96)

    enc = Encoder(len(src_vocab), emb_dim, enc_hid_dim, dec_hid_dim, dropout=0.0)
    dec = Decoder(len(tgt_vocab), emb_dim, enc_hid_dim, dec_hid_dim, dropout=0.0)
    model = Seq2Seq(enc, dec, pad_idx=PAD_IDX).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    # Load Test Set
    test_ds = TransliterationDataset(str(test_file_path), src_vocab=src_vocab, tgt_vocab=tgt_vocab)

    # Load Test raw records to extract language labels
    lang_labels = []
    if Path(test_file_path).exists():
        with open(test_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        obj = json.loads(line)
                        lang_labels.append(obj.get("language", "unknown"))
                    except Exception:
                        lang_labels.append("unknown")

    total_char_dist = 0
    total_ref_chars = 0
    exact_matches = 0
    results: List[Dict] = []

    # Per language accumulators
    lang_metrics = {
        "hi": {"char_dist": 0, "ref_chars": 0, "exact": 0, "total": 0},
        "mr": {"char_dist": 0, "ref_chars": 0, "exact": 0, "total": 0}
    }

    for idx in range(len(test_ds)):
        src_enc, tgt_enc, src_raw, tgt_raw = test_ds[idx]
        src_tensor = src_enc.unsqueeze(0).to(device)

        pred_tokens = model.predict(src_tensor, max_len=30, sos_idx=SOS_IDX, eos_idx=EOS_IDX)[0].tolist()
        pred_str = tgt_vocab.decode(pred_tokens, strip_special=True)

        dist = levenshtein_distance(tgt_raw, pred_str)
        total_char_dist += dist
        total_ref_chars += max(1, len(tgt_raw))
        is_exact = (tgt_raw == pred_str)
        if is_exact:
            exact_matches += 1

        cur_lang = lang_labels[idx] if idx < len(lang_labels) else "unknown"
        if cur_lang in lang_metrics:
            lang_metrics[cur_lang]["char_dist"] += dist
            lang_metrics[cur_lang]["ref_chars"] += max(1, len(tgt_raw))
            lang_metrics[cur_lang]["total"] += 1
            if is_exact:
                lang_metrics[cur_lang]["exact"] += 1

        results.append({
            "language": cur_lang,
            "input_roman": src_raw,
            "expected_devanagari": tgt_raw,
            "predicted_devanagari": pred_str,
            "exact_match": is_exact,
            "edit_distance": dist,
            "char_len": len(tgt_raw)
        })

    cer = round((total_char_dist / max(1, total_ref_chars)) * 100, 2)
    em_acc = round((exact_matches / max(1, len(test_ds))) * 100, 2)
    wer = round(100.0 - em_acc, 2)

    per_lang_summary = {}
    for l_key, l_data in lang_metrics.items():
        if l_data["total"] > 0:
            l_em = round((l_data["exact"] / l_data["total"]) * 100, 2)
            per_lang_summary[l_key] = {
                "samples": l_data["total"],
                "cer": round((l_data["char_dist"] / max(1, l_data["ref_chars"])) * 100, 2),
                "exact_match_pct": l_em,
                "wer": round(100.0 - l_em, 2)
            }

    report = {
        "model": "CharSeq2Seq-BahdanauAttention",
        "checkpoint_path": str(checkpoint_path),
        "vocab_path": str(vocab_path),
        "test_file_path": str(test_file_path),
        "parameters": sum(p.numel() for p in model.parameters()),
        "test_examples": len(test_ds),
        "metrics": {
            "character_error_rate_cer": cer,
            "word_error_rate_wer": wer,
            "exact_match_accuracy": em_acc,
            "total_character_edits": total_char_dist,
            "total_reference_characters": total_ref_chars
        },
        "per_language_metrics": per_lang_summary,
        "sample_predictions": results[:10]
    }

    report_path = base_dir / "eval_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n================ M7 Transliteration Evaluation ================")
    print(f"Total Test Words       : {len(test_ds)}")
    print(f"Character Error Rate   : {cer}% (CER)")
    print(f"Word Error Rate        : {wer}% (WER)")
    print(f"Exact Match Accuracy   : {em_acc}%")
    for l_key, l_res in per_lang_summary.items():
        print(f"  - {l_key.upper()} ({l_res['samples']} words): Exact Match = {l_res['exact_match_pct']}% | CER = {l_res['cer']}%")
    print(f"Report saved to        : {report_path}")
    print("===============================================================\n")

    return report

if __name__ == "__main__":
    evaluate_transliteration()
