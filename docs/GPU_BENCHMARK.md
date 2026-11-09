# GPU translation evaluation

The translation adapter automatically uses CUDA when PyTorch can access a compatible NVIDIA GPU. It uses float16 weights on CUDA and float32 by default on CPU. The benchmark records actual precision, device, GPU name, PyTorch version and CUDA runtime; CPU and GPU results are kept in separate directories.

The same 96-example diagnostic took 1,044.7 seconds on CPU and 49.3 seconds on the RTX 4050: approximately 21.2 times faster for inference, excluding model loading and corpus auditing. Both runs used four-example batches and four CPU threads; GPU inference also changed precision from float32 to float16. These timings describe this sample and machine, not a general speed guarantee. All six GPU diagnostic directions completed with zero inference failures. Reports are in [`ml/evaluation/gpu-diagnostic/`](../ml/evaluation/gpu-diagnostic/).

## Local setup

Hardware checked on 9 November 2026: NVIDIA GeForce RTX 4050 Laptop GPU, 6 GB VRAM, driver 592.82. The previous PyTorch package was CPU-only. Install the matching official CUDA build in the project environment while the backend is stopped:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade "torch==2.14.1+cu130" --index-url https://download.pytorch.org/whl/cu130
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

This command is specific to the verified local driver and Python environment. For another machine, select a compatible build using the [official PyTorch installer](https://pytorch.org/get-started/locally/). Installing a CUDA wheel alone does not provide an NVIDIA GPU or its driver.

## Reproduce

First time the same 16-row diagnostic used for the CPU investigation:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_expanded_translation.py --all-pairs --offline --require-device cuda --limit 16 --batch-size 4 --threads 4 --output-dir ml/evaluation/gpu-diagnostic
.\.venv\Scripts\python.exe scripts/finalize_translation_reports.py ml/evaluation/gpu-diagnostic
```

Then evaluate all 1,012 frozen sentences in each of six directions:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_expanded_translation.py --all-pairs --offline --require-device cuda --batch-size 32 --threads 4 --output-dir ml/evaluation/expanded-gpu
.\.venv\Scripts\python.exe scripts/finalize_translation_reports.py ml/evaluation/expanded-gpu
```

The full run makes 6,072 native-script translations. It uses cached model weights and no Gemini calls. Keep the computer awake and connected to power during long runs. Progress is saved after each batch; rerun the same command to resume compatible reports. The finalizer requires all directions, matching configurations, complete example coverage, the frozen corpus checksum and matching source/reference text before writing a summary. If GPU memory is insufficient, use a smaller batch size.

`--require-device cuda` prevents a silent CPU run. `--precision` selects CPU precision only; the CUDA adapter selects float16. The previous CPU diagnostic used float32, so timing comparisons also include the precision change. A faster device does not establish better translation quality, and floating-point differences can change predictions.

## Evaluation scope

BLEU and chrF++ measure similarity to held-out FLORES references. Reviewed-memory overrides, Roman input, grammar explanations and generated English meanings are outside this benchmark. The first 16 rows were previously inspected during debugging; results over the full split include those rows and are not a newly untouched test. Upstream pretrained-model exposure to FLORES is unknown. Bilingual review is still needed for semantic errors.

## Completed full run

All 6,072 cases were evaluated with 1 inference failure in 28.6 minutes including startup, corpus audit and report finalization. See [the score table and evaluation limits](TRANSLATION_EVALUATION.md) and [machine-readable full results](../ml/evaluation/expanded-gpu/summary.json).
