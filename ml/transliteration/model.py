"""
BhashaBridge — Character Seq2Seq Model with Bahdanau Attention (M7)
Lightweight neural architecture designed for phonetic sequence-to-sequence transliteration.
"""

import random
import torch
import torch.nn as nn
import torch.nn.functional as F

class Encoder(nn.Module):
    def __init__(self, input_dim: int, emb_dim: int, enc_hid_dim: int, dec_hid_dim: int, dropout: float = 0.1):
        super().__init__()
        self.embedding = nn.Embedding(input_dim, emb_dim)
        self.rnn = nn.GRU(emb_dim, enc_hid_dim, bidirectional=True, batch_first=True)
        self.fc = nn.Linear(enc_hid_dim * 2, dec_hid_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, src: torch.Tensor):
        # src: [batch_size, src_len]
        embedded = self.dropout(self.embedding(src))  # [batch_size, src_len, emb_dim]
        outputs, hidden = self.rnn(embedded)          # outputs: [batch_size, src_len, enc_hid_dim * 2]
        # hidden: [2, batch_size, enc_hid_dim] -> concatenate forward and backward
        hidden_cat = torch.cat((hidden[-2, :, :], hidden[-1, :, :]), dim=1)
        hidden = torch.tanh(self.fc(hidden_cat))      # [batch_size, dec_hid_dim]
        return outputs, hidden


class Attention(nn.Module):
    def __init__(self, enc_hid_dim: int, dec_hid_dim: int):
        super().__init__()
        self.attn = nn.Linear((enc_hid_dim * 2) + dec_hid_dim, dec_hid_dim)
        self.v = nn.Linear(dec_hid_dim, 1, bias=False)

    def forward(self, hidden: torch.Tensor, encoder_outputs: torch.Tensor, mask: torch.Tensor = None):
        # hidden: [batch_size, dec_hid_dim]
        # encoder_outputs: [batch_size, src_len, enc_hid_dim * 2]
        src_len = encoder_outputs.shape[1]
        hidden_rep = hidden.unsqueeze(1).repeat(1, src_len, 1) # [batch_size, src_len, dec_hid_dim]
        energy = torch.tanh(self.attn(torch.cat((hidden_rep, encoder_outputs), dim=2)))
        attention = self.v(energy).squeeze(2) # [batch_size, src_len]
        if mask is not None:
            attention = attention.masked_fill(mask == 0, -1e10)
        return F.softmax(attention, dim=1)


class Decoder(nn.Module):
    def __init__(self, output_dim: int, emb_dim: int, enc_hid_dim: int, dec_hid_dim: int, dropout: float = 0.1):
        super().__init__()
        self.output_dim = output_dim
        self.attention = Attention(enc_hid_dim, dec_hid_dim)
        self.embedding = nn.Embedding(output_dim, emb_dim)
        self.rnn = nn.GRU((enc_hid_dim * 2) + emb_dim, dec_hid_dim, batch_first=True)
        self.fc_out = nn.Linear((enc_hid_dim * 2) + dec_hid_dim + emb_dim, output_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, input_token: torch.Tensor, hidden: torch.Tensor, encoder_outputs: torch.Tensor, mask: torch.Tensor = None):
        # input_token: [batch_size]
        input_token = input_token.unsqueeze(1)
        embedded = self.dropout(self.embedding(input_token)) # [batch_size, 1, emb_dim]

        a = self.attention(hidden, encoder_outputs, mask)     # [batch_size, src_len]
        a = a.unsqueeze(1)                                    # [batch_size, 1, src_len]

        weighted = torch.bmm(a, encoder_outputs)             # [batch_size, 1, enc_hid_dim * 2]
        rnn_input = torch.cat((embedded, weighted), dim=2)   # [batch_size, 1, (enc*2)+emb]

        output, hidden = self.rnn(rnn_input, hidden.unsqueeze(0))
        # output: [batch_size, 1, dec_hid_dim]
        output = output.squeeze(1)
        weighted = weighted.squeeze(1)
        embedded = embedded.squeeze(1)

        prediction = self.fc_out(torch.cat((output, weighted, embedded), dim=1))
        return prediction, hidden.squeeze(0), a.squeeze(1)


class Seq2Seq(nn.Module):
    def __init__(self, encoder: Encoder, decoder: Decoder, pad_idx: int = 0):
        super().__init__()
        self.encoder = encoder
        self.decoder = decoder
        self.pad_idx = pad_idx

    def create_mask(self, src: torch.Tensor):
        return (src != self.pad_idx).long()

    def forward(self, src: torch.Tensor, tgt: torch.Tensor, teacher_forcing_ratio: float = 0.5):
        # src: [batch_size, src_len]
        # tgt: [batch_size, tgt_len]
        batch_size = src.shape[0]
        tgt_len = tgt.shape[1]
        tgt_vocab_size = self.decoder.output_dim

        outputs = torch.zeros(batch_size, tgt_len, tgt_vocab_size, device=src.device)
        mask = self.create_mask(src)

        encoder_outputs, hidden = self.encoder(src)

        # First token is <sos>
        input_tok = tgt[:, 0]

        for t in range(1, tgt_len):
            prediction, hidden, _ = self.decoder(input_tok, hidden, encoder_outputs, mask)
            outputs[:, t, :] = prediction
            teacher_force = random.random() < teacher_forcing_ratio
            top1 = prediction.argmax(1)
            input_tok = tgt[:, t] if teacher_force else top1

        return outputs

    def predict(self, src: torch.Tensor, max_len: int = 40, sos_idx: int = 1, eos_idx: int = 2):
        self.eval()
        with torch.no_grad():
            mask = self.create_mask(src)
            encoder_outputs, hidden = self.encoder(src)
            batch_size = src.shape[0]

            input_tok = torch.tensor([sos_idx] * batch_size, device=src.device)
            preds = [input_tok.unsqueeze(1)]

            for _ in range(max_len):
                prediction, hidden, _ = self.decoder(input_tok, hidden, encoder_outputs, mask)
                top1 = prediction.argmax(1)
                preds.append(top1.unsqueeze(1))
                input_tok = top1

            return torch.cat(preds, dim=1)
