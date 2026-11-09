# Bengali transliteration v1 (experimental)

This is a character-level Roman-to-Bengali word model trained from scratch on the expanded Google Dakshina training split. It is a spelling aid, not a translator or pronunciation assessor.

## Measured results

| Split | Native-word groups | Previous dictionary/phonetic fallback exact match | Neural exact match | Previous CER | Neural CER |
|---|---:|---:|---:|---:|---:|
| Validation | 2,500 | 9.16% | 35.68% | 37.12% | 17.71% |
| Test | 2,500 | 9.84% | 36.92% | 36.37% | 17.82% |

Each group is evaluated using its preferred Roman annotation. Other accepted aliases are not scored here. CER is edit distance over Unicode codepoints after NFC normalization, divided by reference length; it is not grapheme or acoustic error rate. The baseline includes the existing common-word mappings and training-only lexical lookup. These figures describe held-out words, not general sentence accuracy.

The best checkpoint was selected by validation loss. Deployment requires the full validation comparison to improve both exact match and CER, with matching model/vocabulary/data hashes. The independent test split was scored after freezing that checkpoint; it does not choose the model. Absolute accuracy remains limited, so the feature remains experimental.

## Training and artifacts

- 90,293 Bengali training pairs; 2,500 validation word groups; no native-word or normalized Roman-source overlap across the expanded training/held-out splits.
- Bidirectional GRU encoder with packed sequences, Bahdanau attention, GRU decoder; 64-dimensional embeddings, 128-dimensional hidden states, 438,335 trainable parameters.
- CPU-only PyTorch 2.14.1, seed 42, Adam at 0.003, batch size 256, two threads, teacher forcing 0.5, dropout 0.15.
- Three full epochs completed (about 15 minutes). The requested eight-epoch run ran out of system memory during epoch four while a second model job was active. Epoch-three weights were saved before interruption; no partially updated weights were exported.
- `inference.pt` contains only inference weights and architecture metadata (about 1.76 MB); `vocab.json` contains character mappings; `promotion.json` records validation results and SHA-256 hashes.
- Full training history and the two evaluation reports are in `ml/experiments/bengali-v1/`.

Runtime order is common phrases/words → unambiguous training lexicon → this model for unseen ASCII Roman words of 2–32 letters → phonetic rules. Reverse Bengali-to-Roman conversion remains lexical/phonetic. The model is lazy and optional: missing PyTorch, disabled configuration, failed checksums or failed inference leave the phonetic fallback available. `BENGALI_NEURAL_TRANSLITERATION=false` disables it. Test/mock mode never loads it.

## Reproduce

```powershell
.\.venv\Scripts\python.exe ml/transliteration/train.py --data-dir data/processed/expanded/transliteration --language bengali --output-dir ml/experiments/bengali-reproduction --epochs 3 --batch-size 256 --hidden-dim 128 --embedding-dim 64 --threads 2 --seed 42
.\.venv\Scripts\python.exe scripts/evaluate_bengali_transliteration.py --model-dir ml/experiments/bengali-reproduction --split validation
.\.venv\Scripts\python.exe scripts/evaluate_bengali_transliteration.py --model-dir ml/experiments/bengali-reproduction --split test
```

Training data and derived weights: **CC BY-SA 4.0**. Attribution: [Google Dakshina v1.0](https://github.com/google-research-datasets/dakshina), and [the project data documentation](../../../data/README.md). No upstream IndicTrans2 weights are included in this artifact.
