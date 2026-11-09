"""Compare a trained Bengali model with the current app fallback on held-out words."""
import argparse
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]


def edit_distance(a,b):
    row=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        next_row=[i]
        for j,cb in enumerate(b,1): next_row.append(min(next_row[-1]+1,row[j]+1,row[j-1]+(ca!=cb)))
        row=next_row
    return row[-1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir',type=Path,default=ROOT/'ml/experiments/bengali-v1')
    parser.add_argument('--split',choices=['validation','test'],default='test')
    parser.add_argument('--threads',type=int,default=2)
    args=parser.parse_args()
    import torch
    torch.set_num_threads(args.threads)
    from ml.transliteration.model import Encoder,Decoder,Seq2Seq
    from ml.transliteration.dataset import CharVocab
    from app.services.transliteration.bengali import transliterate_bengali
    from check_expanded_data import audit
    audit()
    weights=args.model_dir/'weights/seq2seq_translit.pt'
    checkpoint=torch.load(weights,map_location='cpu',weights_only=True)
    hp=checkpoint['hyperparams']
    if hp.get('language')!='bengali': raise ValueError('Not a Bengali checkpoint')
    vocab=json.loads((args.model_dir/'vocab.json').read_text(encoding='utf-8'))
    src=CharVocab.from_dict(vocab['src_vocab']); tgt=CharVocab.from_dict(vocab['tgt_vocab'])
    model=Seq2Seq(Encoder(len(src),hp['emb_dim'],hp['enc_hid_dim'],hp['dec_hid_dim'],packed=hp.get('packed_encoder',False)),Decoder(len(tgt),hp['emb_dim'],hp['enc_hid_dim'],hp['dec_hid_dim']))
    model.load_state_dict(checkpoint['model_state_dict']); model.eval()
    path=ROOT/f'data/processed/expanded/transliteration/{args.split}.jsonl'
    rows=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    rows=[r for r in rows if r['language']=='bengali']
    predictions=[]
    for start in range(0,len(rows),128):
        batch=rows[start:start+128]
        encoded=[torch.tensor(src.encode(r['roman'])) for r in batch]
        padded=torch.nn.utils.rnn.pad_sequence(encoded,batch_first=True,padding_value=0)
        with torch.inference_mode(): output=model.predict(padded,max_len=40)
        predictions.extend({'roman':r['roman'],'reference':unicodedata.normalize('NFC',r['native']),
                            'neural':unicodedata.normalize('NFC',tgt.decode(tokens.tolist())),
                            'fallback':unicodedata.normalize('NFC',transliterate_bengali(r['roman'],'latin_to_devanagari',use_neural=False))} for r,tokens in zip(batch,output))
    def score(key):
        return {'exact_match_percent':100*sum(p[key]==p['reference'] for p in predictions)/len(predictions),
                'character_error_rate':sum(edit_distance(p[key],p['reference']) for p in predictions)/sum(len(p['reference']) for p in predictions)}
    neural=score('neural'); fallback=score('fallback')
    report={'language':'bengali','split':args.split,'examples':len(rows),'sampling':'One preferred Roman spelling per held-out native-word group; not all aliases.',
            'test_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'weights_sha256':hashlib.sha256(weights.read_bytes()).hexdigest(),
            'vocab_sha256':hashlib.sha256((args.model_dir/'vocab.json').read_bytes()).hexdigest(),'best_epoch':checkpoint['epoch'],
            'neural':neural,'current_app_fallback':fallback,
            'promotion_eligible':neural['exact_match_percent']>fallback['exact_match_percent'] and neural['character_error_rate']<fallback['character_error_rate'],
            'limitations':['Unicode-codepoint CER after NFC normalization, not grapheme or pronunciation accuracy.','Word-level benchmark does not measure sentence quality or names.','The existing fallback includes fixed common-word mappings and a training-only lexical lookup.'],
            'examples_preview':predictions[:30], 'neural_errors': [p for p in predictions if p['neural']!=p['reference']][:30]}
    (args.model_dir/f'{args.split}_evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('examples_preview','neural_errors')},indent=2))


if __name__=='__main__': main()
