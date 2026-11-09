"""Add a manually checked sentence pair to the local exact-match memory."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    from app.core.languages import LANGUAGES, has_native
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-language", required=True, choices=list(LANGUAGES))
    parser.add_argument("--target-language", choices=list(LANGUAGES), help="Required for new language pairs")
    parser.add_argument("--source", required=True, help="Checked native-script source sentence")
    parser.add_argument("--target", required=True, help="Checked native-script translation")
    parser.add_argument("--target-roman", default=None)
    parser.add_argument("--english", default=None)
    parser.add_argument("--reviewed", action="store_true", help="Confirm a person checked the translation")
    args = parser.parse_args()
    if not args.reviewed:
        parser.error("Add --reviewed only after a person checks both sentences.")
    target_language = args.target_language or {"hindi": "marathi", "marathi": "hindi"}.get(args.source_language)
    if target_language is None or target_language == args.source_language:
        parser.error("Choose a distinct --target-language.")
    if not has_native(args.source, args.source_language) or not has_native(args.target, target_language):
        parser.error("Source and target must use their language's native script.")
    if len(args.source) > 2000 or len(args.target) > 2000:
        parser.error("Sentences must be at most 2000 characters.")

    from app.models.database import SessionLocal, init_db
    from app.models.entities import ReviewedTranslation
    from app.services.translation.corpus import normalize_source, heldout_sources

    source_key = normalize_source(args.source)
    forbidden_hi, forbidden_mr = heldout_sources()
    if source_key in {"hindi": forbidden_hi, "marathi": forbidden_mr}.get(args.source_language, set()):
        parser.error("This source is in the frozen evaluation set; keep it out of translation memory.")
    init_db()
    with SessionLocal() as db:
        row = db.query(ReviewedTranslation).filter_by(
            source_language=args.source_language, target_language=target_language,
            source_key=source_key,
        ).first()
        if row is None:
            row = ReviewedTranslation(source_language=args.source_language,
                                      target_language=target_language, source_key=source_key)
            db.add(row)
        row.source_text = args.source.strip()
        row.target_text = args.target.strip()
        row.target_roman = args.target_roman.strip() if args.target_roman else None
        row.english_meaning = args.english.strip() if args.english else None
        row.provenance = "manual_review"
        db.commit()
    print("Reviewed translation saved. It will be used on the next matching request.")


if __name__ == "__main__":
    main()
