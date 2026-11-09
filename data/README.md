# BhashaBridge data

The current multilingual expansion lives in `processed/expanded/`. It is separate from the older course and benchmark files so those references remain reproducible. `dataset_stats.json` contains both legacy and expanded counts; `processed/expanded/manifest.json` records processed and raw SHA-256 hashes and exact source URLs.

| Expanded collection | Contents |
| --- | --- |
| Transliteration training | Deduplicated legacy training pairs plus official Dakshina training annotations for Hindi, Marathi and Bengali; native words and Roman sources appearing in held-out splits are removed. |
| Transliteration validation/test | Official Dakshina dev/test word groups; all attested Roman aliases retained. |
| Spelling lexicon | Training-only native words with attested Roman variants and annotation counts. These are not English dictionary definitions. |
| Translation teaching | 997 aligned FLORES-200 dev rows, each containing English, Hindi, Marathi and Bengali. |
| Translation training | Six directed Indic-language pairs per teaching row (5,982 records representing 997 aligned source rows, not 5,982 independent examples). |
| Translation benchmark | 1,012 aligned FLORES-200 devtest rows. These are excluded from games, lexicon retrieval and translation teaching. |

Sources and attribution:

- **Google Research Dakshina v1.0**, Roark et al., *Processing South Asian Languages Written in the Latin Script: the Dakshina Dataset* (LREC 2020). [Official source](https://github.com/google-research-datasets/dakshina), [paper](https://aclanthology.org/2020.lrec-1.294/). The **data license is CC BY-SA 4.0**, not Apache 2.0. This project selects Hindi, Marathi and Bengali lexicons, normalizes and filters records, merges training data, and preserves official dev/test separation.
- **Meta/Facebook FLORES-200**. [Official source and citation information](https://github.com/facebookresearch/flores/tree/main/flores200). Data is **CC BY-SA 4.0**. This project selects four languages by aligned line number and derives teaching/game items and directed Indic-language pairs. FLORES dev is now used as teaching/training material here; never report it as an unseen benchmark.
- New source-derived records and data adaptations retain the [CC BY-SA 4.0 terms](https://creativecommons.org/licenses/by-sa/4.0/) and source attribution. Legacy records in the merged training file retain their original source metadata where present; unknown legacy provenance is labelled `legacy_project_corpus`, rather than falsely attributed to a new source.

```powershell
.\.venv\Scripts\python.exe scripts/expand_datasets.py
.\.venv\Scripts\python.exe scripts/expand_datasets.py --offline
.\.venv\Scripts\python.exe scripts/check_expanded_data.py
.\.venv\Scripts\python.exe scripts/dataset_stats.py
```

The downloader uses bounded byte ranges to read the nine required lexicon files from Google's uncompressed 2 GB tar archive, and downloads the approximately 26 MB FLORES archive. It reads selected members without extracting arbitrary archive paths. Raw files stay under ignored `data/raw/expanded/`.

The older `processed/learning` set has 360 project-authored examples, and the older translation set has 1,242 training and 219 diagnostic test pairs with known alignment concerns. Importing additional data does not establish an accuracy score. A subsequent Bengali character-model training/evaluation run is documented separately in its [model card](../ml/models/bengali-v1/MODEL_CARD.md). The previously contaminated high-BLEU report remains invalid for unseen quality.

`lessons/starter_vocabulary.json` contains 36 authored starter words for each of the three languages. `lessons/bengali_starter.json` contains six units with 24 phrases. Four greeting phrases are source-checked against the cited Bhasha Sangam booklet; the rest are editorial drafts awaiting native-speaker review. These files are teaching material, not held-out benchmark data, dictionary definitions or automatically approved translation-memory records. The corpus overlap audit covers the expanded corpus files; authored starter lessons are separately labelled and are not used to train or evaluate the Bengali model.
