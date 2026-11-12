"""Structural onboarding checks, with review/quality gates reported separately."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def check():
    from app.core.languages import LANGUAGES,has_native
    from app.services.gamification.curriculum import course
    from runtime_evaluation import load_cases
    _,cases=load_cases()
    result={}
    for name,metadata in LANGUAGES.items():
        required=('label','native_name','script','speech','flores','unicode_start','unicode_end','transliteration_backend','sample_native','sample_roman')
        missing=[key for key in required if not metadata.get(key)]
        directions={other:sum(r['source_language']==name and r['target_language']==other for r in cases) for other in LANGUAGES if other!=name}
        result[name]={'structural_ready':not missing and has_native(metadata['sample_native'],name) and all(n>=50 for n in directions.values()),
                      'missing_metadata':missing,'draft_cases_by_target':directions,
                      'has_foundations_content':bool(course(name)), 'human_quality_gate':'pending',
                      'advertise_verified_accuracy':False}
    return result


if __name__=='__main__':
    result=check();print(json.dumps(result,indent=2));raise SystemExit(0 if all(row['structural_ready'] for row in result.values()) else 1)
