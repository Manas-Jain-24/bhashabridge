"""
BhashaBridge — ML Transliteration Model Training Script (M7)
Trains a character-level Seq2Seq Attention model on the transliteration corpus.
Saves model checkpoint and vocabulary for inference and CER/WER evaluation.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

import os
import json
import time
import random
import hashlib
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from dataset import TransliterationDataset, collate_fn, PAD_IDX, SOS_IDX, EOS_IDX
from model import Encoder, Decoder, Seq2Seq

def train_transliteration_model(
    epochs: int = 10,
    batch_size: int = 512,
    lr: float = 0.003,
    device_name: str = "auto",
    data_dir: str = None,
    output_dir: str = None,
    language: str = None,
    threads: int = 2,
    hidden_dim: int = 128,
    embedding_dim: int = 64,
    seed: int = 42,
    patience: int = 3
):
    base_dir = Path(__file__).resolve().parent
    root_dir = base_dir.parent.parent
    if min(epochs,batch_size,threads,hidden_dim,embedding_dim,patience)<=0 or lr<=0:
        raise ValueError('Epochs, batch size, threads, dimensions, patience and learning rate must be positive')
    if data_dir and (not output_dir or not language):
        raise ValueError("Expanded data requires --language and a separate --output-dir; existing models must not be overwritten.")
    corpus_dir = Path(data_dir) if data_dir else root_dir / "data/processed/transliteration"
    artifact_dir = Path(output_dir) if output_dir else base_dir
    if data_dir and artifact_dir.resolve()==base_dir.resolve():
        raise ValueError('Expanded training must use a separate output directory')
    artifact_dir.mkdir(parents=True, exist_ok=True)
    train_file, val_file = corpus_dir / "train.jsonl", corpus_dir / "validation.jsonl"
    weights_dir = artifact_dir / "weights"
    weights_dir.mkdir(exist_ok=True)
    vocab_file = artifact_dir / "vocab.json"
    torch.set_num_threads(threads)
    random.seed(seed); torch.manual_seed(seed)

    if device_name == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(device_name)
    print(f"[*] Training on device: {device}")

    # 1. Build dataset and vocabularies
    train_ds = TransliterationDataset(str(train_file), build_vocab=True, language=language)
    val_ds = TransliterationDataset(str(val_file), src_vocab=train_ds.src_vocab, tgt_vocab=train_ds.tgt_vocab, language=language)

    if not len(train_ds) or not len(val_ds):
        raise ValueError("Training and validation must both contain examples for this language.")
    src_vocab = train_ds.src_vocab
    tgt_vocab = train_ds.tgt_vocab

    print(f"[*] Vocabularies initialized: Source chars={len(src_vocab)}, Target chars={len(tgt_vocab)}")
    print(f"[*] Dataset sizes: Train={len(train_ds)}, Val={len(val_ds)}")

    # Save vocab
    with open(vocab_file, "w", encoding="utf-8") as f:
        json.dump({
            "src_vocab": src_vocab.to_dict(),
            "tgt_vocab": tgt_vocab.to_dict()
        }, f, ensure_ascii=False, indent=2)
    print(f"[*] Vocabulary serialized to {vocab_file}")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)

    # 2. Model Hyperparameters
    emb_dim = embedding_dim
    enc_hid_dim = hidden_dim
    dec_hid_dim = hidden_dim
    dropout = 0.15

    enc = Encoder(len(src_vocab), emb_dim, enc_hid_dim, dec_hid_dim, dropout, packed=True)
    dec = Decoder(len(tgt_vocab), emb_dim, enc_hid_dim, dec_hid_dim, dropout)
    model = Seq2Seq(enc, dec, pad_idx=PAD_IDX).to(device)

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[*] Seq2Seq Architecture initialized with {total_params:,} trainable parameters.")

    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss(ignore_index=PAD_IDX)

    best_val_loss = float("inf")
    best_weights_path = weights_dir / "seq2seq_translit.pt"

    start_time = time.time()
    history = []
    stale = 0
    metadata = {"language": language, "seed": seed, "device": str(device), "torch_version": torch.__version__,
                "training_examples": len(train_ds), "validation_examples": len(val_ds),
                "train_sha256": hashlib.sha256(train_file.read_bytes()).hexdigest(),
                "validation_sha256": hashlib.sha256(val_file.read_bytes()).hexdigest(),
                "batch_size": batch_size, "learning_rate": lr, "threads": threads}
    metadata.update(requested_epochs=epochs,architecture={'embedding_dim':emb_dim,'hidden_dim':enc_hid_dim,'packed_encoder':True,'trainable_parameters':total_params})

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0

        for batch_index, (src, tgt, _, _, _, _) in enumerate(train_loader):
            src = src.to(device)
            tgt = tgt.to(device)

            optimizer.zero_grad()
            output = model(src, tgt, teacher_forcing_ratio=0.5)

            # output: [batch_size, tgt_len, tgt_vocab_size]
            output_dim = output.shape[-1]
            output = output[:, 1:].reshape(-1, output_dim)
            tgt = tgt[:, 1:].reshape(-1)

            loss = criterion(output, tgt)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            epoch_loss += loss.item()
            if (batch_index + 1) % 100 == 0:
                print(f"Epoch {epoch} batch {batch_index+1}/{len(train_loader)} loss={loss.item():.4f}", flush=True)

        avg_train_loss = epoch_loss / max(1, len(train_loader))

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for src, tgt, _, _, _, _ in val_loader:
                src = src.to(device)
                tgt = tgt.to(device)

                output = model(src, tgt, teacher_forcing_ratio=0.0)
                output_dim = output.shape[-1]
                output = output[:, 1:].reshape(-1, output_dim)
                tgt = tgt[:, 1:].reshape(-1)

                loss = criterion(output, tgt)
                val_loss += loss.item()

        avg_val_loss = val_loss / max(1, len(val_loader))

        if avg_val_loss < best_val_loss:
            stale = 0
            best_val_loss = avg_val_loss
            pending_weights=best_weights_path.with_suffix('.tmp')
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": best_val_loss,
                "hyperparams": {
                    "emb_dim": emb_dim,
                    "enc_hid_dim": enc_hid_dim,
                    "dec_hid_dim": dec_hid_dim,
                    "src_vocab_len": len(src_vocab),
                    "tgt_vocab_len": len(tgt_vocab),
                    "packed_encoder": True,
                    "language": language,
                }
            }, str(pending_weights))
            pending_weights.replace(best_weights_path)
            mark = "* [Saved Best]"
        else:
            stale += 1
            mark = ""

        history.append({"epoch": epoch, "train_loss": avg_train_loss, "validation_loss": avg_val_loss, "elapsed_seconds": time.time()-start_time})
        (artifact_dir / "training_report.json").write_text(json.dumps({**metadata, "best_validation_loss": best_val_loss, "history": history}, indent=2), encoding="utf-8")
        print(f"Epoch [{epoch:02d}/{epochs:02d}] | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} {mark}", flush=True)
        if stale >= patience:
            print("Early stopping: validation loss stopped improving.", flush=True)
            break

    total_time = time.time() - start_time
    (artifact_dir/'training_report.json').write_text(json.dumps({**metadata,'status':'completed' if len(history)==epochs else 'early_stopped',
        'completed_epochs':len(history),'best_validation_loss':best_val_loss,'history':history},indent=2),encoding='utf-8')
    print(f"[*] Training finished in {total_time:.2f} seconds. Best Val Loss: {best_val_loss:.4f}")
    return str(best_weights_path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--data-dir")
    parser.add_argument("--output-dir")
    parser.add_argument("--language", choices=["hindi", "marathi", "bengali"])
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--embedding-dim", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--patience", type=int, default=3)
    args = parser.parse_args()
    train_transliteration_model(epochs=args.epochs, batch_size=args.batch_size, device_name=args.device,
                                data_dir=args.data_dir, output_dir=args.output_dir, language=args.language,
                                threads=args.threads, hidden_dim=args.hidden_dim, embedding_dim=args.embedding_dim,
                                seed=args.seed, patience=args.patience)
