"""Create a reproducible error-review queue without treating similarity as correctness."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import unicodedata

ROOT=Path(__file__).resolve().parents[1]


def numeric_values(text):
    normalized=''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)
    return set(re.findall(r'\d+(?:[.,:/-]\d+)*',normalized))


def flags(row):
    source,prediction=row['source'],row['prediction']
    result=[]
    if row.get('inference_error'): result.append('inference_failure')
    if numeric_values(source)!=numeric_values(prediction): result.append('possible_number_change')
    if re.search(r'[<\[]\s*id\s*\d+\s*[>\]]|ω\d',prediction,re.IGNORECASE): result.append('placeholder_artifact')
    if prediction and not 0.4<=len(prediction)/max(len(source),1)<=2.5: result.append('unusual_length_ratio')
    source_acronyms=set(re.findall(r'\b[A-Z]{2,}\b',source))
    if source_acronyms-set(re.findall(r'\b[A-Z]{2,}\b',prediction)): result.append('possible_acronym_change')
    return result


def main():
    directory=ROOT/'ml/evaluation/expanded-gpu'
    output=ROOT/'ml/evaluation/quality-audit-v1'
    output.mkdir(parents=True,exist_ok=True)
    summary=[]; queue=[]
    corpus=[json.loads(line) for line in (ROOT/'data/processed/expanded/translation/test.jsonl').read_text(encoding='utf-8').splitlines()]
    for path in sorted(directory.glob('*.json')):
        if path.name=='summary.json': continue
        report=json.loads(path.read_text(encoding='utf-8'))
        if not report.get('complete'): raise ValueError('Incomplete baseline report')
        counts=Counter(flag for row in report['predictions'] for flag in flags(row))
        lowest=[p['index'] for p in report['lowest_scoring_examples']]
        flagged=[p['index'] for p in report['predictions'] if flags(p)]
        rng=random.Random(42)
        sample=rng.sample([p['index'] for p in report['predictions']],10)
        selected=sorted(set(lowest+flagged[:25]+sample))
        for index in selected:
            row=report['predictions'][index]
            queue.append({'pair':path.stem,**row,'english_reference':corpus[index]['sentences']['english'],
                          'flags':flags(row),'review_status':'pending_bilingual_review',
                          'selection':('lowest_chrf' if index in lowest else 'heuristic_flag' if index in flagged else 'seeded_sample')})
        summary.append({'pair':path.stem,'examples':report['examples'],'flags':dict(counts),
                        'review_queue_examples':len(selected),'report_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (output/'review_queue.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in queue),encoding='utf-8')
    # These are provisional model-assisted observations, not native-speaker approval.
    notes=[{'pair':'bengali-marathi','index':304,'category':'degenerate_generation',
            'observation':'Repeated fragment rejected by the output guard. Empty hypothesis retained in scoring.'},
           {'pair':'bengali-marathi','index':76,'category':'placeholder_corruption',
            'observation':'Prediction contains a run of Greek omega/digit fragments and loses most sentence content.'},
           {'pair':'bengali-marathi','index':662,'category':'extraneous_content',
            'observation':'Prediction adds an unrelated fragment resembling a date/era inside a sentence about leadership.'},
           {'pair':'bengali-marathi','index':643,'category':'reference_variation',
            'observation':'Bengali source says pen; prediction also says pen while Marathi reference says pencil. Low similarity alone is not a demonstrated meaning error.'},
           {'pair':'bengali-marathi','index':994,'category':'wording_or_reference_variation',
            'observation':'Prediction uses a literal nearby-holiday phrasing. Needs bilingual review before classifying as a semantic error.'}]
    result={'complete':True,'directions':summary,'review_queue_examples':len(queue),
            'provisional_observations':notes,
            'limitations':['Heuristic flags are review candidates, not confirmed error counts.',
                           'No automated score can verify all names, tense, negation or meaning.',
                           'A native bilingual reviewer has not approved this queue.',
                           'Benchmark sources and references are forbidden training inputs.']}
    (output/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'review_queue_examples':len(queue),'directions':summary},indent=2))


if __name__=='__main__': main()
