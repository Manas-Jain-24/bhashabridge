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
    device_name: str = "auto"
):
    base_dir = Path(__file__).resolve().parent
    root_dir = base_dir.parent.parent
    train_file = root_dir / "data" / "processed" / "transliteration" / "train.jsonl"
    val_file = root_dir / "data" / "processed" / "transliteration" / "validation.jsonl"
    weights_dir = base_dir / "weights"
    weights_dir.mkdir(exist_ok=True)
    vocab_file = base_dir / "vocab.json"

    if device_name == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(device_name)
    print(f"[*] Training on device: {device}")

    # 1. Build dataset and vocabularies
    train_ds = TransliterationDataset(str(train_file), build_vocab=True)
    val_ds = TransliterationDataset(str(val_file), src_vocab=train_ds.src_vocab, tgt_vocab=train_ds.tgt_vocab)

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
    emb_dim = 128
    enc_hid_dim = 256
    dec_hid_dim = 256
    dropout = 0.15

    enc = Encoder(len(src_vocab), emb_dim, enc_hid_dim, dec_hid_dim, dropout)
    dec = Decoder(len(tgt_vocab), emb_dim, enc_hid_dim, dec_hid_dim, dropout)
    model = Seq2Seq(enc, dec, pad_idx=PAD_IDX).to(device)

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[*] Seq2Seq Architecture initialized with {total_params:,} trainable parameters.")

    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss(ignore_index=PAD_IDX)

    best_val_loss = float("inf")
    best_weights_path = weights_dir / "seq2seq_translit.pt"

    start_time = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0

        for src, tgt, _, _, _, _ in train_loader:
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
            best_val_loss = avg_val_loss
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
                }
            }, str(best_weights_path))
            mark = "* [Saved Best]"
        else:
            mark = ""

        print(f"Epoch [{epoch:02d}/{epochs:02d}] | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} {mark}")

    total_time = time.time() - start_time
    print(f"[*] Training finished in {total_time:.2f} seconds. Best Val Loss: {best_val_loss:.4f}")
    return str(best_weights_path)

if __name__ == "__main__":
    train_transliteration_model(epochs=10, batch_size=512)
