"""
BhashaBridge — ML Transliteration Dataset & Vocabulary Module (M7)
Constructs character-level vocabularies and PyTorch Datasets for Latin <-> Devanagari transliteration.
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import torch
from torch.utils.data import Dataset

PAD_TOKEN = "<pad>"
SOS_TOKEN = "<sos>"
EOS_TOKEN = "<eos>"
UNK_TOKEN = "<unk>"

PAD_IDX = 0
SOS_IDX = 1
EOS_IDX = 2
UNK_IDX = 3

class CharVocab:
    def __init__(self, name: str):
        self.name = name
        self.char2idx: Dict[str, int] = {
            PAD_TOKEN: PAD_IDX,
            SOS_TOKEN: SOS_IDX,
            EOS_TOKEN: EOS_IDX,
            UNK_TOKEN: UNK_IDX,
        }
        self.idx2char: Dict[int, str] = {v: k for k, v in self.char2idx.items()}

    def add_char(self, ch: str):
        if ch not in self.char2idx:
            idx = len(self.char2idx)
            self.char2idx[ch] = idx
            self.idx2char[idx] = ch

    def encode(self, text: str, add_sos_eos: bool = True) -> List[int]:
        tokens = [SOS_IDX] if add_sos_eos else []
        for ch in text:
            tokens.append(self.char2idx.get(ch, UNK_IDX))
        if add_sos_eos:
            tokens.append(EOS_IDX)
        return tokens

    def decode(self, indices: List[int], strip_special: bool = True) -> str:
        chars = []
        for idx in indices:
            if strip_special and idx in (PAD_IDX, SOS_IDX, EOS_IDX):
                if idx == EOS_IDX:
                    break
                continue
            chars.append(self.idx2char.get(idx, ""))
        return "".join(chars)

    def __len__(self):
        return len(self.char2idx)

    def to_dict(self) -> Dict:
        return {"name": self.name, "char2idx": self.char2idx}

    @classmethod
    def from_dict(cls, data: Dict) -> "CharVocab":
        vocab = cls(data["name"])
        vocab.char2idx = data["char2idx"]
        vocab.idx2char = {int(v): k for k, v in vocab.char2idx.items()}
        return vocab


class TransliterationDataset(Dataset):
    def __init__(
        self,
        filepath: str,
        src_vocab: Optional[CharVocab] = None,
        tgt_vocab: Optional[CharVocab] = None,
        direction: str = "latin_to_devanagari",
        build_vocab: bool = False
    ):
        self.pairs: List[Tuple[str, str, str]] = []
        self.direction = direction

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                roman = record.get("roman", "").strip().lower()
                devanagari = record.get("devanagari", "").strip()
                lang = record.get("language", "mr")
                if roman and devanagari:
                    if direction == "latin_to_devanagari":
                        self.pairs.append((roman, devanagari, lang))
                    else:
                        self.pairs.append((devanagari, roman, lang))

        if build_vocab or src_vocab is None:
            self.src_vocab = CharVocab("src")
            for src_str, _, _ in self.pairs:
                for ch in src_str:
                    self.src_vocab.add_char(ch)
        else:
            self.src_vocab = src_vocab

        if build_vocab or tgt_vocab is None:
            self.tgt_vocab = CharVocab("tgt")
            for _, tgt_str, _ in self.pairs:
                for ch in tgt_str:
                    self.tgt_vocab.add_char(ch)
        else:
            self.tgt_vocab = tgt_vocab

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx: int):
        src_str, tgt_str, lang = self.pairs[idx]
        src_enc = torch.tensor(self.src_vocab.encode(src_str, add_sos_eos=True), dtype=torch.long)
        tgt_enc = torch.tensor(self.tgt_vocab.encode(tgt_str, add_sos_eos=True), dtype=torch.long)
        return src_enc, tgt_enc, src_str, tgt_str


def collate_fn(batch):
    src_tensors = [item[0] for item in batch]
    tgt_tensors = [item[1] for item in batch]
    src_raw = [item[2] for item in batch]
    tgt_raw = [item[3] for item in batch]

    src_lens = [len(t) for t in src_tensors]
    tgt_lens = [len(t) for t in tgt_tensors]

    src_pad = torch.nn.utils.rnn.pad_sequence(src_tensors, batch_first=True, padding_value=PAD_IDX)
    tgt_pad = torch.nn.utils.rnn.pad_sequence(tgt_tensors, batch_first=True, padding_value=PAD_IDX)

    return src_pad, tgt_pad, torch.tensor(src_lens), torch.tensor(tgt_lens), src_raw, tgt_raw
