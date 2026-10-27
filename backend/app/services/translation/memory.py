"""Exact, reviewed sentence memory. Model guesses never enter this table."""
import json
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.entities import ReviewedTranslation
from app.services.translation.corpus import ROOT, heldout_sources, normalize_source
from app.services.transliteration.service import transliteration_service


def seed_reviewed_translations(db: Session) -> int:
    """Import unambiguous project-curated examples; leave existing edits intact."""
    path = ROOT / "data/processed/learning/bhashabridge_learning.json"
    if not path.exists():
        return 0
    pairs = json.loads(path.read_text(encoding="utf-8"))
    forbidden_hi, forbidden_mr = heldout_sources()
    candidates = defaultdict(list)
    for pair in pairs:
        hi = pair.get("hindi_devanagari", "").strip()
        mr = pair.get("marathi_devanagari", "").strip()
        if not hi or not mr or normalize_source(hi) in forbidden_hi or normalize_source(mr) in forbidden_mr:
            continue
        for source_lang, target_lang, source, target in (
            ("hindi", "marathi", hi, mr),
            ("marathi", "hindi", mr, hi),
        ):
            candidates[(source_lang, target_lang, normalize_source(source))].append((pair, source, target))

    existing = {(row.source_language, row.target_language, row.source_key) for row in db.query(ReviewedTranslation).all()}
    added = 0
    for key, options in candidates.items():
        # A source with two different translations needs context; an exact lookup
        # must never pick one arbitrarily.
        if key in existing or len({normalize_source(target) for _, _, target in options}) != 1:
            continue
        pair, source, target = options[0]
        target_lang = key[1]
        db.add(ReviewedTranslation(
            source_language=key[0], target_language=target_lang, source_key=key[2],
            source_text=source, target_text=target,
            target_roman=pair.get(f"{target_lang}_roman") or None,
            english_meaning=pair.get("english_meaning") or None,
            provenance=pair.get("source") or "project_curated",
        ))
        added += 1
    db.flush()
    return added


def lookup_reviewed(db: Session, text: str, source_language: str, target_language: str, script: str = "both"):
    if source_language == target_language:
        return None
    source_native = text.strip()
    if not any("\u0900" <= char <= "\u097f" for char in source_native):
        source_native = transliteration_service.transliterate(
            source_native, language=source_language, direction="latin_to_devanagari"
        )
    key = normalize_source(source_native)
    row = db.query(ReviewedTranslation).filter_by(
        source_language=source_language, target_language=target_language, source_key=key
    ).first()
    if row is None:
        return None
    roman = row.target_roman or transliteration_service.transliterate(
        row.target_text, language=target_language, direction="devanagari_to_latin"
    )
    return {
        "source_text": text,
        "source_language": source_language,
        "target_language": target_language,
        "translation": row.target_text if script == "devanagari" else roman,
        "translation_native": row.target_text,
        "translation_roman": roman,
        "english_meaning": row.english_meaning or "",
        "model_source": "reviewed_database",
        "engine": "reviewed_database",
        "fallback_used": False,
    }
