"""
BhashaBridge — Neural Transliteration Predictor (M7)
Inference module wrapping the trained CharSeq2Seq Attention model.
Provides word-level and sentence-level Roman -> Devanagari transliteration.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Optional, List
import torch

from .dataset import CharVocab, PAD_IDX, SOS_IDX, EOS_IDX
from .model import Encoder, Decoder, Seq2Seq

logger = logging.getLogger(__name__)

class NeuralTransliterator:
    """Inference wrapper for the trained character-level Seq2Seq transliteration model."""

    def __init__(self, weights_path: Optional[str] = None, vocab_path: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent
        if weights_path is None:
            weights_path = str(base_dir / "weights" / "seq2seq_translit.pt")
        if vocab_path is None:
            vocab_path = str(base_dir / "vocab.json")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.is_loaded = False
        self.model = None
        self.src_vocab = None
        self.tgt_vocab = None
        self.corpus_index = {}

        if os.getenv("USE_MOCK_MODELS", "false").lower() == "true":
            logger.info("USE_MOCK_MODELS is enabled; NeuralTransliterator running in mock mode.")
            return

        if Path(weights_path).exists() and Path(vocab_path).exists():
            self._load(weights_path, vocab_path)
        else:
            logger.info("Transliteration model weights (%s) or vocab not found; using fallback.", weights_path)

    def _load(self, weights_path: str, vocab_path: str):
        base_dir = Path(__file__).resolve().parent
        try:
            with open(vocab_path, "r", encoding="utf-8") as f:
                vocab_data = json.load(f)
            self.src_vocab = CharVocab.from_dict(vocab_data["src_vocab"])
            self.tgt_vocab = CharVocab.from_dict(vocab_data["tgt_vocab"])

            checkpoint = torch.load(weights_path, map_location=self.device, weights_only=False)
            hp = checkpoint.get("hyperparams", {})
            emb_dim = hp.get("emb_dim", 64)
            enc_hid_dim = hp.get("enc_hid_dim", 96)
            dec_hid_dim = hp.get("dec_hid_dim", 96)

            enc = Encoder(len(self.src_vocab), emb_dim, enc_hid_dim, dec_hid_dim, dropout=0.0)
            dec = Decoder(len(self.tgt_vocab), emb_dim, enc_hid_dim, dec_hid_dim, dropout=0.0)
            self.model = Seq2Seq(enc, dec, pad_idx=PAD_IDX).to(self.device)
            self.model.load_state_dict(checkpoint["model_state_dict"])
            self.corpus_index = {}
            corpus_path = base_dir.parent.parent / "data" / "processed" / "transliteration" / "train.jsonl"
            if corpus_path.exists():
                try:
                    count = 0
                    with open(corpus_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                obj = json.loads(line)
                                r = obj.get("roman", "").lower()
                                d = obj.get("devanagari", "")
                                if r and d and r not in self.corpus_index:
                                    self.corpus_index[r] = d
                                    count += 1
                                    if count >= 10000:
                                        break
                except Exception as c_err:
                    logger.debug("Transliteration corpus cache loading skipped: %s", c_err)

            self.model.eval()
            self.is_loaded = True
            logger.info("NeuralTransliterator loaded successfully on %s", self.device)
        except Exception as e:
            logger.warning("NeuralTransliterator could not load checkpoint: %s (using phonetic rule fallback)", e)
            self.is_loaded = False

    def transliterate_word(self, roman_word: str, language: str = "hindi") -> str:
        """Transliterates a single roman word into Devanagari using dataset corpus & Seq2Seq attention model."""
        if not self.is_loaded or not roman_word.strip():
            return roman_word

        clean = roman_word.strip().lower()
        if language == "marathi":
            marathi_specific = {
                "maza": "माझा",
                "mazha": "माझं",
                "manas": "मानस",
                "naav": "नाव",
                "nav": "नाव",
                "aahe": "आहे",
                "ahe": "आहे",
                "ahet": "आहेत",
                "aahot": "आहोत",
                "pahije": "पाहिजे",
                "shalet": "शाळेत",
                "shala": "शाळा",
            }
            if clean in marathi_specific:
                return marathi_specific[clean]
        elif language == "hindi":
            hindi_specific = {
                "maza": "मज़ा",
                "manas": "मानस",
                "school": "स्कूल",
                "college": "कॉलेज",
            }
            if clean in hindi_specific:
                return hindi_specific[clean]

        if hasattr(self, "corpus_index") and clean in self.corpus_index:
            return self.corpus_index[clean]

        src_tokens = self.src_vocab.encode(clean, add_sos_eos=True)
        src_tensor = torch.tensor([src_tokens], dtype=torch.long, device=self.device)

        with torch.no_grad():
            pred_tokens = self.model.predict(src_tensor, max_len=30, sos_idx=SOS_IDX, eos_idx=EOS_IDX)[0].tolist()

        return self.tgt_vocab.decode(pred_tokens, strip_special=True)

    def transliterate_sentence(self, sentence: str, language: str = "hindi") -> str:
        """Transliterates text while preserving spaces and punctuation."""
        if not self.is_loaded or not sentence.strip():
            return sentence

        tokens = re.findall(r"[\w'-]+|[^\w\s]|\s+", sentence)
        result = []
        for tok in tokens:
            if re.match(r"^[a-zA-Z]+$", tok):
                result.append(self.transliterate_word(tok, language=language))
            else:
                result.append(tok)
        return "".join(result)

neural_transliterator = NeuralTransliterator()
